"""DebateEngine MCP Server package.

Provides a thin MCP adapter layer that exposes DebateEngine's critique
and debate capabilities as MCP tools for use with Claude Code, Cursor,
and other MCP-compatible clients.

Usage::

    # Via CLI
    debate-engine mcp

    # Via Python module
    python -m debate_engine.mcp_server

    # Programmatic
    from debate_engine.mcp_server import create_mcp_server
    server = create_mcp_server()
"""

from typing import Any

from .server import mcp

__all__ = ["mcp"]


def create_mcp_server() -> Any:
    """Create and return the FastMCP server instance.

    This is the public factory function for programmatic access to the
    MCP server. The returned ``FastMCP`` instance can be run with any
    transport supported by the MCP SDK.

    Returns
    -------
    FastMCP
        The configured MCP server instance with all DebateEngine tools
        registered.
    """
    return mcp
