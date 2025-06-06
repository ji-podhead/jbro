# python-backend/mcps/__init__.py
from .mcp_base import MCPBase, MCPToolInfo, MCPToolParameterInfo # Expose base classes if needed
from .web_scraper_mcp import WebScraperMCP
from .file_system_mcp import FileSystemMCP

# This list could be used for auto-discovery or registration by an MCP manager.
# For now, it just makes them easily importable via `from mcps import ...`
__all__ = [
    "MCPBase",
    "MCPToolInfo",
    "MCPToolParameterInfo",
    "WebScraperMCP",
    "FileSystemMCP"
]

# Later, this could be a list or dict of registered MCP instances or classes:
# available_mcp_classes = [WebScraperMCP, FileSystemMCP]
#
# available_mcps_instances = {
#     mcp_class().mcp_name: mcp_class() for mcp_class in available_mcp_classes
# }
#
# def get_mcp_instance(name: str):
#    return available_mcps_instances.get(name)

# Example of how one might access them (for conceptual understanding):
# if __name__ == '__main__':
#     print("Registered MCPs (conceptual):")
#     for name, mcp_instance in available_mcps_instances.items():
#         print(f"- {name}: {mcp_instance.mcp_description}")
#         for tool_name in mcp_instance.get_tools().keys():
#             print(f"  - Tool: {tool_name}")

```
