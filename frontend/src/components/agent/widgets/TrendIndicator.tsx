interface PeriodStats {
  count: number;
  avg_rating: number | null;
}

export function TrendIndicator({ data }: { data: Record<string, unknown> }) {
  const period = data.period as string | undefined;
  const current = data.current as PeriodStats | undefined;
  const previous = data.previous as PeriodStats | undefined;
  const changePct = data.change_pct as number | null | undefined;

  if (!current || !previous) {
    return <p className="text-xs text-gray-400">No trend data.</p>;
  }

  const trendColor =
    changePct == null
      ? "text-gray-700"
      : changePct > 0
        ? "text-green-600"
        : changePct < 0
          ? "text-red-600"
          : "text-gray-700";

  const rows: [string, React.ReactNode][] = [
    ["Period", period ?? "—"],
    ["Reviews (current)", current.count],
    ["Reviews (prior)", previous.count],
    ...(changePct != null
      ? [
          [
            "Change",
            <span key="chg" className={trendColor}>
              {changePct > 0 ? "+" : ""}
              {changePct}%
            </span>,
          ] as [string, React.ReactNode],
        ]
      : []),
    ...(current.avg_rating != null
      ? [["Avg rating", `★ ${current.avg_rating}`] as [string, React.ReactNode]]
      : []),
  ];

  return (
    <div className="divide-y divide-gray-100">
      {rows.map(([label, value]) => (
        <div key={label} className="flex items-center justify-between py-1.5 text-sm">
          <span className="text-gray-500">{label}</span>
          <span className="font-medium text-gray-800">{value}</span>
        </div>
      ))}
    </div>
  );
}
