import os
import pathlib # Import pathlib
from typing import Dict, Any, Callable, List, Optional
from .mcp_base import MCPBase, MCPToolInfo, MCPToolParameterInfo
import logging

logger = logging.getLogger(__name__)
# Define a base path for file operations for some level of sandboxing in tests,
# actual sandboxing for production use would need to be more robust.
# For testing, we'll write to a subdirectory within python-backend/mcps/
TEST_FILES_BASE_DIR = pathlib.Path(__file__).parent / "test_files"

class FileSystemMCP(MCPBase):
    @property
    def mcp_name(self) -> str:
        return "FileSystemMCP"

    @property
    def mcp_description(self) -> str:
        return "Provides tools for interacting with the local file system."

    # --- Tool Implementations (Placeholders/Mocks) ---
    def tool_read_file(self, path: str) -> str:
        """
        Reads the content of a file from the local file system.
        (Currently a mock implementation).

        Args:
            path: The absolute or relative path to the file.

        Returns:
            The content of the file as a string, or an error message string.
        """
        # Basic security: Disallow absolute paths or paths trying to go "up" (../) excessively
        # This is a very basic check and not a complete security solution.
        # A real application would need a robust sandboxing mechanism if paths are user-influenced.
        if os.path.isabs(path) or ".." in path:
            logger.error(f"Blocked attempt to access potentially unsafe path: {path}")
            return f"Error: Access to path '{path}' is not allowed. Only relative paths within a defined scope are permitted."

        # For this example, assume 'path' is relative to a specific, safe base directory.
        # If using the TEST_FILES_BASE_DIR for __main__ tests, that logic would be there.
        # For general use, the agent or caller should ensure paths are safe.
        # Here, we'll just try to resolve it directly.
        file_path = pathlib.Path(path)
        logger.info(f"Attempting to read file: {file_path.resolve()}")

        try:
            if not file_path.exists():
                logger.warning(f"File not found at '{file_path}'.")
                return f"Error: File not found at '{file_path}'."
            if not file_path.is_file():
                logger.warning(f"Path '{file_path}' is not a file.")
                return f"Error: Path '{file_path}' is not a file."

            content = file_path.read_text(encoding='utf-8')
            logger.info(f"Successfully read file '{file_path}'. Content length: {len(content)}")
            return content
        except IOError as e:
            logger.error(f"IOError reading file '{file_path}': {e}")
            return f"IOError: Could not read file '{file_path}'. {e}"
        except UnicodeDecodeError as e:
            logger.error(f"UnicodeDecodeError reading file '{file_path}': {e}")
            return f"UnicodeDecodeError: Could not decode file '{file_path}' as UTF-8. {e}"
        except Exception as e:
            logger.error(f"Unexpected error reading file '{file_path}': {e}", exc_info=True)
            return f"UnexpectedError: Could not read file '{file_path}'. {e}"

    def tool_write_file(self, path: str, content: str) -> bool:
        """
        Writes content to a file on the local file system.
        If the file exists, it's overwritten. If it doesn't, it's created.
        (Currently a mock implementation).

        Args:
            path: The absolute or relative path to the file.
            content: The string content to write to the file.

        Returns:
            True if writing was successful, False otherwise.
        """
        if os.path.isabs(path) or ".." in path: # Basic security
            logger.error(f"Blocked attempt to write to potentially unsafe path: {path}")
            # In a real scenario, might return an error message string or raise specific exception
            return False

        file_path = pathlib.Path(path)
        logger.info(f"Attempting to write to file: {file_path.resolve()}, Content length: {len(content)}")

        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding='utf-8')
            logger.info(f"Successfully wrote to file '{file_path}'.")
            return True
        except IOError as e:
            logger.error(f"IOError writing file '{file_path}': {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error writing file '{file_path}': {e}", exc_info=True)
            return False

    # --- Tool Registration and Information ---
    def get_tools(self) -> Dict[str, Callable[..., Any]]:
        return {
            "read_file": self.tool_read_file,
            "write_file": self.tool_write_file,
        }

    def get_tool_info(self, tool_name: str) -> Optional[MCPToolInfo]:
        if tool_name == "read_file":
            return MCPToolInfo(
                name="read_file",
                description="Reads the entire content of a specified file.",
                parameters={
                    "path": MCPToolParameterInfo(type="str", description="The path to the file to be read.", required=True)
                }
                # returns_description="The content of the file as a string, or an error message."
            )
        elif tool_name == "write_file":
            return MCPToolInfo(
                name="write_file",
                description="Writes the given text content to a specified file, overwriting it if it exists, or creating it if it doesn't.",
                parameters={
                    "path": MCPToolParameterInfo(type="str", description="The path to the file to be written.", required=True),
                    "content": MCPToolParameterInfo(type="str", description="The text content to write into the file.", required=True)
                }
                # returns_description="Boolean indicating success (True) or failure (False)."
            )
        return None

if __name__ == '__main__':
    # Configure basic logging for the test if run standalone
    if not logging.getLogger().hasHandlers(): # Ensure handlers aren't added multiple times
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    fs_mcp = FileSystemMCP()
    print(f"--- {fs_mcp.mcp_name} Test ---")
    print(f"Description: {fs_mcp.mcp_description}")

    print("\nAvailable Tools (from list_tools):")
    for tool_info in fs_mcp.list_tools():
        print(f"- Tool: {tool_info.name}, Description: {tool_info.description}")
        for param_name, param_info in tool_info.parameters.items():
            print(f"  - Param: {param_name} ({param_info.type}), Required: {param_info.required}, Desc: {param_info.description}")

    print("\n--- Live File System Test Execution Examples ---")

    # Define test file path within the sandboxed directory
    TEST_FILES_BASE_DIR.mkdir(parents=True, exist_ok=True) # Ensure base test dir exists
    test_file_path_str = "test_file.txt" # Relative path, will be resolved if MCP handles it, or use full path from base
    test_file_path = TEST_FILES_BASE_DIR / "test_file_for_fs_mcp.txt"


    # Test 1: Write a file
    test_content = "Hello from FileSystemMCP test!\nThis is a test file.\nLine 3."
    print(f"\n1. Testing write_file to: {test_file_path}")
    # Forcing path to be relative to the test dir for this test.
    # The tool itself currently expects paths that are either absolute or relative to CWD.
    # For robust testing, we construct a path we know is safe for the test environment.
    # We will use a path relative to the test_files_base_dir for the tool methods.
    # The tool's internal path handling should be designed for security.
    # For this test, we will pass paths relative to where the script is, inside test_files.
    # The tool's basic security check will prevent absolute paths or ".."
    # We will use paths like "test_files/my_test_file.txt" for the tool.

    # To make this test work with the tool's current relative path assumption (or lack of base_path):
    # We need to ensure the tool_write_file and tool_read_file operate within a known directory.
    # The tool itself should ideally prepend a base_path. Since it doesn't explicitly,
    # we'll pass paths that are relative but intended for the test_files_base_dir.
    # For the purpose of this test, let's assume paths passed to tools are relative to project root for simplicity of testing.
    # So, `python-backend/mcps/test_files/test_file.txt`

    # Let's use a path clearly within the allowed structure for the tool methods
    # Assuming current working directory for main.py is project root.
    # The tool methods themselves currently don't use TEST_FILES_BASE_DIR.
    # This test script should use paths that the tool can understand based on its current implementation.
    # The tool currently resolves paths relative to current working dir if not absolute.
    # To make tests reliable, we'll use paths relative to the `mcps` dir for the tool,
    # and the test block will manage files inside its `test_files` subdir.

    # Path for the tool to use, relative to where it might be called from (e.g., project root)
    # This is tricky because `os.getcwd()` in the tool might be different than `pathlib.Path(__file__).parent` here.
    # For the test, let's assume the tool operates relative to `python-backend` for simplicity.
    # No, the tool uses `pathlib.Path(path)` which means relative to CWD of main.py.
    # So, the test here should create files in a path that `main.py`'s CWD would resolve.
    # Let's assume CWD is project root when `main.py` runs.

    # Path for test setup (this script creates/deletes files here)
    managed_test_file = TEST_FILES_BASE_DIR / "fs_mcp_test_file.txt"
    # Path to pass to the tool (how the tool will see it, assuming CWD is project root)
    path_for_tool = f"python-backend/mcps/test_files/{managed_test_file.name}"


    print(f"Managed test file path: {managed_test_file}")
    print(f"Path to be passed to tool: {path_for_tool}")

    write_success = fs_mcp.tool_write_file(path=path_for_tool, content=test_content)
    print(f"write_file result: {write_success}")
    assert write_success, "Test 1 Failed: Writing file"

    # Test 2: Read the file back
    print(f"\n2. Testing read_file from: {path_for_tool}")
    read_content = fs_mcp.tool_read_file(path=path_for_tool)
    print(f"read_file content: '{read_content}'")
    assert read_content == test_content, "Test 2 Failed: Reading file content mismatch"

    # Test 3: Read a non-existent file
    non_existent_path = "python-backend/mcps/test_files/non_existent_file.txt"
    print(f"\n3. Testing read_file from non-existent path: {non_existent_path}")
    read_non_existent = fs_mcp.tool_read_file(path=non_existent_path)
    print(f"read_file for non-existent result: '{read_non_existent}'")
    assert "Error: File not found" in read_non_existent, "Test 3 Failed: Reading non-existent file"

    # Test 4: Write to a disallowed path (e.g., absolute or using ..)
    # This depends on the tool's security checks.
    # The current basic check in tool_write_file: `if os.path.isabs(path) or ".." in path:`
    print(f"\n4. Testing write_file to disallowed path (absolute): /tmp/test_disallowed.txt")
    disallowed_write_abs = fs_mcp.tool_write_file(path="/tmp/test_disallowed.txt", content="test")
    print(f"write_file to absolute path result: {disallowed_write_abs}")
    assert not disallowed_write_abs, "Test 4a Failed: Writing to absolute path should be disallowed"

    print(f"\n5. Testing write_file to disallowed path (relative ../): ../../test_disallowed.txt")
    disallowed_write_rel = fs_mcp.tool_write_file(path="../../test_disallowed.txt", content="test")
    print(f"write_file to relative ../ path result: {disallowed_write_rel}")
    assert not disallowed_write_rel, "Test 4b Failed: Writing to relative ../ path should be disallowed"


    # Clean up the created test file
    try:
        if managed_test_file.exists():
            managed_test_file.unlink()
            print(f"\nCleaned up test file: {managed_test_file}")
    except Exception as e:
        print(f"Error during cleanup: {e}")

    print("\n--- FileSystemMCP Test Complete ---")
```
