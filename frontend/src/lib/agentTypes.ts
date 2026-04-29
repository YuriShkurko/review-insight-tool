export type MessageItem = {
  id: string;
} & (
  | { kind: "user"; text: string }
  | { kind: "assistant_text"; text: string }
  | { kind: "tool_call"; name: string; args: Record<string, unknown> }
  | {
      kind: "tool_result";
      name: string;
      widgetType: string | null;
      result: Record<string, unknown>;
    }
);

export interface WorkspaceWidget {
  id: string;
  widget_type: string;
  title: string;
  data: Record<string, unknown>;
  position: number;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Array<{
    role?: string;
    content?: string | null;
    tool_calls?: unknown;
  }>;
}
