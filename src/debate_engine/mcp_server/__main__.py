"""Entry point for running the DebateEngine MCP server via ``python -m``.

Usage::

    python -m debate_engine.mcp_server

This starts the MCP server with stdio transport, suitable for use as
an MCP subprocess in Claude Code, Cursor, or other MCP clients.
"""

from .server import mcp

if __name__ == "__main__":
    mcp.run(transport="stdio")
