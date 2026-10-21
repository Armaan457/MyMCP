import argparse
import os
import sys
from src.mcp_server.resources import register_resources
from src.mcp_server.tools import register_tools
from src.mcp_server.prompts import register_prompts
from mcp.server.mcpserver import MCPServer

mcp = MCPServer(
    name="Portfolio MCP Server",
    instructions="Developer portfolio MCP server providing access to resume, GitHub repos, and LeetCode performance."
)

register_resources(mcp)
register_tools(mcp)
register_prompts(mcp)

def main():
    parser = argparse.ArgumentParser(description="Run Portfolio MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport type (stdio or sse)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind for SSE transport"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", 7860)),
        help="Port to bind for SSE transport"
    )
    args = parser.parse_args()

    print(f"Starting Portfolio MCP Server ({args.transport})...", file=sys.stderr)
    if args.transport == "sse":
        mcp.run(transport=args.transport, host=args.host, port=args.port)
    else:
        mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
