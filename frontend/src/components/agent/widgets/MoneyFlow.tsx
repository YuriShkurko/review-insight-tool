type FlowStep = {
  label: string;
  value: number;
  delta?: number | null;
  margin_pct?: number | null;
  kind: "revenue" | "deduction" | "subtotal" | "profit";
  indent?: boolean;
};

function formatCurrency(value: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}

function asNumber(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

function buildSteps(data: Record<string, unknown>): FlowStep[] {
  const revenue = asNumber(data.revenue);
  const cogs = asNumber(data.cogs);
  const opex = asNumber(data.operating_expenses);
  const netProfit = asNumber(data.net_profit);

  if (revenue == null) return [];

  const steps: FlowStep[] = [];

  steps.push({ label: "Revenue", value: revenue, kind: "revenue" });

  if (cogs != null) {
    steps.push({ label: "Cost of Goods Sold", value: cogs, delta: -cogs, kind: "deduction" });
    const gross = revenue - cogs;
    const grossMargin = revenue > 0 ? Math.round((gross / revenue) * 100) : null;
    steps.push({ label: "Gross Profit", value: gross, margin_pct: grossMargin, kind: "subtotal" });

    if (opex != null) {
      steps.push({ label: "Operating Expenses", value: opex, delta: -opex, kind: "deduction" });
      const net = netProfit ?? gross - opex;
      const netMargin = revenue > 0 ? Math.round((net / revenue) * 100) : null;
      steps.push({ label: "Net Profit", value: net, margin_pct: netMargin, kind: "profit" });
    }
  } else if (opex != null) {
    const net = netProfit ?? revenue - opex;
    const netMargin = revenue > 0 ? Math.round((net / revenue) * 100) : null;
    steps.push({ label: "Operating Expenses", value: opex, delta: -opex, kind: "deduction" });
    steps.push({ label: "Net Profit", value: net, margin_pct: netMargin, kind: "profit" });
  }

  return steps;
}

const KIND_STYLES: Record<
  FlowStep["kind"],
  { barClass: string; label: string; value: string; indent: boolean }
> = {
  revenue: {
    barClass: "bg-brand/70",
    label: "text-text-primary font-semibold",
    value: "text-text-primary font-semibold",
    indent: false,
  },
  deduction: {
    barClass: "bg-danger/50",
    label: "text-text-secondary",
    value: "text-danger",
    indent: true,
  },
  subtotal: {
    barClass: "bg-info/60",
    label: "text-text-primary font-medium",
    value: "text-text-primary font-medium",
    indent: false,
  },
  profit: {
    barClass: "bg-success/70",
    label: "text-text-primary font-semibold",
    value: "text-success font-semibold",
    indent: false,
  },
};

export function MoneyFlow({ data }: { data: Record<string, unknown> }) {
  const steps = buildSteps(data);
  const currency = typeof data.currency === "string" ? data.currency : "USD";
  const period = typeof data.period === "string" ? data.period : null;
  const isDemo = data.is_demo === true;
  const summary = typeof data.summary === "string" ? data.summary : null;

  if (steps.length === 0) {
    return (
      <p data-testid="widget-empty-state" className="text-xs text-text-muted">
        No financial flow data available.
      </p>
    );
  }

  const maxValue = Math.max(...steps.map((s) => Math.abs(s.value)), 1);

  return (
    <div className="space-y-3">
      {summary && <p className="text-xs leading-relaxed text-text-secondary">{summary}</p>}

      <div className="space-y-2">
        {steps.map((step, i) => {
          const styles = KIND_STYLES[step.kind];
          const barWidth = Math.max(6, Math.round((Math.abs(step.value) / maxValue) * 100));
          return (
            <div key={i} className={step.indent ? "pl-3" : ""}>
              <div className="mb-1 flex items-center justify-between gap-2 text-xs">
                <span className={styles.label}>{step.label}</span>
                <div className="flex items-center gap-2 tabular-nums">
                  {step.margin_pct != null && (
                    <span className="text-[11px] text-text-muted">{step.margin_pct}% margin</span>
                  )}
                  <span className={styles.value}>
                    {step.kind === "deduction" ? "−" : ""}
                    {formatCurrency(Math.abs(step.value), currency)}
                  </span>
                </div>
              </div>
              <div className="h-2 rounded-full bg-surface-elevated">
                <div
                  className={`h-2 rounded-full transition-all ${styles.barClass}`}
                  style={{ width: `${barWidth}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex items-center gap-2 text-[11px] text-text-muted">
        {period && <span>{period}</span>}
        {isDemo && (
          <span className="rounded-full border border-warning/40 bg-warning-soft px-2 py-0.5 text-warning">
            Demo signal
          </span>
        )}
      </div>
    </div>
  );
}
