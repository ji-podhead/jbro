import os.path
import json
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_FILE = 'python-backend/gmail_credentials.json' # Path relative to project root
TOKEN_FILE = 'python-backend/gmail_token.json' # Path relative to project root

def get_gmail_service():
    """
    Shows basic usage of the Gmail API.
    Handles OAuth2 authentication and returns a Gmail API service object.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            logging.info("Loaded credentials from token file.")
        except Exception as e:
            logging.error(f"Error loading credentials from token file: {e}")
            creds = None

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logging.info("Refreshed expired credentials.")
            except Exception as e:
                logging.error(f"Error refreshing credentials: {e}")
                creds = None # Could not refresh
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                logging.error(f"Gmail credentials file not found at {CREDENTIALS_FILE}. "
                              "Please obtain credentials from Google Cloud Console and place them here.")
                return None
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                # The following line is intended for CLI execution and requires user interaction.
                # It will not run successfully in an automated environment without a user.
                # For this subtask, we assume this step would be done manually by a user if needed.
                logging.info("Attempting to run local server flow for new authorization. This requires user interaction.")
                # creds = flow.run_local_server(port=0)
                # Instead of running, we'll log that it's the point for user interaction.
                logging.warning("run_local_server() was not called in this automated step. Manual auth needed if no token.")
                # If run_local_server was called and succeeded, we would save the credentials.
                # For now, if we reach here without a token, it means manual intervention is needed.
                if not creds : # If we didn't get creds from refresh or successful run_local_server
                    logging.info("No valid token and new authorization flow was not completed.")
                    return None
            except Exception as e:
                logging.error(f"Error during authentication flow: {e}")
                return None

        # Save the credentials for the next run (if they were obtained/refreshed)
        if creds and creds.valid: # Ensure creds are valid before trying to save
            try:
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
                logging.info(f"Saved new/refreshed credentials to {TOKEN_FILE}")
            except Exception as e:
                logging.error(f"Error saving credentials to token file: {e}")

    if not creds or not creds.valid:
        logging.error("Failed to obtain valid Gmail credentials.")
        return None

    try:
        service = build('gmail', 'v1', credentials=creds)
        logging.info("Gmail service built successfully.")
        return service
    except Exception as e:
        logging.error(f"Error building Gmail service: {e}")
        return None

def list_recent_emails(service, count=5):
    """
    Lists recent emails from the user's mailbox.
    """
    if not service:
        return ["Error: Gmail service not available."]
    try:
        results = service.users().messages().list(userId='me', maxResults=count, q="is:unread").execute()
        messages_summary = []
        messages = results.get('messages', [])

        if not messages:
            return ["No new messages found."]

        for msg_ref in messages:
            msg = service.users().messages().get(userId='me', id=msg_ref['id'], format='metadata', metadataHeaders=['From', 'Subject', 'Date']).execute()
            snippet = msg.get('snippet', 'N/A')
            headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
            from_val = headers.get('From', 'N/A')
            subject_val = headers.get('Subject', 'N/A')
            date_val = headers.get('Date', 'N/A')
            messages_summary.append(f"From: {from_val}\nSubject: {subject_val}\nDate: {date_val}\nSnippet: {snippet.strip()}\n---")
        return messages_summary
    except HttpError as error:
        logging.error(f"An API error occurred: {error}")
        return [f"Gmail API Error: {error}"]
    except Exception as e:
        logging.error(f"An unexpected error occurred in list_recent_emails: {e}")
        return [f"Unexpected error listing emails: {e}"]


def read_email(service, message_id):
    """
    Placeholder for reading a specific email's full content.
    """
    if not service:
        return "Error: Gmail service not available."
    # Actual implementation will involve getting message parts, decoding base64, etc.
    return f"Reading email with ID: {message_id} (Not fully implemented yet, only snippet available via list command)"

def send_email(service, to, subject, body):
    """
    Placeholder for sending an email.
    """
    if not service:
        return "Error: Gmail service not available."
    # Actual implementation requires 'gmail.send' scope, message MIME construction, base64 encoding.
    return f"Sending email to {to} with subject '{subject}' (Not implemented yet - requires 'gmail.send' scope and more)"


if __name__ == '__main__':
    logging.info("Running Gmail integration test...")
    if not os.path.exists(CREDENTIALS_FILE):
        logging.warning(f"'{CREDENTIALS_FILE}' not found.")
        print(f"INSTRUCTIONS: To test Gmail integration, please obtain 'credentials.json' for the Gmail API")
        print(f"from Google Cloud Console and place it at '{CREDENTIALS_FILE}'.")
        print("You will also need to go through the OAuth consent flow the first time.")
    else:
        logging.info(f"Credentials file found at {CREDENTIALS_FILE}. Attempting to get service...")
        # The get_gmail_service function is designed not to trigger run_local_server in this automated context.
        # It will try to use an existing token.json or log that manual auth is needed.
        service = get_gmail_service()
        if service:
            print("Gmail service obtained. Attempting to list recent emails...")
            emails = list_recent_emails(service, count=3)
            if emails:
                print("\nRecent Emails:")
                for email_summary in emails:
                    print(email_summary)
            else:
                print("Could not retrieve emails or no emails found.")

            # Example placeholder calls (won't do much yet)
            print(f"\nPlaceholder read_email: {read_email(service, 'some_message_id')}")
            print(f"Placeholder send_email: {send_email(service, 'test@example.com', 'Test Subject', 'Test Body')}")

        else:
            print("Failed to get Gmail service. Check logs for details.")
            print(f"If this is the first time or token is invalid/expired, manual OAuth flow might be needed by running a script that calls get_gmail_service() in an environment allowing browser interaction.")

    logging.info("Gmail integration test finished.")
