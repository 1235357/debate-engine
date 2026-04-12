"""Command-line interface for DebateEngine."""

import argparse
import sys


def main() -> None:
    """Entry point for the debate-engine CLI command."""
    parser = argparse.ArgumentParser(
        prog="debate-engine",
        description="DebateEngine Server - Structured Multi-Agent Critique & Consensus Engine",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- serve subcommand (default) ---
    serve_parser = subparsers.add_parser(
        "serve",
        help="Start the FastAPI REST server (default)",
    )
    serve_parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port to bind the server to (default: 8765)",
    )
    serve_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    # --- mcp subcommand ---
    subparsers.add_parser(
        "mcp",
        help="Start the MCP server (stdio transport)",
    )

    # Legacy positional args (backward compat: debate-engine --host ... --port ...)
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind the server to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port to bind the server to (default: 8765)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    args = parser.parse_args()

    if args.command == "mcp":
        _run_mcp()
    else:
        # Default: run the REST API server
        _run_serve(args.host, args.port, args.reload)


def _run_serve(host: str, port: int, reload: bool) -> None:
    """Start the FastAPI REST server."""
    import uvicorn

    uvicorn.run(
        "debate_engine.api.server:app",
        host=host,
        port=port,
        reload=reload,
    )


def _run_mcp() -> None:
    """Start the MCP server with stdio transport."""
    from debate_engine.mcp_server.server import mcp

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
