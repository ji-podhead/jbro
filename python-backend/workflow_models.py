from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, validator

# --- Enums for Types ---

class TriggerType(str, Enum):
    CRON = "cron"
    EVENT = "event" # Assuming this was there or could be added/is already
    SEMANTIC_CONDITION = "semantic_condition"

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
        # 'values' may not contain 'trigger_type' yet if it hasn't been validated or is missing.
        # To get trigger_type reliably for this validator, it should be part of the 'values' dict.
        # Pydantic processes fields in the order they are defined.
        # If trigger_type is defined before config, it should be in values.
        trigger_type_value = values.get('trigger_type')

        if not trigger_type_value:
            # This can happen if trigger_type itself is invalid or missing.
            # The validation for trigger_type field itself will catch invalid enum values.
            # If trigger_type is missing, other validators might have issues.
            # For now, if trigger_type isn't resolved, we can't validate config based on it.
            return v # Or raise an error if config validation is strictly dependent on a valid trigger_type

        if trigger_type_value == TriggerType.CRON:
            if "cron_expression" not in v:
                raise ValueError("Cron trigger config must contain 'cron_expression'")
            parts = str(v['cron_expression']).split() # Ensure it's a string before splitting
            if not (5 <= len(parts) <= 6):
                raise ValueError("Cron expression must have 5 or 6 parts")
        elif trigger_type_value == TriggerType.EVENT:
            if "event_source" not in v or "event_type" not in v:
                raise ValueError("Event trigger config must contain 'event_source' and 'event_type'")
        elif trigger_type_value == TriggerType.SEMANTIC_CONDITION:
            if 'condition_description' not in v:
                raise ValueError("Semantic condition trigger config must contain 'condition_description'")
            if not isinstance(v['condition_description'], str) or not v['condition_description'].strip():
                 raise ValueError("'condition_description' must be a non-empty string")
            if 'check_interval_cron' not in v:
                raise ValueError("Semantic condition trigger config must contain 'check_interval_cron'")

            parts = str(v['check_interval_cron']).split() # Ensure it's a string
            if not (5 <= len(parts) <= 6):
                raise ValueError("Semantic condition 'check_interval_cron' must be a cron string with 5 or 6 parts")

            if 'required_tools_mcps' in v: # Optional field
                if not isinstance(v['required_tools_mcps'], list) or \
                   not all(isinstance(item, str) for item in v['required_tools_mcps']):
                    raise ValueError("'required_tools_mcps' must be a list of strings, if provided.")
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
        Trigger(trigger_type=TriggerType.CRON, config={"wrong_key": "should_fail"})
    except ValueError as e:
        print(f"Caught expected error for cron trigger: {e}")

    try:
        Trigger(trigger_type=TriggerType.EVENT, config={"event_source": "test"}) # Missing event_type
    except ValueError as e:
        print(f"Caught expected error for event trigger: {e}")

    print("\n--- Testing Semantic Condition Trigger ---")
    try:
        # Valid Semantic Condition
        semantic_trigger_valid_config = {
            "condition_description": "If the stock price of AAPL is above $200",
            "check_interval_cron": "0 * * * *", # Every hour
            "required_tools_mcps": ["web_search", "stock_checker_tool"]
        }
        semantic_trigger = Trigger(trigger_type=TriggerType.SEMANTIC_CONDITION, config=semantic_trigger_valid_config)
        print(f"Valid semantic trigger: {semantic_trigger.model_dump_json(indent=2)}")

        # Valid Semantic Condition (optional mcps missing)
        semantic_trigger_valid_config_no_mcps = {
            "condition_description": "If user sentiment is negative",
            "check_interval_cron": "*/30 * * * *" # Every 30 minutes
        }
        semantic_trigger_no_mcps = Trigger(trigger_type=TriggerType.SEMANTIC_CONDITION, config=semantic_trigger_valid_config_no_mcps)
        print(f"Valid semantic trigger (no mcps): {semantic_trigger_no_mcps.model_dump_json(indent=2)}")


        # Invalid: Missing condition_description
        Trigger(trigger_type=TriggerType.SEMANTIC_CONDITION, config={"check_interval_cron": "* * * * *"})
    except ValueError as e:
        print(f"Caught expected error for semantic trigger (missing condition_description): {e}")

    try:
        # Invalid: Missing check_interval_cron
        Trigger(trigger_type=TriggerType.SEMANTIC_CONDITION, config={"condition_description": "Test"})
    except ValueError as e:
        print(f"Caught expected error for semantic trigger (missing check_interval_cron): {e}")

    try:
        # Invalid: Bad cron string for check_interval_cron
        Trigger(trigger_type=TriggerType.SEMANTIC_CONDITION,
                config={"condition_description": "Test", "check_interval_cron": "bad cron"})
    except ValueError as e:
        print(f"Caught expected error for semantic trigger (bad cron): {e}")

    try:
        # Invalid: mcps not a list
        Trigger(trigger_type=TriggerType.SEMANTIC_CONDITION,
                config={"condition_description": "Test", "check_interval_cron": "* * * * *", "required_tools_mcps": "not-a-list"})
    except ValueError as e:
        print(f"Caught expected error for semantic trigger (mcps not a list): {e}")

    # Example workflow using semantic condition
    semantic_workflow = Workflow(
        id="wf_semantic_example_1",
        name="Monitor Stock and Notify",
        trigger=semantic_trigger, # Use the valid one created above
        target_connector=TargetConnectorType.GMAIL, # Example target
        action=BaseAction(
            action_type=GmailActionType.SEND_EMAIL, # Example action
            params={"to": "user@example.com", "subject": "Stock Alert!", "body": "AAPL is above $200"}
        ),
        is_enabled=True
    )
    print("\n--- Example Workflow with Semantic Condition Trigger ---")
    print(semantic_workflow.model_dump_json(indent=2))


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
