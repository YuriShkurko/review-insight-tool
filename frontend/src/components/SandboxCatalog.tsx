"use client";

import Link from "next/link";
import type { CatalogBusiness, CatalogResponse } from "@/lib/types";
import { displayBusinessName } from "@/lib/displayName";
import { BusinessTypeIcon } from "@/components/icons/BusinessTypeIcon";

function formatScenarioTitle(id: string): string {
  return id
    .split(/[-_\s]+/)
    .filter(Boolean)
    .map((part) => part[0]?.toUpperCase() + part.slice(1))
    .join(" ");
}

function formatBusinessType(value: string): string {
  return value === "other" ? "Sample" : value;
}

function totalScenarioReviews(main: CatalogBusiness, competitors: CatalogBusiness[]): number {
  return competitors.reduce((sum, c) => sum + c.review_count, main.review_count);
}

function SampleBusinessCard({
  row,
  role,
  onImportPlace,
  busy,
  featured = false,
}: {
  row: CatalogBusiness;
  role: "main" | "competitor" | "standalone";
  onImportPlace: (placeId: string) => Promise<void>;
  busy: boolean;
  featured?: boolean;
}) {
  const roleLabel =
    role === "main" ? "Main workspace" : role === "competitor" ? "Competitor" : "Sample";

  return (
    <article
      data-testid={
        role === "main"
          ? "sandbox-main-business"
          : role === "competitor"
            ? "sandbox-competitor-business"
            : "sandbox-standalone-business"
      }
      data-place-id={row.place_id}
      className={`flex h-full flex-col rounded-lg border bg-surface-card p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md ${
        featured ? "border-brand/30 ring-2 ring-brand/10" : "border-border"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${
                role === "main"
                  ? "border-brand/20 bg-brand-light text-brand"
                  : "border-border-subtle bg-surface text-text-muted"
              }`}
            >
              {roleLabel}
            </span>
            {featured && (
              <span className="rounded-full border border-accent/20 bg-accent-light px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-accent">
                Best demo start
              </span>
            )}
          </div>
          <h4 className="mt-3 flex items-center gap-2 text-base font-semibold leading-snug text-text-primary">
            <BusinessTypeIcon
              businessType={row.business_type}
              className="h-4 w-4 shrink-0 text-text-muted"
              aria-hidden
            />
            <span className="truncate">{displayBusinessName(row)}</span>
          </h4>
          {row.address && (
            <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-text-muted">
              {row.address}
            </p>
          )}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-lg border border-border-subtle bg-surface px-3 py-2">
          <p className="font-medium uppercase tracking-wider text-text-muted">Reviews</p>
          <p className="mt-1 text-sm font-semibold text-text-primary">
            {row.review_count.toLocaleString()}
          </p>
        </div>
        <div className="rounded-lg border border-border-subtle bg-surface px-3 py-2">
          <p className="font-medium uppercase tracking-wider text-text-muted">Type</p>
          <p className="mt-1 truncate text-sm font-semibold capitalize text-text-primary">
            {formatBusinessType(row.business_type)}
          </p>
        </div>
      </div>

      <div className="mt-auto pt-4">
        {row.imported && row.business_id ? (
          <Link
            href={`/businesses/${row.business_id}`}
            data-testid="sandbox-open-action"
            data-place-id={row.place_id}
            className="inline-flex w-full items-center justify-center rounded-lg bg-[#111827] px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-brand"
          >
            Open workspace
          </Link>
        ) : (
          <button
            type="button"
            disabled={busy}
            onClick={() => void onImportPlace(row.place_id)}
            data-testid="sandbox-import-action"
            data-place-id={row.place_id}
            className="inline-flex w-full items-center justify-center rounded-lg bg-brand px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-hover disabled:opacity-50"
          >
            {busy ? "Adding..." : "Add sample"}
          </button>
        )}
      </div>
    </article>
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
  const totalScenarios = catalog.scenarios.length;
  const totalSamples =
    catalog.standalone.length +
    catalog.scenarios.reduce((sum, scenario) => sum + 1 + scenario.competitors.length, 0);

  const inner = (
    <>
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-brand">
            Offline demo catalog
          </p>
          <h2 className="mt-1 text-xl font-semibold text-text-primary">
            Choose a ready-made review story
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-text-secondary">
            Import a curated business, then fetch reviews, run analysis, compare competitors, and
            build the AI workspace with deterministic local JSON instead of live Google data.
          </p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs text-text-secondary">
            <span className="rounded-full border border-border-subtle bg-surface px-3 py-1 text-text-secondary">
              {totalScenarios} scenario{totalScenarios !== 1 ? "s" : ""}
            </span>
            <span className="rounded-full border border-border-subtle bg-surface px-3 py-1 text-text-secondary">
              {totalSamples} sample{totalSamples !== 1 ? "s" : ""}
            </span>
            <span className="rounded-full border border-border-subtle bg-surface px-3 py-1 text-text-secondary">
              Local demo data
            </span>
          </div>
        </div>
        {onResetSandbox && (
          <button
            type="button"
            disabled={resetBusy}
            onClick={() => onResetSandbox()}
            data-testid="sandbox-reset-action"
            className="rounded-lg border border-border bg-surface-card px-3 py-2 text-xs font-medium text-text-secondary transition-colors hover:border-danger/40 hover:bg-danger-soft hover:text-danger disabled:opacity-50 dark:hover:border-danger/50"
          >
            {resetBusy ? "Resetting..." : "Reset offline samples"}
          </button>
        )}
      </div>

      <div className="space-y-5">
        {catalog.scenarios.map((scenario) => (
          <section
            key={scenario.id}
            data-testid="sandbox-scenario-card"
            data-scenario-id={scenario.id}
            className="overflow-hidden rounded-xl border border-border bg-surface"
          >
            <div className="border-b border-border bg-surface-card px-4 py-4 sm:px-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="text-lg font-semibold text-text-primary">
                    {formatScenarioTitle(scenario.id)} scenario
                  </h3>
                  <p className="mt-1 max-w-2xl text-sm leading-relaxed text-text-secondary">
                    {scenario.description}
                  </p>
                </div>
                <div className="rounded-lg border border-border-subtle bg-surface px-3 py-2 text-right">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                    Curated reviews
                  </p>
                  <p className="mt-1 text-sm font-semibold text-text-primary">
                    {totalScenarioReviews(scenario.main, scenario.competitors).toLocaleString()}
                  </p>
                </div>
              </div>
            </div>

            <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1.4fr)] sm:p-5">
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-text-muted">
                  Start here
                </p>
                <SampleBusinessCard
                  row={scenario.main}
                  role="main"
                  featured={scenario.main.place_id === "offline_lager_ale"}
                  onImportPlace={onImportPlace}
                  busy={busyPlaceId === scenario.main.place_id}
                />
              </div>

              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-text-muted">
                  Compare against
                </p>
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                  {scenario.competitors.map((c) => (
                    <SampleBusinessCard
                      key={c.place_id}
                      row={c}
                      role="competitor"
                      onImportPlace={onImportPlace}
                      busy={busyPlaceId === c.place_id}
                    />
                  ))}
                </div>
              </div>
            </div>
          </section>
        ))}

        {catalog.standalone.length > 0 && (
          <section className="rounded-xl border border-border bg-surface-card p-4 sm:p-5">
            <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
              <div>
                <h3 className="text-lg font-semibold text-text-primary">More samples</h3>
                <p className="mt-1 text-sm text-text-secondary">
                  Extra businesses you can launch on their own or use for alternate demos.
                </p>
              </div>
              <p className="rounded-full border border-border-subtle bg-surface px-3 py-1 text-xs text-text-secondary">
                {catalog.standalone.length} standalone
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {catalog.standalone.map((c) => (
                <SampleBusinessCard
                  key={c.place_id}
                  row={c}
                  role="standalone"
                  onImportPlace={onImportPlace}
                  busy={busyPlaceId === c.place_id}
                  featured={c.place_id === "sim_lager_ale_tlv"}
                />
              ))}
            </div>
          </section>
        )}
      </div>
    </>
  );

  if (variant === "compact") {
    return (
      <details
        data-testid="sandbox-catalog"
        className="rounded-xl border border-border bg-surface-card p-4 shadow-sm"
      >
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-sm font-medium text-text-primary [&::-webkit-details-marker]:hidden">
          <span>Browse offline demo samples</span>
          <span className="rounded-full border border-border-subtle bg-surface px-2 py-0.5 text-xs font-medium text-text-secondary">
            {totalSamples} samples
          </span>
        </summary>
        <div className="mt-4 border-t border-border-subtle pt-4">{inner}</div>
      </details>
    );
  }

  return (
    <section
      data-testid="sandbox-catalog"
      className="rounded-xl border border-border bg-surface-card p-5 shadow-sm sm:p-6"
    >
      {inner}
    </section>
  );
}
