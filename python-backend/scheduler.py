import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.base import JobLookupError

# Assuming workflow_models.py and main.py are in the same directory or python-backend is in PYTHONPATH
from .workflow_models import Workflow, TargetConnectorType, BrowserActionType, GmailActionType
from .main import perform_navigation # Import the actual function
# If perform_navigation cannot be directly imported due to circular dependencies or structure,
# this will need to be addressed, possibly by passing the function reference or refactoring.

logger = logging.getLogger(__name__)

# Initialize scheduler
scheduler = BackgroundScheduler(daemon=True)
# It's generally better to start the scheduler after all initial jobs are loaded,
# or after the application is fully initialized. For now, start it here.
# If main.py imports this module, scheduler.start() will be called upon import.
scheduler.start()
logger.info("APScheduler started.")


def execute_workflow_action(workflow: Workflow):
    """
    This function is called by APScheduler when a job triggers.
    It executes the action defined in the workflow.
    """
    logger.info(f"Executing scheduled workflow: {workflow.id} - {workflow.name} "
                f"(Connector: {workflow.target_connector}, Action: {workflow.action.action_type})")

    try:
        if workflow.target_connector == TargetConnectorType.BROWSER:
            if workflow.action.action_type == BrowserActionType.NAVIGATE:
                url = workflow.action.params.get('url')
                if url:
                    logger.info(f"Attempting navigation for workflow {workflow.id} to URL: {url}")
                    # perform_navigation should handle its own Playwright context
                    result = perform_navigation(url)
                    logger.info(f"Navigation result for workflow {workflow.id}: {result}")
                else:
                    logger.error(f"URL missing in action params for browser navigation workflow: {workflow.id}")
            else:
                logger.info(f"Browser action '{workflow.action.action_type}' for workflow {workflow.id} not yet implemented in scheduler.")

        elif workflow.target_connector == TargetConnectorType.GMAIL:
            # Placeholder for Gmail actions
            logger.info(f"Gmail action '{workflow.action.action_type}' for workflow {workflow.id} not yet implemented in scheduler.")
            # Example for list_emails if it were implemented here:
            # if workflow.action.action_type == GmailActionType.LIST_EMAILS:
            #     count = workflow.action.params.get('count', 5)
            #     # Need a way to get gmail_service here, or this function needs to be part of a class
            #     # that has access to the gmail_service instance.
            #     logger.warning("Gmail list_emails execution from scheduler needs gmail_service access.")

        else:
            logger.warning(f"Unknown target connector '{workflow.target_connector}' for workflow: {workflow.id}")

    except Exception as e:
        logger.error(f"Error during execution of workflow {workflow.id} ('{workflow.name}'): {e}", exc_info=True)


def add_or_update_job(workflow: Workflow):
    """
    Adds a new job or updates an existing one in the scheduler based on the workflow.
    If the workflow is disabled or not a cron trigger, it ensures the job is removed.
    """
    if not workflow.is_enabled:
        logger.info(f"Workflow '{workflow.id}' is disabled. Ensuring it's not scheduled.")
        remove_job(workflow.id)
        return

    if workflow.trigger.trigger_type == "cron":
        cron_expression = workflow.trigger.config.get("cron_expression")
        if not cron_expression:
            logger.error(f"Cron expression missing for cron-triggered workflow: {workflow.id}")
            remove_job(workflow.id) # Remove if it was scheduled with an old valid cron
            return

        try:
            scheduler.add_job(
                execute_workflow_action,
                trigger=CronTrigger.from_crontab(cron_expression),
                args=[workflow],
                id=workflow.id,
                name=workflow.name,
                replace_existing=True,
                misfire_grace_time=300 # 5 minutes
            )
            logger.info(f"Successfully scheduled/updated cron job for workflow: {workflow.id} - '{workflow.name}' "
                        f"with cron: '{cron_expression}'")
        except Exception as e:
            logger.error(f"Error scheduling cron job for workflow {workflow.id}: {e}", exc_info=True)
    else:
        # If trigger type is not cron (e.g., "event"), remove any existing scheduled (cron) job.
        # Event-based triggers are not handled by APScheduler in this manner; they'd be triggered externally.
        logger.info(f"Workflow '{workflow.id}' is not cron-triggered (type: {workflow.trigger.trigger_type}). "
                    "Ensuring no cron job is scheduled for it.")
        remove_job(workflow.id)


def remove_job(workflow_id: str):
    """
    Removes a job from the scheduler.
    """
    try:
        scheduler.remove_job(workflow_id)
        logger.info(f"Successfully removed job with ID: {workflow_id} from scheduler.")
    except JobLookupError:
        logger.info(f"Job with ID: {workflow_id} not found in scheduler (ignore_missing=True effectively).")
    except Exception as e:
        logger.error(f"Error removing job {workflow_id} from scheduler: {e}", exc_info=True)

def shutdown_scheduler(wait: bool = True):
    """
    Shuts down the scheduler.
    """
    try:
        if scheduler.running:
            logger.info("Attempting to shut down APScheduler...")
            scheduler.shutdown(wait=wait)
            logger.info("APScheduler shut down successfully.")
        else:
            logger.info("APScheduler was not running or already shut down.")
    except Exception as e:
        logger.error(f"Error during APScheduler shutdown: {e}", exc_info=True)

# Example of how to handle scheduler shutdown on application exit (e.g. using atexit)
# import atexit
# atexit.register(shutdown_scheduler)
# This is generally good practice for background schedulers.
# In our case, main.py will call shutdown_scheduler.
```
