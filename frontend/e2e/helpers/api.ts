/**
 * Test helpers that talk to the backend directly (REST + ScriptedProvider).
 *
 * The backend MUST be running with TESTING=true and LLM_PROVIDER=scripted.
 * See playwright.config.ts header for the exact startup env.
 */

import type { APIRequestContext, BrowserContext, Locator, Page } from "@playwright/test";

const BACKEND_URL = process.env.PLAYWRIGHT_BACKEND_URL ?? "http://localhost:8000";
const API_BASE = `${BACKEND_URL}/api`;

const SAMPLE_MAPS_URL =
  "https://www.google.com/maps/place/E2E+Cafe/@0,0,17z/data=!4m2!3m1!1s0x0:0xe2e";

export interface SeededUser {
  email: string;
  password: string;
  token: string;
  businessId: string;
}

function randomEmail(): string {
  const stamp = Date.now().toString(36);
  const rand = Math.random().toString(36).slice(2, 8);
  return `e2e-${stamp}-${rand}@test.com`;
}

/**
 * Create a brand-new user, log them in, attach a business, and load mock
 * reviews so the agent's data tools have something to return. Each spec
 * gets a fresh user to keep state isolated.
 */
export async function seedUser(api: APIRequestContext): Promise<SeededUser> {
  const email = randomEmail();
  const password = "playwright123";

  const reg = await api.post(`${API_BASE}/auth/register`, { data: { email, password } });
  if (reg.status() !== 201) {
    throw new Error(`register failed: ${reg.status()} ${await reg.text()}`);
  }
  const token = (await reg.json()).access_token as string;
  const headers = { Authorization: `Bearer ${token}` };

  const boot = await api.get(`${API_BASE}/bootstrap`);
  const reviewProvider =
    boot.status() === 200
      ? ((await boot.json()) as { review_provider?: string }).review_provider
      : undefined;

  let businessId: string;
  if (reviewProvider === "offline") {
    const imp = await api.post(`${API_BASE}/sandbox/import`, {
      headers,
      data: { place_id: "offline_lager_ale" },
    });
    if (imp.status() !== 201) {
      throw new Error(`sandbox import failed: ${imp.status()} ${await imp.text()}`);
    }
    businessId = (await imp.json()).id as string;
  } else {
    const biz = await api.post(`${API_BASE}/businesses`, {
      headers,
      data: { google_maps_url: SAMPLE_MAPS_URL, business_type: "cafe" },
    });
    if (biz.status() !== 201) {
      throw new Error(`create business failed: ${biz.status()} ${await biz.text()}`);
    }
    businessId = (await biz.json()).id as string;
  }

  // Mock provider returns canned reviews — needed so the agent's data tools
  // (get_dashboard, get_rating_distribution, etc.) have rows to operate on.
  const fetched = await api.post(`${API_BASE}/businesses/${businessId}/fetch-reviews`, {
    headers,
  });
  if (fetched.status() !== 200) {
    throw new Error(`fetch-reviews failed: ${fetched.status()} ${await fetched.text()}`);
  }

  return { email, password, token, businessId };
}

/**
 * Pre-populate the browser's localStorage with the auth token so the page
 * loads logged-in. Avoids driving the login form in every spec.
 */
export async function injectAuthToken(context: BrowserContext, token: string): Promise<void> {
  await context.addInitScript(
    ([t]) => {
      try {
        window.localStorage.setItem("token", t);
      } catch {
        // localStorage may be unavailable in some contexts; silent fallback.
      }
    },
    [token],
  );
}

/**
 * Inject a per-scenario script into the backend's ScriptedProvider singleton.
 * Each call replaces the previous script and rewinds the cursor.
 */
export async function setAgentScript(api: APIRequestContext, script: ScriptTurn[]): Promise<void> {
  const r = await api.post(`${API_BASE}/test/agent/script`, { data: { script } });
  if (r.status() !== 204) {
    throw new Error(`set agent script failed: ${r.status()} ${await r.text()}`);
  }
}

export async function pinWidgetDirect(
  api: APIRequestContext,
  user: SeededUser,
  widgetType: string,
  title: string,
  data: Record<string, unknown>,
): Promise<{ id: string }> {
  const r = await api.post(`${API_BASE}/businesses/${user.businessId}/agent/workspace`, {
    headers: { Authorization: `Bearer ${user.token}` },
    data: { widget_type: widgetType, title, data },
  });
  if (r.status() !== 201) {
    throw new Error(`pin direct failed: ${r.status()} ${await r.text()}`);
  }
  return (await r.json()) as { id: string };
}

export async function gotoBusiness(page: Page, user: SeededUser): Promise<void> {
  await page.goto(`/businesses/${user.businessId}`);
}

/**
 * Scope-locator for the visible dashboard layout. The page renders the same
 * Workspace + ChatPanel twice — once in the desktop container and once in the
 * mobile container — so every data-testid would otherwise resolve to two
 * elements under Playwright's strict mode. We pin to the desktop layout
 * because the default Playwright viewport (Desktop Chrome ≥ 1024px) only
 * shows that one.
 */
export function dashboard(page: Page): Locator {
  return page.locator('[data-testid="dashboard-desktop"]');
}

export interface ScriptTurn {
  text?: string;
  tool_calls?: Array<{
    name: string;
    arguments?: Record<string, unknown>;
  }>;
}

/**
 * Load a JSON fixture from the shared `backend/tests/fixtures/agent_scripts/`
 * directory and substitute `{WIDGET_ID}`/`{BUSINESS_ID}` placeholders.
 */
export function loadScriptFixture(
  name: string,
  substitutions: Record<string, string> = {},
): ScriptTurn[] {
  // Lazy require so the import isn't part of the playwright bootstrap path.
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const fs = require("fs") as typeof import("fs");
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const path = require("path") as typeof import("path");
  const fixturePath = path.resolve(
    __dirname,
    "..",
    "..",
    "..",
    "backend",
    "tests",
    "fixtures",
    "agent_scripts",
    name,
  );
  let raw = fs.readFileSync(fixturePath, "utf-8");
  for (const [key, value] of Object.entries(substitutions)) {
    raw = raw.replaceAll(`{${key}}`, value);
  }
  return JSON.parse(raw) as ScriptTurn[];
}
