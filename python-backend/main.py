import sys
import json # Though not strictly used for simple string responses yet
from playwright.sync_api import sync_playwright

def main():
    print("Python backend started. Waiting for messages...", file=sys.stderr, flush=True)
    while True:
        try:
            line = sys.stdin.readline()
            if not line:  # Handles EOF (Ctrl+D)
                print("Python backend received EOF. Exiting.", file=sys.stderr, flush=True)
                break

            message = line.strip() # Remove trailing newline

            if not message: # Empty line after strip means it was just a newline or empty
                print("Python backend received empty line. Exiting.", file=sys.stderr, flush=True)
                break

            if message.startswith("navigate:"):
                url = message[len("navigate:"):].strip()
                if not url:
                    output_message = "Error: URL for navigation is missing."
                    sys.stdout.write(output_message + '\n')
                    sys.stdout.flush()
                    print("Received navigate command with empty URL.", file=sys.stderr, flush=True)
                    continue

                try:
                    print(f"Attempting to navigate to: {url}", file=sys.stderr, flush=True)
                    with sync_playwright() as p:
                        # Try launching with headless=False first as requested.
                        # If system dependencies are missing, this might fail.
                        browser = p.chromium.launch(headless=False)
                        page = browser.new_page()
                        page.goto(url, timeout=30000) # 30s timeout for navigation

                        # page.wait_for_timeout(5000) # Initially try without this explicit wait

                        output_message = f"Successfully navigated to {url}"
                        sys.stdout.write(output_message + '\n')

                        browser.close() # Ensure browser is closed

                except Exception as e:
                    error_message_stdout = f"Error navigating to {url}: {type(e).__name__} - {e}"
                    sys.stdout.write(error_message_stdout + '\n')
                    print(f"Playwright error while navigating to {url}: {e}", file=sys.stderr, flush=True)
                finally:
                    sys.stdout.flush() # Ensure flush happens for both success and error to stdout
            else:
                processed_message = f"Python backend received: {message}"
                sys.stdout.write(processed_message + '\n')
                sys.stdout.flush()

        except Exception as e:
            # This outer exception is for issues like readline() failing or other unexpected errors
            print(f"Python backend general error: {e}", file=sys.stderr, flush=True)
            # It might be good to also send a generic error to stdout if appropriate
            # sys.stdout.write("Python backend encountered an unrecoverable error.\n")
            # sys.stdout.flush()
            # For now, continue, but for critical errors, breaking might be better.

if __name__ == "__main__":
    main()
