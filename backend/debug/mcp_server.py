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
            "Project-specific debug server for Review Insight Tool (FastAPI + Next.js).\n\n"
            "QUICK START\n"
            "  Run `make debug` — starts backend with DEBUG_TRACE=true and frontend with\n"
            "  NEXT_PUBLIC_DEBUG_TRAIL=true. Both flags must be set for full debug coverage.\n\n"
            "FRONTEND DEBUG SELECTOR (CTRL+click purple highlight + crosshair cursor)\n"
            "  Enabled when NEXT_PUBLIC_DEBUG_TRAIL=true (set in frontend/.env.local).\n"
            "  1. Open the app at http://localhost:3000.\n"
            "  2. Hold CTRL — all cursors switch to crosshair.\n"
            "  3. CTRL+click any element — it gets a purple glow ([data-debug-sel='primary'])\n"
            "     and all its children get a dashed purple outline ([data-debug-sel='child']).\n"
            "  4. Each click appends to the selection. The snapshot is auto-POSTed to\n"
            "     /api/debug/ui-snapshot so MCP tools can read it immediately.\n"
            "  5. Double-tap CTRL (≤300ms) → deselect all / clear highlights.\n"
            "  6. ◉ Debug panel (bottom-left corner) → 'Selector' tab to inspect all\n"
            "     selected elements: tag, React component, CSS path, bounding rect.\n"
            "  Use debug_selector_status() to verify the selector is enabled and see the\n"
            "  latest snapshot. Use ui_snapshot() to read only the snapshot.\n\n"
            "BACKEND TRACING (requires DEBUG_TRACE=true)\n"
            "  health_probe() → is everything alive?\n"
            "  recent_traces(limit=5) → what just happened?\n"
            "  trace_journey('trace-id') → deep dive on one request\n"
            "  llm_call_log('biz-uuid') → why was that analysis slow?\n"
            "  mutation_log('biz-uuid') → what did we write to the DB?\n\n"
            "DATA TOOLS (always available)\n"
            "  system_status() · migration_status() · health_probe()\n"
            "  sandbox_catalog_summary() · recent_businesses(limit) · db_table_counts()\n"
            "  business_snapshot(id) · user_summary(email|id)\n\n"
            "MUTATING (guarded)\n"
            "  sandbox_reset_user(confirm=True, email|id) — offline mode only."
        ),
    )

    register_tools(mcp)
    mcp.run("stdio")


if __name__ == "__main__":
    main()
