"""Review Insight Tool — debug MCP server.

A project-specific introspection server for local development and staging debug sessions.
Communicates with Cursor over stdio. Never deployed to Railway.

Usage:
    cd backend/
    DEBUG_MCP=true python -m debug.mcp_server
"""

import os
import sys


def main() -> None:
    if os.environ.get("DEBUG_MCP") != "true":
        sys.stderr.write(
            "Error: DEBUG_MCP=true is required to start the debug server.\n"
            "This server is for local debug sessions only.\n"
        )
        sys.exit(1)

    from mcp.server.fastmcp import FastMCP

    from debug.tools import register_tools

    mcp = FastMCP(
        name="review-insight-debug",
        instructions=(
            "Project-specific debug server for Review Insight Tool. "
            "Use to inspect system config, migration state, sandbox data, "
            "business/user snapshots, and DB table counts. "
            "All tools are read-only except sandbox_reset_user, which requires confirm=True "
            "and only works in offline mode."
        ),
    )

    register_tools(mcp)
    mcp.run("stdio")


if __name__ == "__main__":
    main()
