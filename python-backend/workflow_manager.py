import json
import os
import uuid
import logging
from typing import List, Dict, Optional

# Assuming workflow_models.py is in the same directory or accessible in PYTHONPATH
from .workflow_models import Workflow, TargetConnectorType, BrowserActionType, GmailActionType, Trigger, BaseAction
from . import scheduler # Import the scheduler module

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

WORKFLOW_FILE = 'python-backend/workflows.json' # Path relative to project root

class WorkflowManager:
    def __init__(self, workflow_file_path: str = WORKFLOW_FILE):
        self.workflow_file_path = workflow_file_path
        self.workflows: Dict[str, Workflow] = {}
        self._load_workflows()
        self._initialize_scheduler_jobs() # Schedule jobs for loaded workflows

    def _initialize_scheduler_jobs(self) -> None:
        """Schedules all enabled cron workflows loaded from the file."""
        logger.info("Initializing scheduler jobs for loaded workflows...")
        count = 0
        for workflow in self.workflows.values():
            if workflow.is_enabled and workflow.trigger.trigger_type == "cron":
                scheduler.add_or_update_job(workflow)
                count += 1
        logger.info(f"Initialized {count} cron jobs from loaded workflows.")


    def _load_workflows(self) -> None:
        if not os.path.exists(self.workflow_file_path):
            logger.info(f"Workflow file '{self.workflow_file_path}' not found. Starting with an empty workflow list.")
            return

        try:
            with open(self.workflow_file_path, 'r') as f:
                workflows_data = json.load(f)
                if not isinstance(workflows_data, list):
                    logger.error("Workflow file content is not a list. Cannot load workflows.")
                    return

            for workflow_data in workflows_data:
                try:
                    workflow = Workflow.model_validate(workflow_data)
                    self.workflows[workflow.id] = workflow
                except Exception as e: # Pydantic's ValidationError is a subclass of Exception
                    logger.error(f"Error validating workflow data: {workflow_data.get('id', 'Unknown ID')}. Error: {e}")
            logger.info(f"Loaded {len(self.workflows)} workflows from '{self.workflow_file_path}'.")
        except FileNotFoundError: # Should be caught by os.path.exists, but good practice
            logger.info(f"Workflow file '{self.workflow_file_path}' not found. Starting fresh.")
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from '{self.workflow_file_path}'. File might be corrupted.")
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading workflows: {e}")


    def _save_workflows(self) -> None:
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.workflow_file_path), exist_ok=True)

            workflow_list_to_save = [workflow.model_dump() for workflow in self.workflows.values()]
            with open(self.workflow_file_path, 'w') as f:
                json.dump(workflow_list_to_save, f, indent=2)
            logger.info(f"Saved {len(self.workflows)} workflows to '{self.workflow_file_path}'.")
        except IOError as e:
            logger.error(f"IOError saving workflows to '{self.workflow_file_path}': {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while saving workflows: {e}")

    def add_workflow(self, workflow_data: dict) -> Optional[Workflow]:
        # Ensure 'id' is present, generate if not
        workflow_data.setdefault('id', str(uuid.uuid4()))

        try:
            workflow = Workflow.model_validate(workflow_data)
            if workflow.id in self.workflows:
                logger.warning(f"Workflow with ID '{workflow.id}' already exists. Cannot add.")
                return None # Or raise an error

            self.workflows[workflow.id] = workflow
            self._save_workflows()
            # After successfully adding and saving, update the scheduler
            scheduler.add_or_update_job(workflow)
            logger.info(f"Added workflow '{workflow.name}' with ID '{workflow.id}' and updated scheduler.")
            return workflow
        except Exception as e: # Pydantic's ValidationError
            logger.error(f"Error validating workflow data for add: {e}. Data: {workflow_data}")
            return None

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        return self.workflows.get(workflow_id)

    def list_workflows(self) -> List[Workflow]:
        return list(self.workflows.values())

    def update_workflow(self, workflow_id: str, workflow_update_data: dict) -> Optional[Workflow]:
        existing_workflow = self.get_workflow(workflow_id)
        if not existing_workflow:
            logger.warning(f"Workflow with ID '{workflow_id}' not found. Cannot update.")
            return None

        try:
            # Create a new dict from the existing model, then update with new data
            updated_data = existing_workflow.model_dump()

            # Sensible merge: only update fields present in workflow_update_data
            # For nested structures like 'trigger' or 'action', this replaces them entirely if present in update.
            # A more granular update for nested fields would require deeper logic.
            for key, value in workflow_update_data.items():
                updated_data[key] = value

            # Ensure ID is not changed by the update data
            updated_data['id'] = workflow_id

            updated_workflow = Workflow.model_validate(updated_data)
            self.workflows[workflow_id] = updated_workflow
            self._save_workflows()
            # After successfully updating and saving, update the scheduler
            scheduler.add_or_update_job(updated_workflow)
            logger.info(f"Updated workflow '{updated_workflow.name}' with ID '{workflow_id}' and updated scheduler.")
            return updated_workflow
        except Exception as e: # Pydantic's ValidationError
            logger.error(f"Error validating workflow data for update (ID: {workflow_id}): {e}. Update Data: {workflow_update_data}")
            return None

    def delete_workflow(self, workflow_id: str) -> bool:
        if workflow_id in self.workflows:
            deleted_workflow_name = self.workflows[workflow_id].name
            del self.workflows[workflow_id]
            self._save_workflows()
            # After successfully deleting from store, remove from scheduler
            scheduler.remove_job(workflow_id)
            logger.info(f"Deleted workflow '{deleted_workflow_name}' with ID '{workflow_id}' and removed from scheduler.")
            return True
        logger.warning(f"Workflow with ID '{workflow_id}' not found. Cannot delete.")
        return False

if __name__ == '__main__':
    print("--- WorkflowManager Test ---")
    # Use a test-specific workflow file to avoid interfering with a real one
    TEST_WORKFLOW_FILE = 'python-backend/test_workflows.json'

    # Ensure scheduler is gracefully shutdown for tests, especially if they re-initialize it.
    # For simplicity in this test block, we'll rely on the main app's shutdown.
    # If this test were run completely standalone, we'd manage scheduler shutdown here.

    # Clean up old test file if it exists
    if os.path.exists(TEST_WORKFLOW_FILE):
        os.remove(TEST_WORKFLOW_FILE)
        print(f"Removed old '{TEST_WORKFLOW_FILE}'.")

    manager = WorkflowManager(workflow_file_path=TEST_WORKFLOW_FILE)
    # Note: The scheduler is started when scheduler.py is imported.
    # And manager.__init__ calls _initialize_scheduler_jobs.

    # 1. Add a workflow
    print("\n1. Adding a new workflow...")
    sample_workflow_data_1 = {
        "name": "Daily Site Check",
        "trigger": {"trigger_type": "cron", "config": {"cron_expression": "0 8 * * *"}},
        "target_connector": TargetConnectorType.BROWSER.value, # Use enum value
        "action": {
            "action_type": BrowserActionType.NAVIGATE.value, # Use enum value
            "params": {"url": "https://example.com"}
        },
        "is_enabled": True
    }
    added_wf1 = manager.add_workflow(sample_workflow_data_1)
    if added_wf1:
        print(f"Added workflow: {added_wf1.name} (ID: {added_wf1.id})")
        wf1_id = added_wf1.id
    else:
        print("Failed to add workflow 1.")
        wf1_id = None


    sample_workflow_data_2 = {
        "id": "fixed_id_workflow_2", # Provide a specific ID
        "name": "Gmail Email Lister",
        "trigger": {"trigger_type": "event", "config": {"event_source": "manual", "event_type": "button_click"}},
        "target_connector": TargetConnectorType.GMAIL.value,
        "action": {
            "action_type": GmailActionType.LIST_EMAILS.value,
            "params": {"count": 7}
        }
    }
    added_wf2 = manager.add_workflow(sample_workflow_data_2)
    if added_wf2:
        print(f"Added workflow: {added_wf2.name} (ID: {added_wf2.id})")
    else:
        print("Failed to add workflow 2.")

    # 2. List workflows
    print("\n2. Listing workflows...")
    all_workflows = manager.list_workflows()
    print(f"Found {len(all_workflows)} workflows:")
    for wf in all_workflows:
        print(f"  - {wf.name} (ID: {wf.id}, Enabled: {wf.is_enabled})")

    # 3. Get a specific workflow (if wf1_id is available)
    if wf1_id:
        print(f"\n3. Getting workflow with ID: {wf1_id}...")
        retrieved_wf = manager.get_workflow(wf1_id)
        if retrieved_wf:
            print(f"Retrieved: {retrieved_wf.name}, Target: {retrieved_wf.target_connector}")
        else:
            print(f"Workflow {wf1_id} not found.")

    # 4. Update a workflow (if wf1_id is available)
    if wf1_id:
        print(f"\n4. Updating workflow {wf1_id}...")
        update_data = {"name": "Daily Example.com Check - Updated", "is_enabled": False}
        updated_wf = manager.update_workflow(wf1_id, update_data)
        if updated_wf:
            print(f"Updated workflow name to: '{updated_wf.name}', Enabled: {updated_wf.is_enabled}")
            # Verify by getting again
            check_wf = manager.get_workflow(wf1_id)
            if check_wf:
                 print(f"Verification - Name: {check_wf.name}, Enabled: {check_wf.is_enabled}")
        else:
            print(f"Failed to update workflow {wf1_id}.")

    # 5. Delete a workflow (if wf1_id is available)
    if wf1_id:
        print(f"\n5. Deleting workflow {wf1_id}...")
        delete_success = manager.delete_workflow(wf1_id)
        print(f"Deletion status for {wf1_id}: {delete_success}")
        # Verify by trying to get it again
        print(f"Trying to get deleted workflow {wf1_id}: {manager.get_workflow(wf1_id)}")

    # 6. List workflows again
    print("\n6. Listing workflows after deletion...")
    all_workflows_after_delete = manager.list_workflows()
    print(f"Found {len(all_workflows_after_delete)} workflows:")
    for wf in all_workflows_after_delete:
        print(f"  - {wf.name} (ID: {wf.id})")

    # Test loading from file by creating a new manager instance
    print("\n7. Testing loading from file...")
    manager2 = WorkflowManager(workflow_file_path=TEST_WORKFLOW_FILE)
    print(f"Manager2 loaded {len(manager2.list_workflows())} workflows.")
    for wf in manager2.list_workflows():
        print(f"  - Loaded: {wf.name} (ID: {wf.id})")
        if wf.id == "fixed_id_workflow_2":
             assert wf.action.params.get("count") == 7 # Basic check

    # Test adding invalid workflow data
    print("\n8. Testing adding invalid workflow data...")
    invalid_workflow_data = {
        "name": "Invalid Workflow",
        "trigger": {"trigger_type": "cron"}, # Missing config.cron_expression
        "target_connector": "unknown_connector", # Invalid enum
        "action": {"action_type": "unknown_action"}
    }
    added_invalid_wf = manager.add_workflow(invalid_workflow_data)
    print(f"Result of adding invalid workflow: {added_invalid_wf}")
    assert added_invalid_wf is None

    print("\n--- WorkflowManager Test Complete ---")
    # Clean up test file after tests
    # if os.path.exists(TEST_WORKFLOW_FILE):
    #     os.remove(TEST_WORKFLOW_FILE)
    #     print(f"Cleaned up '{TEST_WORKFLOW_FILE}'.")

    # It's important to shut down the global scheduler if these tests are run multiple times
    # or if the main application also uses it. For this __main__ block, we assume it's the
    # primary user or the main app isn't running simultaneously with these tests.
    # In a real test suite, scheduler management would be more careful.
    print("\n--- Test complete. Shutting down scheduler for this test run. ---")
    scheduler.shutdown_scheduler(wait=False) # Use wait=False for quick exit in tests
