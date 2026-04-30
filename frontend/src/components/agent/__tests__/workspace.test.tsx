import { renderToStaticMarkup } from "react-dom/server";
import { describe, it, expect } from "vitest";
import { Workspace } from "../Workspace";
import type { WorkspaceWidget } from "@/lib/agentTypes";

const noop = () => {};

function widget(id: string, position: number): WorkspaceWidget {
  return {
    id,
    widget_type: "summary_card",
    title: `Widget ${id}`,
    data: { summary: id },
    position,
    created_at: "2026-04-29T00:00:00Z",
  };
}

describe("Workspace render with error + existing widgets", () => {
  it("shows banner (not the full failed state) when widgets are present and reload errored", () => {
    const html = renderToStaticMarkup(
      <Workspace
        widgets={[widget("w1", 0)]}
        onDelete={noop}
        isLoading={false}
        error="Network: Failed to load."
        onRetry={noop}
      />,
    );

    expect(html).toContain("Network: Failed to load.");
    expect(html).toContain("Widget w1");
    expect(html).toContain("Dashboard");
    // Banner uses small inline padding (px-3 py-2); the full failed state uses
    // a thick dashed card. Asserting the small banner classes proves we did
    // not fall through to the catastrophic empty state.
    expect(html).toContain("px-3 py-2");
    expect(html).not.toContain("border-2 border-dashed border-red-300");
  });

  it("shows the full failed state when no widgets are present and reload errored", () => {
    const html = renderToStaticMarkup(
      <Workspace
        widgets={[]}
        onDelete={noop}
        isLoading={false}
        error="Network: Failed to load."
        onRetry={noop}
      />,
    );

    expect(html).toContain("Network: Failed to load.");
    expect(html).toContain("border-2 border-dashed border-red-300");
  });
});
