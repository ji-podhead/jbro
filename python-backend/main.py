import sys
import json
from playwright.sync_api import sync_playwright
from agent import Agent # Import the Agent class
from workflow_manager import WorkflowManager # Import WorkflowManager


def perform_navigation(url: str) -> str:
    """
    Launches Playwright, navigates to the given URL, and returns a status message.
    Manages its own Playwright instance.
    """
    print(f"Attempting to navigate to: {url}", file=sys.stderr, flush=True)
    try:
        with sync_playwright() as p:
            # TODO: Consider making headless a configurable option
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            page.goto(url, timeout=30000)  # 30s timeout for navigation

            # page.wait_for_timeout(5000) # Explicit wait if needed for visual confirmation

            response_message = f"Successfully navigated to {url}"
            # Future: Could add page title or other info: response_message = f"Successfully navigated to {url}. Page title: {page.title()}"

            browser.close()
            return response_message
    except Exception as e:
        error_detail = f"{type(e).__name__}: {str(e).splitlines()[0] if str(e) else 'No details'}" # Get first line of error
        print(f"Playwright error while navigating to {url}: {e}", file=sys.stderr, flush=True)
        return f"Error navigating to {url}: {error_detail}"

def main():
    ai_agent = Agent() # Instantiate the agent
    workflow_mgr = WorkflowManager() # Instantiate WorkflowManager
    print("Python backend started. Agent and WorkflowManager are ready.", file=sys.stderr, flush=True)

    while True:
        # final_response_to_electron is for direct string responses for echo_message or errors.
        # For structured data like workflow list, we'll construct the JSON for echo_message tool directly.
        final_response_to_electron = ""
        try:
            line = sys.stdin.readline()
            if not line:  # Handles EOF (Ctrl+D)
                print("Python backend received EOF. Exiting.", file=sys.stderr, flush=True)
                break

            message_from_electron = line.strip()

            if not message_from_electron: # Empty line after strip
                print("Python backend received empty line signal. Exiting.", file=sys.stderr, flush=True)
                break

            # Get structured action from the agent
            structured_action_str = ai_agent.process_message(message_from_electron)

            try:
                action_data = json.loads(structured_action_str)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from agent: {e}. Raw: {structured_action_str}", file=sys.stderr, flush=True)
                # Construct the error message for the echo_message tool
                error_payload_for_echo = json.dumps({"tool": "echo_message", "message": f"Error: Could not understand agent's response. (Invalid JSON: {e})"})
                sys.stdout.write(error_payload_for_echo + '\n')
                sys.stdout.flush()
                continue # Skip further processing for this malformed message

            tool_to_use = action_data.get("tool")
            output_payload_for_electron = None # This will hold the JSON string to send

            if tool_to_use == "browser_navigate":
                url_to_navigate = action_data.get("url")
                nav_response = ""
                if url_to_navigate:
                    nav_response = perform_navigation(url_to_navigate)
                else:
                    nav_response = "Error: Agent requested navigation but no URL was provided."
                output_payload_for_electron = json.dumps({"tool": "echo_message", "message": nav_response})

            elif tool_to_use == "browser_search":
                query = action_data.get("query", "nothing specific")
                search_response = f"Agent action: Search for '{query}'. (Search tool not yet implemented in main handler)"
                print(f"Received browser_search tool request for query: {query}", file=sys.stderr, flush=True)
                output_payload_for_electron = json.dumps({"tool": "echo_message", "message": search_response})

            elif tool_to_use == "echo_message":
                echo_msg = action_data.get("message", "Agent requested echo but no message was provided.")
                # The message might already be JSON (e.g. from list_workflows), or plain text.
                # We just wrap it again in the echo_message tool structure for consistency if it's not already.
                # However, the agent.py for list_workflows already sends it in the final desired format for echo_message.
                # So, if the message is from list_workflows, it's already a JSON string.
                # We need to be careful not to double-encode.
                # The current plan is for list_workflows in main.py to construct the final JSON string for echo_message.
                output_payload_for_electron = json.dumps({"tool": "echo_message", "message": echo_msg})

            elif tool_to_use == "list_workflows":
                workflows = workflow_mgr.list_workflows()
                workflows_data = [wf.model_dump() for wf in workflows]
                # Package the workflow list data into a specific structure for the frontend
                # This entire structure will be the 'message' part of an 'echo_message' tool call
                workflow_list_message_content = json.dumps({"type": "workflow_list", "data": workflows_data})
                output_payload_for_electron = json.dumps({"tool": "echo_message", "message": workflow_list_message_content})

            else:
                unknown_tool_message = f"Error: Unknown tool '{tool_to_use}' requested by agent."
                print(unknown_tool_message, file=sys.stderr, flush=True)
                output_payload_for_electron = json.dumps({"tool": "echo_message", "message": unknown_tool_message})

            if output_payload_for_electron:
                sys.stdout.write(output_payload_for_electron + '\n')
                sys.stdout.flush()

        except Exception as e:
            print(f"Python backend main loop error: {e}", file=sys.stderr, flush=True)
            # Try to inform Electron if possible
            critical_error_msg = f"Critical error in Python backend: {type(e).__name__}"
            error_payload = json.dumps({"tool": "echo_message", "message": critical_error_msg})
            sys.stdout.write(error_payload + '\n')
            sys.stdout.flush()
            # Depending on error severity, might need to break or attempt to recover.
            # If stdin/stdout pipe is broken, exiting might be the only option.

if __name__ == "__main__":
    main()
