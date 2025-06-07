import json
import re # Import regular expression module
import logging # Added for self.logger
from typing import Optional, List # Added for type hinting

from . import gmail_integration # For integration within the package
# import gmail_integration # For standalone testing if gmail_integration.py is in PYTHONPATH
from typing import Dict, Any, Callable # For MCPs
# Attempt to import MCPs. This structure assumes `mcps` is a package sibling to `agent.py`
try:
    from .mcps import WebScraperMCP, FileSystemMCP #, available_mcp_classes
    # from .mcps import available_mcps_instances # If using instance registration in mcps/__init__.py
except ImportError:
    WebScraperMCP = None
    FileSystemMCP = None
    # available_mcps_instances = {}
    logging.getLogger(__name__).warning("Could not import MCPs. MCP functionalities will be unavailable.")


class Agent:
    def __init__(self):
        """
        Initializes the Agent, its logger, Gmail service, and loads MCPs.
        """
        self.logger = logging.getLogger(__name__)
        if not logging.getLogger().hasHandlers():
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        self.gmail_service = gmail_integration.get_gmail_service()
        if self.gmail_service:
            self.logger.info("Agent: Gmail service initialized successfully.")
        else:
            self.logger.warning("Agent: Gmail service could not be initialized. Email features will be unavailable.")

        self.mcps: Dict[str, Any] = self._load_mcps() # MCP instances
        self.logger.info(f"Loaded {len(self.mcps)} MCPs: {list(self.mcps.keys())}")

    def generate_assisted_text(self, prompt: str) -> str:
        """
        Generates text based on a prompt using mock logic.
        In a real implementation, this would call an LLM.
        """
        self.logger.info(f"Agent received Write Assist prompt: '{prompt[:100]}...'")

        prompt_lower = prompt.lower()

        if "dragon" in prompt_lower and ("story" in prompt_lower or "tale" in prompt_lower):
            return ("Once upon a time, in a land of high mountains and deep valleys, "
                    "lived a friendly dragon named Sparky. Sparky loved to collect shiny pebbles and read ancient scrolls. "
                    "Unlike other dragons, Sparky preferred tea parties over terrorizing villages.")
        elif "python lists" in prompt_lower and ("explain" in prompt_lower or "what are" in prompt_lower):
            return ("Python lists are ordered, mutable collections of items. They can hold items of different types. "
                    "Example: my_list = [1, 'hello', 3.14]. You can append, insert, remove, and sort items.")
        elif "summarize" in prompt_lower and len(prompt) > 50 : # very basic check for a longer text to summarize
             return f"Mock summary for: '{prompt[:50]}...' -> This text has been summarized effectively by the mock AI."
        else:
            # Default fallback response
            return (f"Mock response for prompt '{prompt[:30]}...': This is some AI-generated text based on your input. "
                    "In a real system, an LLM would provide a more sophisticated and contextually relevant answer here. "
                    "For instance, it could elaborate, create, or summarize based on the prompt's intent.")

    def _load_mcps(self) -> Dict[str, Any]:
        """
        Loads and initializes available MCPs.
        In a more dynamic system, this could discover MCPs in the mcps package.
        For now, it manually instantiates the known ones.
        """
        loaded_mcps: Dict[str, Any] = {}
        if WebScraperMCP:
            try:
                scraper = WebScraperMCP()
                loaded_mcps[scraper.mcp_name] = scraper
            except Exception as e:
                self.logger.error(f"Failed to initialize WebScraperMCP: {e}")

        if FileSystemMCP:
            try:
                fs_mcp = FileSystemMCP()
                loaded_mcps[fs_mcp.mcp_name] = fs_mcp
            except Exception as e:
                self.logger.error(f"Failed to initialize FileSystemMCP: {e}")

        # Alternatively, if using a registration dict in mcps/__init__.py:
        # for name, instance in available_mcps_instances.items():
        #     loaded_mcps[name] = instance

        return loaded_mcps

    def _get_all_mcp_tool_definitions_for_llm(self) -> List[Dict[str, Any]]:
        """
        Generates a list of tool definitions from all loaded MCPs,
        formatted in a way suitable for an LLM's tool/function calling feature.
        """
        all_tool_defs: List[Dict[str, Any]] = []
        if not self.mcps: # Ensure self.mcps is populated
            self.logger.warning("_get_all_mcp_tool_definitions_for_llm called when self.mcps is empty.")
            return all_tool_defs

        for mcp_name, mcp_instance in self.mcps.items():
            if not hasattr(mcp_instance, 'list_tools') or not callable(mcp_instance.list_tools):
                self.logger.warning(f"MCP '{mcp_name}' (type: {type(mcp_instance)}) does not have a valid list_tools method. Skipping.")
                continue

            try:
                mcp_tools_info = mcp_instance.list_tools() # List[MCPToolInfo]
                for tool_info in mcp_tools_info:
                    properties = {}
                    required_params = []
                    if tool_info.parameters: # Ensure parameters is not None
                        for param_name, param_detail in tool_info.parameters.items():
                            # Basic type mapping, can be expanded
                            param_type = "string" # default
                            if param_detail.type in ["int", "integer", "number"]: param_type = "integer"
                            if param_detail.type in ["float", "double"]: param_type = "number"
                            if param_detail.type == "bool": param_type = "boolean"
                            if "List" in param_detail.type or "list" in param_detail.type : param_type = "array" # very basic

                            properties[param_name] = {
                                "type": param_type,
                                "description": param_detail.description
                            }
                            if param_detail.required:
                                required_params.append(param_name)

                    llm_tool_def = {
                        # "type": "function", # Standard for OpenAI, could be "tool" for others
                        "function": {
                            "name": f"{mcp_name}__{tool_info.name}", # Convention: MCPName__tool_name
                            "description": tool_info.description,
                            "parameters": {
                                "type": "object",
                                "properties": properties,
                            }
                        }
                    }
                    if required_params: # Add required field only if there are required parameters
                        llm_tool_def["function"]["parameters"]["required"] = required_params

                    all_tool_defs.append(llm_tool_def)
            except Exception as e:
                self.logger.error(f"Error processing tools for MCP '{mcp_name}': {e}", exc_info=True)
        return all_tool_defs

    def execute_mcp_tool_call(self, tool_name_full: str, arguments: Dict[str, Any]) -> Any:
        """
        Executes a tool from an MCP.
        tool_name_full: The combined name, e.g., "WebScraperMCP__get_text_from_element".
        arguments: A dictionary of arguments for the tool.
        """
        self.logger.info(f"Attempting to execute MCP tool: '{tool_name_full}' with args: {arguments}")
        try:
            mcp_name, actual_tool_name = tool_name_full.split("__", 1)
        except ValueError:
            self.logger.error(f"Invalid full tool name format: '{tool_name_full}'. Expected 'MCPName__tool_name'.")
            return f"Error: Invalid tool name format '{tool_name_full}'."

        mcp_instance = self.mcps.get(mcp_name)
        if not mcp_instance:
            self.logger.error(f"MCP '{mcp_name}' not found.")
            return f"Error: MCP '{mcp_name}' not found."

        # Ensure get_tools method exists and is callable
        if not hasattr(mcp_instance, 'get_tools') or not callable(mcp_instance.get_tools):
            self.logger.error(f"MCP '{mcp_name}' does not have a valid get_tools method.")
            return f"Error: MCP '{mcp_name}' is not correctly configured (missing get_tools)."

        tools_dict = mcp_instance.get_tools()
        if not isinstance(tools_dict, dict):
            self.logger.error(f"MCP '{mcp_name}'.get_tools() did not return a dictionary.")
            return f"Error: MCP '{mcp_name}' tools are not correctly configured."

        tool_method = tools_dict.get(actual_tool_name)
        if not tool_method or not callable(tool_method):
            self.logger.error(f"Tool '{actual_tool_name}' not found or not callable in MCP '{mcp_name}'.")
            return f"Error: Tool '{actual_tool_name}' not found in MCP '{mcp_name}'."

        try:
            # Future: Add argument validation against MCPToolInfo.parameters here.
            result = tool_method(**arguments)
            self.logger.info(f"MCP tool '{tool_name_full}' executed successfully. Result type: {type(result)}")
            return result
        except Exception as e:
            self.logger.error(f"Error executing MCP tool '{tool_name_full}': {e}", exc_info=True)
            return f"Error during {tool_name_full} execution: {e}"

    def check_semantic_condition(self, condition_description: str, required_tools_mcps: Optional[List[str]] = None) -> bool:
        """
        Checks if a given semantic condition is met using mock logic.
        """
        self.logger.info(f"Agent checking semantic condition: '{condition_description}' with tools: {required_tools_mcps}")

        condition_lower = condition_description.lower()

        # Example Condition 1: "Is there a new email from 'boss@example.com'?"
        email_condition_match = re.match(r"is there a new email from\s+['\"]?([^'\"@]+@[^'\"@]+\.[^'\"@]+)['\"]?", condition_lower)
        if email_condition_match:
            extracted_sender = email_condition_match.group(1)
            self.logger.info(f"Mock check for new email from: {extracted_sender}")
            if not self.gmail_service:
                self.logger.warning("Gmail service not available for semantic check.")
                return False # Cannot check without service

            try:
                # Simulate checking only the most recent email for this mock
                recent_emails = gmail_integration.list_recent_emails(self.gmail_service, count=1)
                if recent_emails and not recent_emails[0].startswith("Error:") and not recent_emails[0].startswith("No new messages"):
                    # This is a very basic mock. Real parsing of 'From' header is needed.
                    # Assuming list_recent_emails returns strings like "From: Actual Sender <actual@example.com>..."
                    latest_email_summary = recent_emails[0].lower()
                    if extracted_sender in latest_email_summary: # Simple substring check for mock
                        self.logger.info(f"Mock check: Found email potentially from '{extracted_sender}'. Assuming condition MET for mock.")
                        return True
                    else:
                        self.logger.info(f"Mock check: Latest email summary did not match '{extracted_sender}'.")
                        return False
                else:
                    self.logger.info(f"Mock check: No new emails found or error fetching: {recent_emails}")
                    return False
            except Exception as e:
                self.logger.error(f"Error during mock email check for semantic condition: {e}")
                return False

        # Example Condition 2: "Has 'project_alpha_status.txt' been updated today?"
        file_update_match = re.match(r"has\s+['\"]?([^'\"]+\.txt)['\"]?\s+been updated today", condition_lower)
        if file_update_match:
            extracted_filename = file_update_match.group(1)
            self.logger.info(f"Mock check: Has '{extracted_filename}' been updated today?")
            if extracted_filename == 'project_alpha_status.txt':
                self.logger.info("Mock check: Assuming 'project_alpha_status.txt' was updated today. Condition MET.")
                return True
            else:
                self.logger.info(f"Mock check: Filename '{extracted_filename}' not the one we're mocking. Condition FALSE.")
                return False

        self.logger.warning(f"Unknown semantic condition for mock processing: '{condition_description}'")
        return False


    def process_message(self, message_text: str) -> str:
        """
        Processes a raw message string and returns a JSON string representing the action to take.
        This acts as a mock LLM, parsing commands and determining tool usage.
        """
        cleaned_message = message_text.strip().lower()
        original_message_text = message_text.strip() # Keep original casing for echo

        # --- Natural Language Workflow Creation Attempt ---
        # Pattern to capture: "create workflow <name> to <action_description> on schedule <cron_string>"
        # Using re.IGNORECASE for the whole pattern.
        # Making "named", "name", "on schedule", "schedule is", "cron" optional or flexible.
        workflow_pattern = re.compile(
            r"(?:create|new|add)?\s*workflow\s+(?:named\s+|name\s+)?['\"]?(?P<name>[^'\"@]+?)['\"]?"  # Name can't have @ (often in cron)
            r"\s+to\s+(?P<action_description>.+?)"
            r"\s+(?:on\s+schedule|schedule\s+is|cron)\s+(?P<cron_string>"
            r"(?:\s*(?:[^\s]+|\*)){5,6}" # 5 or 6 cron parts
            r")\s*$", # Ensure it's the end of the string or allow for minor trailing spaces
            re.IGNORECASE
        )
        nl_workflow_match = workflow_pattern.match(original_message_text) # Use original for better name extraction before lowercasing everything

        if nl_workflow_match:
            name = nl_workflow_match.group("name").strip()
            action_description = nl_workflow_match.group("action_description").strip().lower() # Lowercase for action parsing
            cron_string = nl_workflow_match.group("cron_string").strip()

            inferred_target_connector = None
            inferred_action_type = None
            inferred_params = {}

            # Infer action from action_description
            nav_match = re.match(r"navigate\s+to\s+(https?://[^\s]+)", action_description)
            list_emails_match = re.match(r"list\s+(?:my\s+)?emails(?:\s+count\s+(\d+))?", action_description)

            if nav_match:
                inferred_target_connector = "BROWSER"
                inferred_action_type = "NAVIGATE"
                inferred_params = {"url": nav_match.group(1)}
            elif list_emails_match:
                inferred_target_connector = "GMAIL"
                inferred_action_type = "LIST_EMAILS"
                count_str = list_emails_match.group(1)
                inferred_params = {"count": int(count_str) if count_str else 5}
            else:
                action_json = {"tool": "echo_message", "message": f"Sorry, I couldn't understand the action: '{nl_workflow_match.group('action_description').strip()}'"}
                return json.dumps(action_json)

            # Validate cron string (basic check for 5 or 6 parts)
            if not (5 <= len(cron_string.split()) <= 6):
                action_json = {"tool": "echo_message", "message": f"Invalid cron string format: '{cron_string}'. Must have 5 or 6 parts."}
                return json.dumps(action_json)

            workflow_data = {
                "name": name,
                "trigger": {"trigger_type": "cron", "config": {"cron_expression": cron_string}},
                "target_connector": inferred_target_connector,
                "action": {"action_type": inferred_action_type, "params": inferred_params},
                "is_enabled": True
            }
            return json.dumps({"tool": "add_workflow", "data": workflow_data})

        # --- Existing Command Processing ---

        # --- Mock LLM + MCP Tool Call Logic ---
        # This section simulates how an LLM might decide to use an MCP tool based on user input.

        # Example 1: "scrape text from element #headline on http://example.com"
        scrape_match = re.match(r"scrape text from element\s+(.+?)\s+on\s+(https?://[^\s]+)", cleaned_message)
        if scrape_match:
            selector = scrape_match.group(1).strip()
            url = scrape_match.group(2).strip()
            self.logger.info(f"Mock LLM: Decided to use WebScraperMCP__get_text_from_element for: {original_message_text}")
            # This structure mimics what an LLM like Gemini or OpenAI might return
            # when it decides to call a function/tool.
            mock_llm_function_call = {
                "name": "WebScraperMCP__get_text_from_element",
                "arguments": {"url": url, "selector": selector}
            }
            tool_result = self.execute_mcp_tool_call(mock_llm_function_call['name'], mock_llm_function_call['arguments'])
            return json.dumps({"tool": "echo_message", "message": f"MCP Tool Result: {tool_result}"})

        # Example 2: "read file path/to/my_document.txt"
        # The FileSystemMCP has basic security. Test with a path relative to the project root or a known safe dir.
        # e.g., "read file python-backend/mcps/test_files/some_file.txt"
        read_file_match = re.match(r"read file\s+([\w\/\.\-\_]+)", cleaned_message)
        if read_file_match:
            file_path = read_file_match.group(1).strip()
            self.logger.info(f"Mock LLM: Decided to use FileSystemMCP__read_file for: {original_message_text}")
            mock_llm_function_call = {
                "name": "FileSystemMCP__read_file",
                "arguments": {"path": file_path}
            }
            tool_result = self.execute_mcp_tool_call(mock_llm_function_call['name'], mock_llm_function_call['arguments'])
            return json.dumps({"tool": "echo_message", "message": f"MCP Tool Result for '{file_path}': {tool_result}"})

        # Example 3: "list links on http://example.com"
        list_links_match = re.match(r"list links on\s+(https?://[^\s]+)", cleaned_message)
        if list_links_match:
            url = list_links_match.group(1).strip()
            self.logger.info(f"Mock LLM: Decided to use WebScraperMCP__get_links_on_page for: {original_message_text}")
            mock_llm_function_call = {
                "name": "WebScraperMCP__get_links_on_page",
                "arguments": {"url": url}
            }
            tool_result = self.execute_mcp_tool_call(mock_llm_function_call['name'], mock_llm_function_call['arguments'])

            # Ensure result (list or error string) is JSON serializable for echo
            if isinstance(tool_result, list):
                # Truncate if too many links for a chat message
                if len(tool_result) > 10:
                    result_str = ", ".join(tool_result[:10]) + f"... and {len(tool_result)-10} more."
                else:
                    result_str = ", ".join(tool_result)
                if not tool_result: result_str = "No links found."
            else: # It's likely an error string
                result_str = str(tool_result)
            return json.dumps({"tool": "echo_message", "message": f"MCP Tool Result (Links on {url}): {result_str}"})

        # (Conceptual for real LLM) Get formatted tools:
        # available_tools_for_llm = self._get_all_mcp_tool_definitions_for_llm()
        # # In a real scenario, you'd send message_text + available_tools_for_llm to an LLM.
        # # The LLM would respond, possibly with a function call object.
        # # llm_response = call_llm(message_text, available_tools_for_llm)
        # # if llm_response.has_function_call:
        # #     tool_result = self.execute_mcp_tool_call(llm_response.function_call.name, llm_response.function_call.arguments)
        # #     # ... then potentially send tool_result back to LLM for summarization or directly to user
        # # else:
        # #     return json.dumps({"tool": "echo_message", "message": llm_response.text_content})


        # Direct command for semantic check (for testing)
        if cleaned_message.startswith("agent check condition:"):
            condition_desc_from_chat = original_message_text[len("agent check condition:"):].strip()
            if not condition_desc_from_chat:
                 return json.dumps({"tool": "echo_message", "message": "Error: No condition description provided for 'agent check condition'."})

            # For this direct test, we don't have required_tools_mcps from a workflow.
            result = self.check_semantic_condition(condition_desc_from_chat, None)
            return json.dumps({"tool": "echo_message", "message": f"Condition '{condition_desc_from_chat}' evaluated to: {result}"})


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

        # Workflow CRUD commands from renderer
        # Expected format: "agent_command: <command_type> <json_payload>"
        # e.g., "agent_command: create workflow {\"name\": \"Test\", ...}"
        elif cleaned_message.startswith("agent_command: create workflow "):
            try:
                # Extract the JSON part of the message
                json_payload_str = original_message_text[len("agent_command: create workflow "):].strip()
                workflow_data = json.loads(json_payload_str)
                action = {"tool": "add_workflow", "data": workflow_data}
            except json.JSONDecodeError as e:
                action = {"tool": "echo_message", "message": f"Error: Invalid JSON payload for create workflow. {e}"}
            except Exception as e: # Catch any other unexpected errors during parsing
                 action = {"tool": "echo_message", "message": f"Error processing 'create workflow' command: {e}"}

        elif cleaned_message.startswith("agent_command: update workflow "):
            try:
                json_payload_str = original_message_text[len("agent_command: update workflow "):].strip()
                workflow_data = json.loads(json_payload_str)
                if 'id' not in workflow_data: # ID is essential for update
                    action = {"tool": "echo_message", "message": "Error: 'id' missing in update workflow data."}
                else:
                    action = {"tool": "update_workflow", "data": workflow_data}
            except json.JSONDecodeError as e:
                action = {"tool": "echo_message", "message": f"Error: Invalid JSON payload for update workflow. {e}"}
            except Exception as e:
                 action = {"tool": "echo_message", "message": f"Error processing 'update workflow' command: {e}"}


        elif cleaned_message.startswith("agent_command: delete workflow "):
            try:
                json_payload_str = original_message_text[len("agent_command: delete workflow "):].strip()
                workflow_data = json.loads(json_payload_str) # Expects {"id": "workflow_id_to_delete"}
                if 'id' not in workflow_data:
                     action = {"tool": "echo_message", "message": "Error: 'id' missing in delete workflow data."}
                else:
                    action = {"tool": "delete_workflow", "data": {"id": workflow_data['id']}}
            except json.JSONDecodeError as e:
                action = {"tool": "echo_message", "message": f"Error: Invalid JSON payload for delete workflow. {e}"}
            except Exception as e:
                 action = {"tool": "echo_message", "message": f"Error processing 'delete workflow' command: {e}"}

        # Settings commands
        elif cleaned_message == "get settings":
            action = {"tool": "get_all_settings"}

        elif cleaned_message.startswith("agent_command: assist_write_generate "):
            try:
                payload_str = original_message_text[len("agent_command: assist_write_generate "):].strip()
                data = json.loads(payload_str)
                prompt = data.get("prompt")

                if prompt is not None: # Check if prompt is None, not just falsy (empty string is a valid prompt)
                    generated_text = self.generate_assisted_text(prompt)
                    response_payload = {"type": "write_assist_response", "text": generated_text}
                else:
                    self.logger.warning("No prompt provided for assist_write_generate.")
                    response_payload = {"type": "write_assist_error", "error": "No prompt provided for text generation."}
                action = {"tool": "echo_message", "message": json.dumps(response_payload)}
            except json.JSONDecodeError as e:
                self.logger.error(f"JSONDecodeError in assist_write_generate: {e}. Payload: {payload_str}")
                error_payload = {"type": "write_assist_error", "error": f"Invalid JSON payload for text generation: {e}."}
                action = {"tool": "echo_message", "message": json.dumps(error_payload)}
            except Exception as e:
                self.logger.error(f"Error in assist_write_generate: {e}")
                error_payload = {"type": "write_assist_error", "error": f"An unexpected error occurred: {e}."}
                action = {"tool": "echo_message", "message": json.dumps(error_payload)}

        elif cleaned_message.startswith("update setting "): # e.g., "update setting theme to dark"
            # This is a very basic parser. A more robust solution might use regex or more structure.
            parts = original_message_text.split(" ", 4) # "update", "setting", "<key>", "to", "<value>"
            if len(parts) == 5 and parts[3].lower() == "to":
                key = parts[2]
                value_str = parts[4]
                # Attempt to convert value to bool or number if appropriate
                value: Any = None
                if value_str.lower() == "true":
                    value = True
                elif value_str.lower() == "false":
                    value = False
                else:
                    try:
                        value = int(value_str)
                    except ValueError:
                        try:
                            value = float(value_str)
                        except ValueError:
                            value = value_str # Keep as string if not bool/number

                action = {"tool": "update_setting", "data": {"key": key, "value": value}}
            else:
                action = {"tool": "echo_message", "message": "Error: Invalid 'update setting' format. Use: 'update setting <key> to <value>'"}

        elif cleaned_message.startswith("agent_command: update setting "): # From UI
            try:
                json_payload_str = original_message_text[len("agent_command: update setting "):].strip()
                setting_data = json.loads(json_payload_str) # Expects {"key": "...", "value": ...}
                if 'key' not in setting_data or 'value' not in setting_data:
                     action = {"tool": "echo_message", "message": "Error: 'key' or 'value' missing in update setting data."}
                else:
                    action = {"tool": "update_setting", "data": {"key": setting_data['key'], "value": setting_data['value']}}
            except json.JSONDecodeError as e:
                action = {"tool": "echo_message", "message": f"Error: Invalid JSON for update setting. {e}"}
            except Exception as e:
                 action = {"tool": "echo_message", "message": f"Error processing 'update setting' command: {e}"}


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

    # Required for __main__ test block, to resolve relative paths for test file
    import pathlib # Already imported os at the top of FileSystemMCP, but good to ensure here too
    import os

    test_queries = [
        # NL Workflow creation tests
        "create workflow Morning News to navigate to https://news.google.com on schedule 0 7 * * *",
        "new workflow Check Mails to list my emails count 3 cron */15 * * * *",
        "workflow My Test to navigate to http://test.com schedule is * * * * *", # NL create
        "add workflow Another Test to list emails cron 0 0 * * 0", # Default count for list emails
        "workflow Bad Cron to navigate to https://example.com schedule is 1 2 3 4", # Bad cron
        "create workflow Unknown Action to do something weird on schedule * * * * *", # Unknown action
        "workflow MissingCron to navigate to https://example.com on schedule", # Missing cron string
        "workflow Name with \"quotes\" to navigate to https://quoted.com on schedule * * * * *",
        "workflow name_with_underscore to navigate to https://underscored.com cron * * * * *",
        "WORKFLOW CaseTest to navigate to https://casetest.com ON SCHEDULE * * * * *",


        # Existing tests
        "navigate to example.com",
        "search for python tutorials",
        "echo This is a test message",
        "list emails", # Direct command
        "show my emails",
        "list workflows",
        "agent_command: create workflow {\"name\": \"Test From Agent\", \"trigger\": {\"trigger_type\": \"cron\", \"config\": {\"cron_expression\": \"* * * * *\"}}, \"target_connector\": \"BROWSER\", \"action\": {\"action_type\": \"NAVIGATE\", \"params\": {\"url\": \"http://example.com/agent\"}}}",
        "agent_command: update workflow {\"id\": \"some-id\", \"name\": \"Updated Name\"}",
        "agent_command: delete workflow {\"id\": \"some-id-to-delete\"}",
        "agent_command: create workflow malformed_json",

        "agent check condition: Is there a new email from 'boss@example.com'?",
        "agent check condition: Has 'project_alpha_status.txt' been updated today?",
        "agent check condition: Is the sky blue today?",
        "agent check condition:",

        # Settings tests
        "get settings", # Direct command
        "update setting theme to dark", # Direct command
        "update setting notifications_enabled to false",
        "update setting llm_model_preference to gpt-4-turbo",
        "update setting new_feature_flag to true",
        "update setting count_value to 123",
        "update setting invalid format",
        "agent_command: update setting {\"key\": \"theme\", \"value\": \"from_ui\"}",

        # Write Assist tests
        f"agent_command: assist_write_generate {json.dumps({'type': 'generate_text', 'prompt': 'write a short story about a dragon'})}",
        f"agent_command: assist_write_generate {json.dumps({'type': 'generate_text', 'prompt': 'explain python lists'})}",
        f"agent_command: assist_write_generate {json.dumps({'type': 'generate_text', 'prompt': 'another topic'})}",
        f"agent_command: assist_write_generate {json.dumps({'type': 'generate_text', 'prompt': ''})}",
        f"agent_command: assist_write_generate {json.dumps({'type': 'generate_text'})}",

        # MCP related tests (will trigger mock LLM logic)
        "scrape text from element h1 on http://example.com",
        # Path for FileSystemMCP.read_file test. This path is relative to project root.
        "read file python-backend/mcps/test_files/fs_mcp_test_file.txt",
        "list links on http://example.com",
        # "use WebScraperMCP.get_text_from_element to http://example.com with selector p", # Old format, now handled by regex
        # "use FileSystemMCP.write_file to python-backend/mcps/test_files/agent_test_write.txt with content This_is_a_test", # Needs more complex parsing

        "what is the meaning of life?" # Fallback
    ]

    # Setup for FileSystemMCP test within agent test
    # Ensure the test file exists for the "read file" test case via MCP
    # The path used in test_queries for reading must match this.
    # FileSystemMCP's tool_read_file has basic security to only allow relative paths.
    # It expects paths relative to where main.py is run (project root typically)

    # Determine project root assuming agent.py is in python-backend/
    project_root = pathlib.Path(__file__).parent.parent
    test_file_for_agent_read = project_root / "python-backend/mcps/test_files/fs_mcp_test_file.txt"

    try:
        test_file_for_agent_read.parent.mkdir(parents=True, exist_ok=True)
        with open(test_file_for_agent_read, "w") as f:
            f.write("Content specifically for agent's FileSystemMCP.read_file test via mock LLM.")
        print(f"\nSETUP: Created or ensured '{test_file_for_agent_read}' exists for testing MCPs.\n")
    except Exception as e:
        print(f"\nSETUP ERROR: Could not create test file '{test_file_for_agent_read}': {e}\n")


    for query in test_queries:
        print(f"\nInput: \"{query}\"")
        action_json = agent_instance.process_message(query)
        action_data = json.loads(action_json)
        print(f"Action: {action_data}")
        if action_data["tool"] == "echo_message":
            print(f"Echoing: {action_data['message']}")

    print("\nAgent standalone test finished.")
