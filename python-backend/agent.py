import json
from . import gmail_integration # For integration within the package
# import gmail_integration # For standalone testing if gmail_integration.py is in PYTHONPATH

class Agent:
    def __init__(self):
        """
        Initializes the Agent and the Gmail service.
        """
        # Attempt to initialize Gmail service when Agent is created.
        # gmail_integration.get_gmail_service() is designed to be safe even if
        # credentials are not yet fully set up (will return None and log).
        self.gmail_service = gmail_integration.get_gmail_service()
        if self.gmail_service:
            gmail_integration.logging.info("Agent: Gmail service initialized successfully.")
        else:
            gmail_integration.logging.warning("Agent: Gmail service could not be initialized. Email features will be unavailable.")

    def process_message(self, message_text: str) -> str:
        """
        Processes a raw message string and returns a JSON string representing the action to take.
        This acts as a mock LLM, parsing commands and determining tool usage.
        """
        cleaned_message = message_text.strip().lower()
        original_message_text = message_text.strip() # Keep original casing for echo

        # Default action, overridden if a command is matched
        action = {"tool": "echo_message", "message": f"I'm not sure how to handle: {original_message_text}"}

        if cleaned_message.startswith("navigate to "):
            url = original_message_text[len("navigate to "):].strip()
            if url:
                if not (url.startswith("http://") or url.startswith("https://")):
                    url = "http://" + url
                action = {"tool": "browser_navigate", "url": url}
            else:
                action = {"tool": "echo_message", "message": "Please specify a URL to navigate to."}

        elif cleaned_message.startswith("search for "):
            query = original_message_text[len("search for "):].strip()
            if query:
                action = {"tool": "browser_search", "query": query}
            else:
                action = {"tool": "echo_message", "message": "Please specify what you want to search for."}

        elif cleaned_message.startswith("echo "):
            text_to_echo = original_message_text[len("echo "):].strip()
            if text_to_echo:
                action = {"tool": "echo_message", "message": text_to_echo}
            else:
                action = {"tool": "echo_message", "message": "Echo command received, but no message to echo."}

        elif cleaned_message in ["list emails", "show my emails", "get my emails"]:
            if self.gmail_service:
                email_list = gmail_integration.list_recent_emails(self.gmail_service, count=3) # Fetch 3 for brevity
                if email_list and not (len(email_list) == 1 and "Error:" in email_list[0]):
                    response_message = "Here are your recent emails:\n" + "\n".join(email_list)
                    action = {"tool": "echo_message", "message": response_message}
                elif not email_list: # Explicitly empty list, not an error from the function
                     action = {"tool": "echo_message", "message": "No recent emails found."}
                else: # email_list contains an error message or is empty due to error
                    # If list_recent_emails returns a list with a single error string
                    error_msg_from_func = email_list[0] if isinstance(email_list, list) and len(email_list) > 0 else "Could not retrieve emails. Check logs or Gmail setup."
                    action = {"tool": "echo_message", "message": error_msg_from_func}
            else:
                action = {"tool": "echo_message", "message": "Gmail service is not available. Please ensure credentials are set up correctly."}

        elif cleaned_message == "list workflows":
            action = {"tool": "list_workflows"}

        # The default action defined at the beginning of the method is used if no other command matches.

        return json.dumps(action)

if __name__ == '__main__':
    # This basic test for agent.py will likely fail to initialize gmail_service
    # if gmail_credentials.json is not found or if run outside the package context
    # where `from . import gmail_integration` works.
    # For more robust standalone testing of agent.py, you might need to adjust imports
    # or ensure PYTHONPATH is set up.

    print("Starting Agent standalone test...")
    # To test gmail_integration part, ensure 'python-backend/gmail_credentials.json' exists
    # and 'python-backend' is in PYTHONPATH or run from the project root.
    # For this example, we assume `gmail_integration.py` is in the same dir or PYTHONPATH.
    # If running this file directly, `from . import gmail_integration` might need to be
    # changed to `import gmail_integration` and ensure gmail_integration.py is discoverable.

    # Quick check if gmail_integration is accessible; this doesn't mean service is working
    try:
        from . import gmail_integration as gi_test
        print(f"Successfully imported gmail_integration (version check: {hasattr(gi_test, 'SCOPES')})")
    except ImportError:
        try:
            import gmail_integration as gi_test_alt
            print(f"Successfully imported gmail_integration (alternative) (version check: {hasattr(gi_test_alt, 'SCOPES')})")
            # Make it available for the Agent class if it was imported this way
            gmail_integration = gi_test_alt
        except ImportError:
            print("Failed to import gmail_integration. Email features will not work in this test.")
            # Create a dummy gmail_integration to prevent Agent init from crashing if it's not found
            class DummyGmailIntegration:
                def get_gmail_service(self): return None
                def list_recent_emails(self, service, count): return ["Error: Gmail module not found."]
                def logging(self): return type('dummy_logging', (object,), {'info': print, 'warning': print, 'error': print})()
            gmail_integration = DummyGmailIntegration()


    agent_instance = Agent()

    test_queries = [
        "navigate to example.com",
        "search for python tutorials",
        "echo This is a test message",
        "list emails",
        "show my emails",
        "list workflows", # New test case
        "what is the meaning of life?" # Fallback
    ]

    for query in test_queries:
        print(f"\nInput: \"{query}\"")
        action_json = agent_instance.process_message(query)
        action_data = json.loads(action_json)
        print(f"Action: {action_data}")
        if action_data["tool"] == "echo_message":
            print(f"Echoing: {action_data['message']}")

    print("\nAgent standalone test finished.")
