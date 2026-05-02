import type { BrowserContext, Page } from "@playwright/test";
import { injectAuthToken } from "./api";

export const MOCK_NOW = "2026-05-02T10:00:00.000Z";
export const MOCK_BUSINESS_ID = "mock-business-1";

export const mockBusiness = {
  id: MOCK_BUSINESS_ID,
  place_id: "mock_place_1",
  name: "E2E Cafe",
  business_type: "cafe",
  address: "1 Test Street",
  google_maps_url: null,
  avg_rating: 4.2,
  total_reviews: 42,
  created_at: MOCK_NOW,
  updated_at: MOCK_NOW,
};

export const mockDashboard = {
  place_id: mockBusiness.place_id,
  business_name: mockBusiness.name,
  business_type: mockBusiness.business_type,
  address: mockBusiness.address,
  avg_rating: mockBusiness.avg_rating,
  total_reviews: mockBusiness.total_reviews,
  top_complaints: [{ label: "Slow service", count: 7 }],
  top_praise: [{ label: "Friendly staff", count: 11 }],
  ai_summary: "Customers like the staff, but service speed needs attention.",
  action_items: ["Add one more host on Fridays."],
  risk_areas: ["Weekend staffing gap"],
  recommended_focus: "Reduce wait time during evening rush.",
  analysis_created_at: MOCK_NOW,
  last_updated_at: MOCK_NOW,
};

export interface MockWorkspaceWidget {
  id: string;
  widget_type: string;
  title: string;
  data: Record<string, unknown>;
  position: number;
  created_at: string;
}

export function metricWidget(id = "metric-1") {
  return {
    id,
    widget_type: "metric_card",
    title: "Avg Rating",
    data: { value: 4.2 },
    position: 0,
    created_at: MOCK_NOW,
  } satisfies MockWorkspaceWidget;
}

export function lineWidget(id = "line-1") {
  return {
    id,
    widget_type: "line_chart",
    title: "Rating Trend",
    data: {
      series: [
        { date: "2026-05-01", avg_rating: 4.1 },
        { date: "2026-05-02", avg_rating: 4.3 },
      ],
      metric: "avg_rating",
    },
    position: 1,
    created_at: MOCK_NOW,
  } satisfies MockWorkspaceWidget;
}

export function ratingDistributionWidget(id = "rating-distribution-1") {
  return {
    id,
    widget_type: "bar_chart",
    title: "Rating distribution",
    data: {
      bars: [
        { label: "1 star", value: 1 },
        { label: "2 star", value: 2 },
        { label: "3 star", value: 4 },
        { label: "4 star", value: 8 },
        { label: "5 star", value: 18 },
      ],
    },
    position: 0,
    created_at: MOCK_NOW,
  } satisfies MockWorkspaceWidget;
}

export async function prepareMockAuth(context: BrowserContext) {
  await injectAuthToken(context, "mock-token");
}

export async function mockBusinessDetailApi(
  page: Page,
  options: { initialWidgets?: MockWorkspaceWidget[] } = {},
) {
  let widgets = [...(options.initialWidgets ?? [])];

  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();

    if (url.pathname === "/api/auth/me") {
      await route.fulfill({
        json: { id: "mock-user-1", email: "mock-e2e@test.com", created_at: MOCK_NOW },
      });
      return;
    }

    if (url.pathname === `/api/businesses/${MOCK_BUSINESS_ID}/dashboard`) {
      await route.fulfill({ json: mockDashboard });
      return;
    }

    if (
      url.pathname === `/api/businesses/${MOCK_BUSINESS_ID}/agent/workspace` &&
      method === "GET"
    ) {
      await route.fulfill({ json: widgets });
      return;
    }

    if (
      url.pathname === `/api/businesses/${MOCK_BUSINESS_ID}/agent/workspace/reorder` &&
      method === "PATCH"
    ) {
      const body = JSON.parse(request.postData() ?? "{}") as { widget_ids?: string[] };
      const byId = new Map(widgets.map((widget) => [widget.id, widget]));
      widgets = (body.widget_ids ?? [])
        .map((id, position) => {
          const widget = byId.get(id);
          return widget ? { ...widget, position } : null;
        })
        .filter(Boolean) as typeof widgets;
      await route.fulfill({ json: { reordered: true, widget_ids: body.widget_ids ?? [] } });
      return;
    }

    if (url.pathname === `/api/businesses/${MOCK_BUSINESS_ID}/agent/chat` && method === "POST") {
      const widget = ratingDistributionWidget();
      widgets = [widget];
      await route.fulfill({
        contentType: "text/event-stream",
        body: [
          `event: workspace_event\ndata: ${JSON.stringify({ action: "widget_added", widget })}\n\n`,
          `event: text_delta\ndata: ${JSON.stringify({ text: "Added rating distribution to the dashboard." })}\n\n`,
          `event: done\ndata: ${JSON.stringify({ conversation_id: "mock-conversation-1" })}\n\n`,
        ].join(""),
      });
      return;
    }

    await route.fulfill({ status: 404, json: { detail: `Unhandled test route: ${url.pathname}` } });
  });
}
