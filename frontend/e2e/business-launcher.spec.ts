/**
 * Phase 1 launcher coverage: authenticated landing, opening a workspace tile,
 * and the offline sandbox import/open path.
 */

import { test, expect, type Page } from "@playwright/test";
import { injectAuthToken } from "./helpers/api";
import { MOCK_BUSINESS_ID, MOCK_NOW, mockBusiness, prepareMockAuth } from "./helpers/mockApi";

const now = MOCK_NOW;

const offlineBusiness = {
  id: "offline-biz-1",
  place_id: "offline_lager_ale",
  name: "Lager & Ale (Rothschild)",
  business_type: "bar",
  address: "Rothschild Blvd, Tel Aviv, Israel",
  google_maps_url: null,
  avg_rating: null,
  total_reviews: 0,
  created_at: now,
  updated_at: now,
};

const catalogBusiness = {
  place_id: "offline_lager_ale",
  name: "Lager & Ale (Rothschild)",
  business_type: "bar",
  address: "Rothschild Blvd, Tel Aviv, Israel",
  review_count: 128,
  imported: false,
  business_id: null,
};

async function mockOfflineLauncherApi(page: Page) {
  let imported = false;

  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const method = request.method();

    if (url.pathname === "/api/auth/me") {
      await route.fulfill({
        json: { id: "offline-user-1", email: "offline-e2e@test.com", created_at: now },
      });
      return;
    }

    if (url.pathname === "/api/bootstrap") {
      await route.fulfill({ json: { review_provider: "offline" } });
      return;
    }

    if (url.pathname === "/api/businesses" && method === "GET") {
      await route.fulfill({ json: imported ? [offlineBusiness] : [] });
      return;
    }

    if (url.pathname === "/api/sandbox/catalog" && method === "GET") {
      await route.fulfill({
        json: {
          scenarios: [
            {
              id: "bar",
              description: "Lager & Ale vs nearby competitors",
              main: {
                ...catalogBusiness,
                imported,
                business_id: imported ? offlineBusiness.id : null,
              },
              competitors: [
                {
                  place_id: "offline_beer_garden",
                  name: "Beer Garden",
                  business_type: "bar",
                  address: "Rothschild Blvd, Tel Aviv, Israel",
                  review_count: 64,
                  imported: false,
                  business_id: null,
                },
              ],
            },
          ],
          standalone: [],
        },
      });
      return;
    }

    if (url.pathname === "/api/sandbox/import" && method === "POST") {
      imported = true;
      await route.fulfill({ status: 201, json: offlineBusiness });
      return;
    }

    await route.fulfill({ status: 404, json: { detail: `Unhandled test route: ${url.pathname}` } });
  });
}

async function mockExistingBusinessLauncherApi(page: Page) {
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();

    if (url.pathname === "/api/auth/me") {
      await route.fulfill({
        json: { id: "mock-user-1", email: "mock-e2e@test.com", created_at: now },
      });
      return;
    }

    if (url.pathname === "/api/bootstrap") {
      await route.fulfill({ json: { review_provider: "mock" } });
      return;
    }

    if (url.pathname === "/api/businesses" && method === "GET") {
      await route.fulfill({ json: [mockBusiness] });
      return;
    }

    await route.fulfill({ status: 404, json: { detail: `Unhandled test route: ${url.pathname}` } });
  });
}

test.describe("business launcher", () => {
  test("authenticated user sees launcher and opens an existing workspace tile", async ({
    page,
    context,
  }) => {
    await mockExistingBusinessLauncherApi(page);
    await prepareMockAuth(context);

    await page.goto("/businesses");

    await expect(page.getByTestId("business-launcher")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Your business insight workspaces" }),
    ).toBeVisible();

    const firstTile = page.getByTestId("business-tile").first();
    await expect(firstTile).toBeVisible();
    await firstTile.getByTestId("open-business-workspace").click();

    await expect(page).toHaveURL(new RegExp(`/businesses/${MOCK_BUSINESS_ID}$`));
  });

  test("offline catalog import turns a scenario sample into an open workspace action", async ({
    page,
    context,
  }) => {
    await mockOfflineLauncherApi(page);
    await injectAuthToken(context, "offline-token");

    await page.goto("/businesses");

    await expect(page.getByTestId("sandbox-catalog")).toBeVisible();
    await expect(page.getByTestId("sandbox-scenario-card")).toHaveCount(1);

    const mainSample = page.locator(
      '[data-testid="sandbox-main-business"][data-place-id="offline_lager_ale"]',
    );
    await expect(mainSample).toBeVisible();
    await mainSample.getByTestId("sandbox-import-action").click();

    const importedTile = page.locator(
      `[data-testid="business-tile"][data-business-id="${offlineBusiness.id}"]`,
    );
    await expect(importedTile).toBeVisible();
    await importedTile.getByTestId("open-business-workspace").click();

    await expect(page).toHaveURL(/\/businesses\/offline-biz-1$/);
  });
});
