from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, List, Optional
from pydantic import BaseModel, Field # Assuming Pydantic is available

class MCPToolParameterInfo(BaseModel):
    """Describes a single parameter for an MCP tool."""
    type: str = Field(..., description="The expected Python type of the parameter (e.g., 'str', 'int', 'bool', 'List[str]').")
    description: str = Field(..., description="A brief description of what the parameter is for.")
    required: bool = Field(default=True, description="Whether the parameter is required.")
    # default_value: Optional[Any] = None # Could add later if needed

class MCPToolInfo(BaseModel):
    """Describes a tool provided by an MCP."""
    name: str = Field(..., description="The programmatic name of the tool.")
    description: str = Field(..., description="A user-friendly description of what the tool does.")
    parameters: Dict[str, MCPToolParameterInfo] = Field(default_factory=dict, description="A dictionary of parameters the tool accepts.")
    # Example parameters: {"url": MCPToolParameterInfo(type="str", description="URL to navigate to", required=True)}}
    # returns: Optional[str] = None # Description of what the tool returns, could also be a Pydantic model

class MCPBase(ABC):
    """
    Abstract Base Class for Multi-Capability Platforms (MCPs).
    MCPs are modules that provide a set of related tools (capabilities)
    that the agent can utilize.
    """

    @property
    @abstractmethod
    def mcp_name(self) -> str:
        """A unique and programmatic name for this MCP (e.g., 'WebScraperMCP')."""
        pass

    @property
    @abstractmethod
    def mcp_description(self) -> str:
        """A brief, user-friendly description of what this MCP does."""
        pass

    @abstractmethod
    def get_tools(self) -> Dict[str, Callable[..., Any]]:
        """
        Returns a dictionary where keys are tool names (strings) and
        values are the callable methods implementing these tools.
        Example: {"scrape_url": self.tool_scrape_url}
        """
        pass

    @abstractmethod
    def get_tool_info(self, tool_name: str) -> Optional[MCPToolInfo]:
        """
        Returns detailed structured information about a specific tool,
        including its description and parameters.
        """
        pass

    def list_tools(self) -> List[MCPToolInfo]:
        """
        Provides a list of MCPToolInfo for all tools offered by this MCP.
        This default implementation iterates over keys from get_tools()
        and calls get_tool_info() for each.
        """
        tools_info: List[MCPToolInfo] = []
        available_tools = self.get_tools()
        if available_tools: # Ensure get_tools() doesn't return None or empty during init
            for tool_name in available_tools.keys():
                info = self.get_tool_info(tool_name)
                if info:
                    tools_info.append(info)
        return tools_info

if __name__ == '__main__':
    # Example of how MCPToolParameterInfo and MCPToolInfo might be used (won't run directly here)
    param_url = MCPToolParameterInfo(type="str", description="The URL of the web page.", required=True)
    tool_example = MCPToolInfo(
        name="example_tool",
        description="This is an example tool.",
        parameters={"url": param_url, "retries": MCPToolParameterInfo(type="int", description="Number of retries.", required=False)}
    )
    print("--- MCP Base Definitions (Conceptual) ---")
    print(f"MCPToolInfo example: {tool_example.model_dump_json(indent=2)}")

    class DummyMCP(MCPBase):
        @property
        def mcp_name(self) -> str: return "DummyMCP"
        @property
        def mcp_description(self) -> str: return "A dummy MCP for testing."

        def tool_dummy_action(self, param1: str, param2: int = 0) -> str:
            return f"Dummy action called with {param1} and {param2}"

        def get_tools(self) -> Dict[str, Callable[..., Any]]:
            return {"dummy_action": self.tool_dummy_action}

        def get_tool_info(self, tool_name: str) -> Optional[MCPToolInfo]:
            if tool_name == "dummy_action":
                return MCPToolInfo(
                    name="dummy_action",
                    description="Performs a dummy action.",
                    parameters={
                        "param1": MCPToolParameterInfo(type="str", description="First parameter.", required=True),
                        "param2": MCPToolParameterInfo(type="int", description="Second parameter.", required=False)
                    }
                )
            return None

    dummy_mcp_instance = DummyMCP()
    print(f"\nDummy MCP Name: {dummy_mcp_instance.mcp_name}")
    print(f"Dummy MCP Description: {dummy_mcp_instance.mcp_description}")
    print(f"Dummy MCP Tools List: {dummy_mcp_instance.list_tools()}")
    for tool_info_item in dummy_mcp_instance.list_tools():
        print(f"Tool Info from list_tools: {tool_info_item.model_dump_json(indent=2)}")

    print(f"Dummy MCP tool_dummy_action via get_tools: {dummy_mcp_instance.get_tools()['dummy_action']('test', 123)}")

```
