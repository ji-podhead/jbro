from typing import Dict, Any, Callable, List, Optional
from .mcp_base import MCPBase, MCPToolInfo, MCPToolParameterInfo
from playwright.sync_api import sync_playwright, PlaywrightError # Import Playwright
import logging

logger = logging.getLogger(__name__)

class WebScraperMCP(MCPBase):
    @property
    def mcp_name(self) -> str:
        return "WebScraperMCP"

    @property
    def mcp_description(self) -> str:
        return "Provides tools for scraping web pages."

    # --- Tool Implementations (Placeholders) ---
    def tool_get_text_from_element(self, url: str, selector: str) -> str:
        """
        Retrieves the text content from a specific HTML element on a web page.
        (Currently a mock implementation).

        Args:
            url: The URL of the web page to scrape.
            selector: The CSS selector to identify the HTML element.

        Returns:
            The text content of the selected element, or an error message string.
        """
        logger.info(f"Attempting to get text from element '{selector}' at URL '{url}'")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True) # MCP tools should be headless by default
                page = browser.new_page()
                try:
                    page.goto(url, timeout=60000, wait_until="domcontentloaded")
                    element = page.query_selector(selector)
                    if element:
                        text_content = element.inner_text()
                        logger.info(f"Successfully retrieved text from '{selector}' at '{url}'. Length: {len(text_content)}")
                        return text_content.strip()
                    else:
                        logger.warning(f"Element with selector '{selector}' not found on {url}.")
                        return f"Error: Element with selector '{selector}' not found on {url}."
                except PlaywrightError as e: # More specific Playwright errors
                    logger.error(f"PlaywrightError while scraping {url} with selector {selector}: {e}")
                    return f"PlaywrightError: {str(e).splitlines()[0]}" # Get a concise error message
                except Exception as e: # Catch other errors like network issues, timeouts not covered by PlaywrightError
                    logger.error(f"Unexpected error while scraping {url} with selector {selector}: {e}")
                    return f"Error: {str(e)}"
                finally:
                    if browser:
                        browser.close()
        except Exception as e: # Catch errors from sync_playwright() or browser launch
            logger.error(f"Error initializing Playwright or launching browser: {e}")
            return f"Fatal Error: Could not initialize browser. {str(e)}"


    def tool_get_links_on_page(self, url: str) -> List[str]:
        """
        Retrieves all unique hyperlinks (href attributes of <a> tags) from the given web page.

        Args:
            url: The URL of the web page to scrape.

        Returns:
            A list of unique URL strings, or a list containing a single error message string.
        """
        logger.info(f"Attempting to get all links from URL '{url}'")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                try:
                    page.goto(url, timeout=60000, wait_until="domcontentloaded")
                    raw_links = page.eval_on_selector_all("a[href]", "elements => elements.map(el => el.href)")

                    # Ensure links are absolute and unique
                    unique_absolute_links = set()
                    for link in raw_links:
                        try:
                            # Create an absolute URL if it's relative
                            absolute_link = page.urljoin(link)
                            unique_absolute_links.add(absolute_link)
                        except Exception: # Handle cases where urljoin might fail on malformed hrefs
                            logger.warning(f"Could not process link '{link}' on page '{url}'.")

                    logger.info(f"Found {len(unique_absolute_links)} unique links on {url}.")
                    return list(unique_absolute_links)
                except PlaywrightError as e:
                    logger.error(f"PlaywrightError while getting links from {url}: {e}")
                    return [f"PlaywrightError: {str(e).splitlines()[0]}"]
                except Exception as e:
                    logger.error(f"Unexpected error while getting links from {url}: {e}")
                    return [f"Error: {str(e)}"]
                finally:
                    if browser:
                        browser.close()
        except Exception as e:
            logger.error(f"Error initializing Playwright or launching browser for get_links_on_page: {e}")
            return [f"Fatal Error: Could not initialize browser for get_links_on_page. {str(e)}"]

    # --- Tool Registration and Information ---
    def get_tools(self) -> Dict[str, Callable[..., Any]]:
        return {
            "get_text_from_element": self.tool_get_text_from_element,
            "get_links_on_page": self.tool_get_links_on_page,
        }

    def get_tool_info(self, tool_name: str) -> Optional[MCPToolInfo]:
        if tool_name == "get_text_from_element":
            return MCPToolInfo(
                name="get_text_from_element",
                description="Retrieves text content from a specific HTML element on a page, identified by a CSS selector.",
                parameters={
                    "url": MCPToolParameterInfo(type="str", description="The URL of the web page.", required=True),
                    "selector": MCPToolParameterInfo(type="str", description="CSS selector for the target element.", required=True)
                }
                # returns_description="The extracted text content as a string."
            )
        elif tool_name == "get_links_on_page":
            return MCPToolInfo(
                name="get_links_on_page",
                description="Extracts all unique hyperlinks (href attributes of <a> tags) from the given web page.",
                parameters={
                    "url": MCPToolParameterInfo(type="str", description="The URL of the web page to scan for links.", required=True)
                }
                # returns_description="A list of unique URL strings."
            )
        return None

if __name__ == '__main__':
    # Configure basic logging for the test if run standalone
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    scraper = WebScraperMCP()
    print(f"--- {scraper.mcp_name} Test ---")
    print(f"Description: {scraper.mcp_description}")

    print("\nAvailable Tools (from list_tools):")
    for tool_info in scraper.list_tools():
        print(f"- Tool: {tool_info.name}, Description: {tool_info.description}")
        for param_name, param_info in tool_info.parameters.items():
            print(f"  - Param: {param_name} ({param_info.type}), Required: {param_info.required}, Desc: {param_info.description}")

    print("\n--- Live Test Execution Examples (requires internet) ---")

    # Test 1: Get text from element
    # Using a known public site that is less likely to change its structure quickly for tests.
    # Let's try to get the main heading from example.com
    test_url_1 = "http://example.com"
    test_selector_1 = "h1"
    print(f"\nTesting get_text_from_element with URL: {test_url_1}, Selector: {test_selector_1}")
    text_result = scraper.tool_get_text_from_element(url=test_url_1, selector=test_selector_1)
    print(f"Result: {text_result}")
    if "Example Domain" not in text_result and not text_result.startswith("Error"):
         print("WARNING: Test for get_text_from_element might not have returned expected 'Example Domain' heading.")

    # Test 2: Get links from page
    test_url_2 = "http://example.com" # example.com has one link
    print(f"\nTesting get_links_on_page with URL: {test_url_2}")
    links_result = scraper.tool_get_links_on_page(url=test_url_2)
    print(f"Found {len(links_result)} link(s):")
    for link in links_result:
        print(f"- {link}")
    if not any("iana.org" in link for link in links_result) and not (len(links_result)==1 and links_result[0].startswith("Error")):
        print(f"WARNING: Test for get_links_on_page from {test_url_2} might not have found the expected link to iana.org.")

    # Test 3: Non-existent element
    test_url_3 = "http://example.com"
    test_selector_3 = "h1.nonexistent" # This class likely doesn't exist on example.com's h1
    print(f"\nTesting get_text_from_element with non-existent selector: URL: {test_url_3}, Selector: {test_selector_3}")
    text_result_nonexistent = scraper.tool_get_text_from_element(url=test_url_3, selector=test_selector_3)
    print(f"Result for non-existent element: {text_result_nonexistent}")
    if not text_result_nonexistent.startswith("Error: Element"):
        print(f"WARNING: Test for non-existent element did not return the expected error message.")

    # Test 4: Invalid URL
    test_url_4 = "thisisnotaurl"
    print(f"\nTesting get_text_from_element with invalid URL: {test_url_4}")
    text_result_invalid_url = scraper.tool_get_text_from_element(url=test_url_4, selector="h1")
    print(f"Result for invalid URL: {text_result_invalid_url}")
    if not text_result_invalid_url.startswith("Error:") and not text_result_invalid_url.startswith("PlaywrightError:"):
         print(f"WARNING: Test for invalid URL did not return an error message as expected.")

    print("\n--- WebScraperMCP Test Complete ---")
```
