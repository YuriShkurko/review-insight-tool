import { renderToStaticMarkup } from "react-dom/server";
import { describe, it, expect } from "vitest";
import { ChatMessage } from "../ChatMessage";
import { ToolCallIndicator } from "../ToolCallIndicator";
import type { MessageItem } from "@/lib/agentTypes";

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
    const html = renderToStaticMarkup(
      <ToolCallIndicator name="custom_tool" isStreaming={false} />,
    );
    expect(html).toContain("custom tool");
  });
});

describe("ChatMessage tool_call branch", () => {
  const noop = () => {};

  it("renders spinner inside ChatMessage when isGlobalStreaming=true", () => {
    const html = renderToStaticMarkup(
      <ChatMessage
        item={TOOL_CALL_ITEM}
        isStreaming={false}
        isGlobalStreaming={true}
        onPin={noop}
      />,
    );
    expect(html).toContain("animate-spin");
    expect(html).not.toContain("✓");
  });

  it("renders checkmark inside ChatMessage when isGlobalStreaming=false", () => {
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
  });

  it("defaults isGlobalStreaming to false (checkmark) when prop omitted", () => {
    const html = renderToStaticMarkup(
      <ChatMessage item={TOOL_CALL_ITEM} isStreaming={false} onPin={noop} />,
    );
    expect(html).not.toContain("animate-spin");
    expect(html).toContain("✓");
  });
});
