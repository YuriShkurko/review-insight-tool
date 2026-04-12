# Review Insight Tool

AI-powered review analysis platform. Fetches Google Maps reviews, runs AI analysis, and surfaces actionable insights for small business owners.

**Stack:** FastAPI (Python) backend · React/TypeScript frontend · Docker Compose

## MCP Tools

### locus
Codebase intelligence — use before tasks that require understanding structure, dependencies, or impact.

- `scan_project` — architecture overview, file graph, hot spots
- `get_dependencies` — dependency tree for a file or package
- `get_impact` — blast radius for a proposed change
- `get_coupling_table` — files that change together
- `diff_branches` — architecture diff between branches
- `get_cycles` — circular dependency detection
- `render_diagram` — Mermaid diagram of repo structure
- `triage` — map a natural-language intent to the right locus tool

**When to use:** before refactors, when tracing an unfamiliar call chain, before touching shared modules, when asked about dependencies or impact.

### scribe
Project-specific event/debug MCP server (workspace: `review-insight`, port 8787). Exposes runtime context — use when debugging live behavior, tracing review fetch/analysis flows, or inspecting emitted events.

**When to use:** debugging review pipeline issues, tracing analyze-all flows, inspecting backend event trail.
