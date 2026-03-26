/**
 * Debug Element Selector
 * Gated by NEXT_PUBLIC_DEBUG_TRAIL=true.
 *
 * Behaviour:
 *  - Hold CTRL and click any element → highlight it (purple glow) + all its children
 *  - Each subsequent CTRL+click adds to the selection
 *  - Double-tap CTRL quickly (≤300ms between presses) → deselect all
 *  - After every selection change, the snapshot is POSTed to the backend
 *    so the MCP debug server can read it via the `ui_snapshot` tool.
 */

const ENABLED = process.env.NEXT_PUBLIC_DEBUG_TRAIL === "true";
const BACKEND = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── CSS injection ──────────────────────────────────────────────────────────

const STYLE_ID = "__debug_selector_styles__";

function injectStyles(): void {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
    @keyframes _debug_shine {
      0%, 100% {
        box-shadow:
          0 0 0 3px rgba(168,85,247,0.5),
          0 0 16px rgba(168,85,247,0.45),
          inset 0 0 0 1px rgba(168,85,247,0.15);
      }
      50% {
        box-shadow:
          0 0 0 5px rgba(168,85,247,0.7),
          0 0 32px rgba(168,85,247,0.65),
          0 0 64px rgba(168,85,247,0.25),
          inset 0 0 0 1px rgba(168,85,247,0.25);
      }
    }
    [data-debug-sel="primary"] {
      outline: 2px solid #a855f7 !important;
      outline-offset: 2px !important;
      animation: _debug_shine 1.6s ease-in-out infinite !important;
      position: relative !important;
      z-index: 9998 !important;
    }
    [data-debug-sel="child"] {
      outline: 1px dashed rgba(168,85,247,0.55) !important;
      outline-offset: 1px !important;
      background: rgba(168,85,247,0.06) !important;
    }
    body[data-debug-selecting] * {
      cursor: crosshair !important;
    }
  `;
  document.head.appendChild(style);
}

// ─── Element serialisation ───────────────────────────────────────────────────

export interface ElementNode {
  tag: string;
  id: string;
  classes: string[];
  text: string;
  path: string;
  rect: { x: number; y: number; width: number; height: number };
  dataAttrs: Record<string, string>;
  reactComponent: string | null;
  children: ChildNode_[];
}

// Renamed to avoid collision with DOM ChildNode
export interface ChildNode_ {
  tag: string;
  id: string;
  classes: string[];
  text: string;
  reactComponent: string | null;
}

function cssPath(el: Element): string {
  const parts: string[] = [];
  let node: Element | null = el;
  while (node && node !== document.body) {
    let selector = node.tagName.toLowerCase();
    if (node.id) {
      selector += `#${node.id}`;
    } else {
      const siblings = Array.from(node.parentElement?.children ?? []).filter(
        (s) => s.tagName === node!.tagName,
      );
      if (siblings.length > 1) {
        selector += `:nth-of-type(${siblings.indexOf(node) + 1})`;
      }
    }
    parts.unshift(selector);
    node = node.parentElement;
  }
  return parts.join(" > ");
}

function getReactComponent(el: Element): string | null {
  try {
    const keys = Object.keys(el);
    const fiberKey = keys.find(
      (k) => k.startsWith("__reactFiber$") || k.startsWith("__reactInternalInstance$"),
    );
    if (!fiberKey) return null;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let fiber = (el as any)[fiberKey];
    while (fiber) {
      const name: string | undefined = fiber.type?.displayName ?? fiber.type?.name;
      if (name && /^[A-Z]/.test(name)) return name;
      fiber = fiber.return;
    }
  } catch {
    // best-effort
  }
  return null;
}

function serializeElement(el: Element): ElementNode {
  const r = el.getBoundingClientRect();
  const dataAttrs: Record<string, string> = {};
  for (const attr of Array.from(el.attributes)) {
    if (attr.name.startsWith("data-") && attr.name !== "data-debug-sel") {
      dataAttrs[attr.name] = attr.value;
    }
  }
  const directChildren = Array.from(el.children).slice(0, 20).map((child) => ({
    tag: child.tagName.toLowerCase(),
    id: child.id || "",
    classes: Array.from(child.classList),
    text: (child.textContent ?? "").trim().slice(0, 80),
    reactComponent: getReactComponent(child),
  }));

  return {
    tag: el.tagName.toLowerCase(),
    id: el.id || "",
    classes: Array.from(el.classList).filter((c) => !c.startsWith("_debug")),
    text: (el.textContent ?? "").trim().slice(0, 200),
    path: cssPath(el),
    rect: { x: Math.round(r.x), y: Math.round(r.y), width: Math.round(r.width), height: Math.round(r.height) },
    dataAttrs,
    reactComponent: getReactComponent(el),
    children: directChildren,
  };
}

// ─── Highlight helpers ───────────────────────────────────────────────────────

function highlightElement(el: Element): void {
  el.setAttribute("data-debug-sel", "primary");
  for (const child of Array.from(el.querySelectorAll("*"))) {
    if (!child.hasAttribute("data-debug-sel")) {
      child.setAttribute("data-debug-sel", "child");
    }
  }
}

function clearAllHighlights(): void {
  for (const el of Array.from(document.querySelectorAll("[data-debug-sel]"))) {
    el.removeAttribute("data-debug-sel");
  }
}

// ─── Backend sync ────────────────────────────────────────────────────────────

async function postSnapshot(selected: ElementNode[]): Promise<void> {
  try {
    await fetch(`${BACKEND}/api/debug/ui-snapshot`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        captured_at: new Date().toISOString(),
        url: window.location.href,
        selected,
      }),
    });
  } catch {
    // debug-only, fire-and-forget
  }
}

// ─── State ───────────────────────────────────────────────────────────────────

let _selected: ElementNode[] = [];
let _lastCtrlTime = 0;

export function getSelected(): ElementNode[] {
  return _selected;
}

export function clearSelection(): void {
  _selected = [];
  clearAllHighlights();
  document.body.removeAttribute("data-debug-selecting");
  void postSnapshot([]);
}

// ─── Event handlers ──────────────────────────────────────────────────────────

function onKeyDown(e: KeyboardEvent): void {
  if (e.key !== "Control") return;
  const now = Date.now();
  if (now - _lastCtrlTime <= 300) {
    // Double CTRL → deselect all
    clearSelection();
    _lastCtrlTime = 0;
  } else {
    _lastCtrlTime = now;
    document.body.setAttribute("data-debug-selecting", "1");
  }
}

function onKeyUp(e: KeyboardEvent): void {
  if (e.key === "Control") {
    document.body.removeAttribute("data-debug-selecting");
  }
}

function onClick(e: MouseEvent): void {
  if (!e.ctrlKey) return;
  e.preventDefault();
  e.stopPropagation();

  const target = e.target as Element;
  // Don't select the debug panel itself
  if (target.closest("[data-debug-panel]")) return;

  highlightElement(target);
  _selected = [..._selected, serializeElement(target)];
  void postSnapshot(_selected);
}

// ─── Mount / unmount ─────────────────────────────────────────────────────────

let _mounted = false;

export function mountDebugSelector(): () => void {
  if (!ENABLED || _mounted || typeof window === "undefined") return () => {};
  _mounted = true;

  injectStyles();
  document.addEventListener("keydown", onKeyDown, true);
  document.addEventListener("keyup", onKeyUp, true);
  document.addEventListener("click", onClick, true);

  return () => {
    _mounted = false;
    document.removeEventListener("keydown", onKeyDown, true);
    document.removeEventListener("keyup", onKeyUp, true);
    document.removeEventListener("click", onClick, true);
    clearAllHighlights();
    document.body.removeAttribute("data-debug-selecting");
  };
}
