"use client";

import { useState } from "react";

export function ChatInput({
  onSend,
  disabled,
}: {
  onSend: (message: string) => void;
  disabled: boolean;
}) {
  const [value, setValue] = useState("");

  function submit() {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div className="shrink-0 px-3 py-3 border-t border-border bg-surface-card">
      <div className="flex items-end gap-2">
        <textarea
          data-testid="agent-input"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your reviews…"
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none rounded-xl border border-border bg-surface px-3 py-2 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-brand/60 focus:ring-1 focus:ring-brand/30 disabled:opacity-50 max-h-28 overflow-y-auto"
        />
        <button
          type="button"
          data-testid="agent-send"
          onClick={submit}
          disabled={disabled || !value.trim()}
          className="shrink-0 bg-brand text-white rounded-xl px-3 py-2 text-sm font-medium hover:bg-brand-hover disabled:opacity-40 transition-colors"
        >
          Send
        </button>
      </div>
    </div>
  );
}
