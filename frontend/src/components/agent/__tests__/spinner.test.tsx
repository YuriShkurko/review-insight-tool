import { renderToStaticMarkup } from "react-dom/server";
import { describe, it, expect } from "vitest";
import { ChatMessage } from "../ChatMessage";
import { ToolCallIndicator } from "../ToolCallIndicator";
import type { MessageItem } from "@/lib/agentTypes";

const noop = () => {};

const TOOL_CALL_ITEM: MessageItem = {
  id: "tc1",
  kind: "tool_call",
  name: "get_dashboard",
  args: {},
};

describe("ToolCallIndicator", () => {
  it("shows spinner when isStreaming=true", () => {
    const html = renderToStaticMarkup(
      <ToolCallIndicator name="get_dashboard" isStreaming={true} />,
    );
    expect(html).toContain("animate-spin");
    expect(html).not.toContain("✓");
  });

  it("shows checkmark when isStreaming=false", () => {
    const html = renderToStaticMarkup(
      <ToolCallIndicator name="get_dashboard" isStreaming={false} />,
    );
    expect(html).not.toContain("animate-spin");
    expect(html).toContain("✓");
  });

  it("renders known tool label", () => {
    const html = renderToStaticMarkup(
      <ToolCallIndicator name="get_dashboard" isStreaming={false} />,
    );
    expect(html).toContain("Loading overview");
  });

  it("falls back to humanised name for unknown tool", () => {
    const html = renderToStaticMarkup(<ToolCallIndicator name="custom_tool" isStreaming={false} />);
    expect(html).toContain("custom tool");
  });
});

describe("ChatMessage tool_call branch", () => {
  it("renders compact spinner inside ChatMessage when isGlobalStreaming=true", () => {
    const html = renderToStaticMarkup(
      <ChatMessage
        item={TOOL_CALL_ITEM}
        isStreaming={false}
        isGlobalStreaming={true}
        onPin={noop}
      />,
    );
    expect(html).toContain("animate-spin");
    expect(html).toContain("rounded-full");
    expect(html).not.toContain("✓");
  });

  it("renders compact checkmark inside ChatMessage when isGlobalStreaming=false", () => {
    const html = renderToStaticMarkup(
      <ChatMessage
        item={TOOL_CALL_ITEM}
        isStreaming={false}
        isGlobalStreaming={false}
        onPin={noop}
      />,
    );
    expect(html).not.toContain("animate-spin");
    expect(html).toContain("✓");
    expect(html).toContain("rounded-full");
  });

  it("defaults isGlobalStreaming to false (checkmark) when prop omitted", () => {
    const html = renderToStaticMarkup(
      <ChatMessage item={TOOL_CALL_ITEM} isStreaming={false} onPin={noop} />,
    );
    expect(html).not.toContain("animate-spin");
    expect(html).toContain("✓");
  });
});

describe("ChatMessage pin_widget tool_result branch", () => {
  it("shows 'Pinned to workspace' when pinned=true", () => {
    const item: MessageItem = {
      id: "tr1",
      kind: "tool_result",
      name: "pin_widget",
      widgetType: null,
      result: { pinned: true, widget_id: "abc" },
    };
    const html = renderToStaticMarkup(<ChatMessage item={item} isStreaming={false} onPin={noop} />);
    expect(html).toContain("Pinned to workspace");
    expect(html).not.toContain("Failed to pin");
    expect(html).not.toContain("text-red-500");
  });

  it("shows failure message when pinned=false", () => {
    const item: MessageItem = {
      id: "tr2",
      kind: "tool_result",
      name: "pin_widget",
      widgetType: null,
      result: { pinned: false },
    };
    const html = renderToStaticMarkup(<ChatMessage item={item} isStreaming={false} onPin={noop} />);
    expect(html).toContain("Failed to pin widget");
    expect(html).toContain("text-red-500");
    expect(html).not.toContain("Pinned to workspace");
  });

  it("shows backend error message when pinned=false and error field is set", () => {
    const item: MessageItem = {
      id: "tr3",
      kind: "tool_result",
      name: "pin_widget",
      widgetType: null,
      result: { pinned: false, error: "Unknown widget_type 'bad_type'" },
    };
    const html = renderToStaticMarkup(<ChatMessage item={item} isStreaming={false} onPin={noop} />);
    expect(html).toContain("Unknown widget_type");
    expect(html).toContain("text-red-500");
  });
});

describe("ChatMessage widget preview", () => {
  it("renders widget previews as collapsible details without raw JSON", () => {
    const item: MessageItem = {
      id: "tr4",
      kind: "tool_result",
      name: "get_rating_distribution",
      widgetType: "donut_chart",
      result: { slices: [{ label: "5 star", value: 4, percent: 80 }] },
    };

    const html = renderToStaticMarkup(<ChatMessage item={item} isStreaming={false} onPin={noop} />);

    expect(html).toContain("<details");
    expect(html).toContain("Expand");
    expect(html).toContain("+ Dashboard");
    expect(html).toContain("5 star");
    expect(html).not.toContain("&quot;slices&quot;");
  });
});
