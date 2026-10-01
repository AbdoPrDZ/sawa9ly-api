"""The MCP server.

Import `McpServer` from here rather than from `src.mcp.server`: this is the
layer's front door, and it is the only name another module should need. Building
the server touches the database, so it is a call and not an import side effect.
"""

from src.mcp.server import McpServer


__all__ = [
  "McpServer",
]
