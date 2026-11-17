// Shared chart styling (Recharts). Colors follow the validated reference palette:
// status colors for outcome series (always with legend + label), blue for single series.
export const CHART = {
  grid: "#eef0f4",
  axis: "#94a3b8",
  blue: "#2a78d6",
  good: "#0ca30c",
  critical: "#d03b3b",
  warning: "#eda100",
  neutral: "#a8a29e",
};

export const axisProps = {
  stroke: CHART.axis,
  tick: { fill: "#64748b", fontSize: 11 },
  tickLine: false,
  axisLine: false,
};

export function ChartTooltip({ active, payload, label, formatter }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs shadow-lg">
      {label !== undefined && <p className="mb-1 font-medium text-slate-800">{label}</p>}
      {payload.map((item) => (
        <div key={item.dataKey} className="flex items-center gap-2 text-slate-600">
          <span className="h-2 w-2 rounded-sm" style={{ background: item.color || item.fill }} />
          <span>{item.name}</span>
          <span className="ml-auto pl-3 font-medium text-slate-900">{formatter ? formatter(item.value) : item.value}</span>
        </div>
      ))}
    </div>
  );
}

export function LegendRow({ items }) {
  return (
    <div className="flex flex-wrap gap-4 px-5 pb-1 text-xs text-slate-600">
      {items.map(([label, color]) => (
        <span key={label} className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-sm" style={{ background: color }} /> {label}
        </span>
      ))}
    </div>
  );
}
