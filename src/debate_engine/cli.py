"""Command-line interface for DebateEngine."""

import argparse

from debate_engine.orchestration.quick_critique import QuickCritiqueEngine


def main() -> None:
    """Entry point for the debate-engine CLI command."""
    from debate_engine import __version__

    parser = argparse.ArgumentParser(
        prog="debate-engine",
        description="DebateEngine Server - Structured Multi-Agent Critique & Consensus Engine",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show the version of debate-engine",
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

    # --- critique subcommand ---
    critique_parser = subparsers.add_parser(
        "critique",
        help="Run a quick critique on provided content",
    )
    critique_parser.add_argument(
        "--content",
        required=True,
        help="Content to critique",
    )
    critique_parser.add_argument(
        "--task-type",
        default="CODE_REVIEW",
        help="Type of task for critique",
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

    if args.version:
        print(f"debate-engine version {__version__}")
        return

    if args.command == "mcp":
        _run_mcp()
    elif args.command == "critique":
        _run_critique(args.content, args.task_type)
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


def _run_critique(content: str, task_type: str) -> None:
    """Run a quick critique on provided content."""
    import asyncio

    from debate_engine.schemas import CritiqueConfigSchema, TaskType

    # Create critique config
    config = CritiqueConfigSchema(
        content=content, task_type=TaskType(task_type) if task_type != "AUTO" else "AUTO"
    )

    engine = QuickCritiqueEngine()
    result = asyncio.run(engine.critique(config))

    print(f"Conclusion: {result.final_conclusion}")
    print(f"Confidence: {result.consensus_confidence * 100:.0f}%")


if __name__ == "__main__":
    main()
