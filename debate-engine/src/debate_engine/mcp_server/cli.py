import argparse
from .server import start_mcp_server


def main():
    """MCP Server CLI 入口"""
    parser = argparse.ArgumentParser(description="DebateEngine MCP Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to listen on")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    
    args = parser.parse_args()
    start_mcp_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
