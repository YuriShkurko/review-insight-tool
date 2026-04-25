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
    <div className="shrink-0 px-4 py-3 border-t border-gray-200 bg-white">
      <div className="flex items-end gap-2">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your reviews… (Enter to send, Shift+Enter for newline)"
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none rounded-xl border border-gray-200 px-4 py-2.5 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:border-blue-400 disabled:opacity-50 max-h-32 overflow-y-auto"
        />
        <button
          type="button"
          onClick={submit}
          disabled={disabled || !value.trim()}
          className="shrink-0 bg-blue-600 text-white rounded-xl px-4 py-2.5 text-sm font-medium hover:bg-blue-700 disabled:opacity-40 transition-colors"
        >
          Send
        </button>
      </div>
    </div>
  );
}
