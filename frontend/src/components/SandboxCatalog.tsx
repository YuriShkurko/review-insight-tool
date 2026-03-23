"use client";

import Link from "next/link";
import type { CatalogBusiness, CatalogResponse } from "@/lib/types";

function BusinessRow({
  row,
  onImport,
  busy,
}: {
  row: CatalogBusiness;
  onImport: (placeId: string) => void;
  busy: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 py-2 border-b border-gray-100 last:border-0">
      <div className="flex-1 min-w-[180px]">
        <span className="font-medium text-sm text-gray-900">{row.name}</span>
        {row.business_type && row.business_type !== "other" && (
          <span className="ml-2 text-[10px] bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full capitalize">
            {row.business_type}
          </span>
        )}
        {row.address && <p className="text-xs text-gray-400 truncate mt-0.5">{row.address}</p>}
        <p className="text-xs text-gray-400 mt-0.5">{row.review_count} curated reviews (offline)</p>
      </div>
      <div className="shrink-0">
        {row.imported && row.business_id ? (
          <Link
            href={`/businesses/${row.business_id}`}
            className="text-sm font-medium text-blue-600 hover:text-blue-700"
          >
            Open
          </Link>
        ) : (
          <button
            type="button"
            disabled={busy}
            onClick={() => onImport(row.place_id)}
            className="text-sm font-medium bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {busy ? "Adding…" : "Add to my account"}
          </button>
        )}
      </div>
    </div>
  );
}

export default function SandboxCatalog({
  catalog,
  onImportPlace,
  busyPlaceId,
  onResetSandbox,
  resetBusy,
  variant = "full",
}: {
  catalog: CatalogResponse;
  onImportPlace: (placeId: string) => Promise<void>;
  busyPlaceId: string | null;
  onResetSandbox?: () => Promise<void>;
  resetBusy?: boolean;
  variant?: "full" | "compact";
}) {
  const inner = (
    <>
      <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">Offline sandbox</h2>
          <p className="text-sm text-gray-500 mt-1">
            Pick a sample business to add to your account, then use <strong>Fetch Reviews</strong>,{" "}
            <strong>Run Analysis</strong>, and <strong>Compare</strong> like a real workflow. Data
            is deterministic local JSON — not live Google data.
          </p>
        </div>
        {onResetSandbox && (
          <button
            type="button"
            disabled={resetBusy}
            onClick={() => onResetSandbox()}
            className="text-xs text-gray-500 hover:text-red-600 disabled:opacity-50"
          >
            {resetBusy ? "Resetting…" : "Reset offline samples"}
          </button>
        )}
      </div>

      <div className="space-y-6">
        {catalog.scenarios.map((scenario) => (
          <div key={scenario.id}>
            <h3 className="text-sm font-semibold text-gray-700 capitalize mb-1">
              {scenario.id} scenario
            </h3>
            <p className="text-xs text-gray-400 mb-2">{scenario.description}</p>
            <div className="rounded-lg border border-gray-200 bg-gray-50/50 px-3">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide pt-3 pb-1">
                Main
              </p>
              <BusinessRow
                row={scenario.main}
                onImport={(id) => onImportPlace(id)}
                busy={busyPlaceId === scenario.main.place_id}
              />
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide pt-2 pb-1">
                Suggested competitors
              </p>
              {scenario.competitors.map((c) => (
                <BusinessRow
                  key={c.place_id}
                  row={c}
                  onImport={(id) => onImportPlace(id)}
                  busy={busyPlaceId === c.place_id}
                />
              ))}
            </div>
          </div>
        ))}

        {catalog.standalone.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">More samples</h3>
            <p className="text-xs text-gray-400 mb-2">
              Extra businesses you can add on their own (not tied to a preset scenario).
            </p>
            <div className="rounded-lg border border-gray-200 bg-gray-50/50 px-3">
              {catalog.standalone.map((c) => (
                <BusinessRow
                  key={c.place_id}
                  row={c}
                  onImport={(id) => onImportPlace(id)}
                  busy={busyPlaceId === c.place_id}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </>
  );

  if (variant === "compact") {
    return (
      <details className="bg-white border border-gray-200 rounded-xl p-4">
        <summary className="text-sm font-medium text-gray-700 cursor-pointer list-none flex items-center justify-between">
          <span>Browse more sample businesses</span>
          <span className="text-gray-400 text-xs">▼</span>
        </summary>
        <div className="mt-4 pt-4 border-t border-gray-100">{inner}</div>
      </details>
    );
  }

  return <div className="bg-white border border-blue-200 rounded-xl p-6 shadow-sm">{inner}</div>;
}
