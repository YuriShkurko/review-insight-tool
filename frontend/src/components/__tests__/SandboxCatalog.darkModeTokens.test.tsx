import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import SandboxCatalog from "../SandboxCatalog";
import type { CatalogBusiness, CatalogResponse } from "@/lib/types";

const sampleRow = (placeId: string, overrides: Partial<CatalogBusiness> = {}): CatalogBusiness => ({
  place_id: placeId,
  name: "Demo Pub",
  business_type: "bar",
  address: "1 Main St",
  review_count: 120,
  imported: false,
  business_id: null,
  ...overrides,
});

const minimalCatalog: CatalogResponse = {
  scenarios: [
    {
      id: "demo_scenario",
      description: "A short scenario for tests.",
      main: sampleRow("offline_main"),
      competitors: [sampleRow("offline_comp_a")],
    },
  ],
  standalone: [sampleRow("offline_standalone")],
};

describe("SandboxCatalog dark-mode token hygiene", () => {
  it("compact variant avoids raw light-only panel classes", () => {
    const html = renderToStaticMarkup(
      <SandboxCatalog
        catalog={minimalCatalog}
        onImportPlace={async () => {}}
        busyPlaceId={null}
        variant="compact"
      />,
    );
    expect(html).not.toContain("bg-white");
    expect(html).not.toContain("border-slate-200");
    expect(html).not.toContain("bg-slate-50");
    expect(html).toContain("bg-surface-card");
    expect(html).toContain("border-border");
  });

  it("full variant avoids raw light-only panel classes", () => {
    const html = renderToStaticMarkup(
      <SandboxCatalog
        catalog={minimalCatalog}
        onImportPlace={async () => {}}
        busyPlaceId={null}
        variant="full"
      />,
    );
    expect(html).not.toContain("bg-white");
    expect(html).not.toContain("border-slate-200");
    expect(html).not.toContain("bg-slate-50");
  });
});
