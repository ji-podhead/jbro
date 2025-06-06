from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, validator

# --- Enums for Types ---
class TargetConnectorType(str, Enum):
    BROWSER = "browser"
    GMAIL = "gmail"
    # Future: DISCORD = "discord", WEBHOOK = "webhook"

class BrowserActionType(str, Enum):
    NAVIGATE = "navigate"
    SCRAPE_ELEMENT = "scrape_element" # Placeholder
    # Future: CLICK = "click", FILL_FORM = "fill_form"

class GmailActionType(str, Enum):
    READ_EMAIL = "read_email"       # Placeholder
    SEND_EMAIL = "send_email"       # Placeholder
    LIST_EMAILS = "list_emails"

# --- Action Parameter Models ---
# These models define the expected parameters for specific actions.
# They can be used within the `BaseAction.params` dict for validation if desired,
# or BaseAction.params can remain a flexible Dict[str, Any].
# For now, we'll define them but keep BaseAction.params flexible.

class BrowserNavigateActionParams(BaseModel):
    url: HttpUrl = Field(..., description="The URL to navigate to.")

class GmailListEmailsActionParams(BaseModel):
    count: Optional[int] = Field(default=5, ge=1, le=100, description="Number of emails to list.")
    # folder: Optional[str] = "INBOX" # Example of another param

# --- Base Action Model ---
class BaseAction(BaseModel):
    """
    Represents a single action to be performed by a target connector.
    The `action_type` should correspond to an enum like BrowserActionType or GmailActionType.
    """
    action_type: str = Field(..., description="Type of action to perform, maps to connector-specific actions.")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the action.")

    # Example of how you might validate params against specific models if action_type is known:
    # @validator('params', pre=True, always=True)
    # def check_params(cls, v, values):
    #     action_type = values.get('action_type')
    #     if action_type == BrowserActionType.NAVIGATE:
    #         return BrowserNavigateActionParams(**v).model_dump()
    #     if action_type == GmailActionType.LIST_EMAILS:
    #         return GmailListEmailsActionParams(**v).model_dump()
    #     # Add more checks as new actions and param models are defined
    #     return v


# --- Trigger Model ---
class Trigger(BaseModel):
    """
    Defines what initiates a workflow.
    """
    trigger_type: str = Field(..., description="Type of trigger, e.g., 'cron', 'event'.")
    config: Dict[str, Any] = Field(..., description="Configuration for the trigger.")

    @validator('config', pre=True, always=True)
    def check_config_for_trigger_type(cls, v, values):
        trigger_type = values.get('trigger_type')
        if trigger_type == "cron":
            if "cron_expression" not in v:
                raise ValueError("Cron trigger_type requires 'cron_expression' in config.")
        elif trigger_type == "event":
            if "event_source" not in v or "event_type" not in v:
                raise ValueError("Event trigger_type requires 'event_source' and 'event_type' in config.")
        # Add more validation as new trigger types are supported
        return v

# --- Main Workflow Model ---
class Workflow(BaseModel):
    """
    Defines an automated workflow, consisting of a trigger, a target connector, and an action.
    """
    id: str = Field(..., description="Unique ID for the workflow.")
    name: str = Field(..., description="User-friendly name for the workflow.")
    trigger: Trigger
    target_connector: TargetConnectorType
    action: BaseAction
    is_enabled: bool = Field(default=True, description="Whether the workflow is currently active.")


# --- Example Usage ---
if __name__ == '__main__':
    # Example 1: Cron-triggered browser navigation
    cron_nav_workflow = Workflow(
        id="wf_cron_navigate_example",
        name="Daily News Check",
        trigger=Trigger(
            trigger_type="cron",
            config={"cron_expression": "0 9 * * MON-FRI"} # 9 AM every weekday
        ),
        target_connector=TargetConnectorType.BROWSER,
        action=BaseAction(
            action_type=BrowserActionType.NAVIGATE,
            params=BrowserNavigateActionParams(url="https://news.google.com").model_dump()
            # Alternative for params if not using specific Pydantic models for them yet:
            # params={"url": "https://news.google.com"}
        )
    )
    print("--- Example Cron Workflow (Browser Navigation) ---")
    print(cron_nav_workflow.model_dump_json(indent=2))

    # Example 2: Event-triggered Gmail email listing
    event_gmail_workflow = Workflow(
        id="wf_event_list_emails_example",
        name="List New Emails on Event",
        trigger=Trigger(
            trigger_type="event", # This event type is hypothetical for now
            config={"event_source": "internal_system", "event_type": "user_request_list_emails"}
        ),
        target_connector=TargetConnectorType.GMAIL,
        action=BaseAction(
            action_type=GmailActionType.LIST_EMAILS,
            params=GmailListEmailsActionParams(count=3).model_dump()
            # Alternative for params:
            # params={"count": 3}
        )
    )
    print("\n--- Example Event Workflow (Gmail List Emails) ---")
    print(event_gmail_workflow.model_dump_json(indent=2))

    # Example 3: Workflow with generic params in BaseAction
    generic_params_workflow = Workflow(
        id="wf_generic_params_example",
        name="Generic Param Test",
        trigger=Trigger(trigger_type="cron", config={"cron_expression": "* * * * *"}),
        target_connector=TargetConnectorType.BROWSER,
        action=BaseAction(
            action_type="some_custom_browser_action", # Not in Enum, shows flexibility
            params={"element_id": "myButton", "value_to_set": "Hello World"}
        )
    )
    print("\n--- Example Workflow (Generic Params) ---")
    print(generic_params_workflow.model_dump_json(indent=2))

    # Test validation for Trigger
    print("\n--- Testing Trigger Validation ---")
    try:
        Trigger(trigger_type="cron", config={"wrong_key": "should_fail"})
    except ValueError as e:
        print(f"Caught expected error for cron trigger: {e}")

    try:
        Trigger(trigger_type="event", config={"event_source": "test"}) # Missing event_type
    except ValueError as e:
        print(f"Caught expected error for event trigger: {e}")

    # Test BrowserNavigateActionParams validation (URL)
    print("\n--- Testing Action Param Validation ---")
    try:
        BrowserNavigateActionParams(url="not_a_valid_url")
    except ValueError as e:
        print(f"Caught expected error for invalid URL: {e}")

    valid_nav_params = BrowserNavigateActionParams(url="http://example.com")
    print(f"Valid navigation params: {valid_nav_params.model_dump_json()}")

    valid_list_params = GmailListEmailsActionParams(count=10)
    print(f"Valid list emails params: {valid_list_params.model_dump_json()}")
