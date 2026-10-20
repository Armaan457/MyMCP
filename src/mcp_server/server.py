import argparse
import sys
from src.mcp_server.resources import register_resources
from mcp.server.mcpserver import MCPServer

mcp = MCPServer(
    name="Portfolio MCP Server",
    instructions="Developer portfolio MCP server providing access to resume, GitHub repos, and LeetCode performance."
)

register_resources(mcp)

def main():
    parser = argparse.ArgumentParser(description="Run Portfolio MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport type (stdio or sse)"
    )
    args = parser.parse_args()

    print(f"Starting Portfolio MCP Server ({args.transport})...", file=sys.stderr)
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
