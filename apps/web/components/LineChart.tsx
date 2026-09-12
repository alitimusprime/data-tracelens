export function LineChart({ values, color = "#5ee6b1", label }: { values: number[]; color?: string; label: string }) {
  if (!values.length) return <div className="chart-empty">Waiting for analysis windows</div>;
  const max = Math.max(...values, 1); const min = Math.min(...values, 0); const range = Math.max(max - min, 1);
  const points = values.map((value, index) => `${(index / Math.max(values.length - 1, 1)) * 100},${44 - ((value - min) / range) * 38}`).join(" ");
  return <div className="line-chart"><span>{label}</span><svg viewBox="0 0 100 48" preserveAspectRatio="none"><defs><linearGradient id={`fill-${label.replace(/\W/g, "")}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={color} stopOpacity=".25"/><stop offset="1" stopColor={color} stopOpacity="0"/></linearGradient></defs><polygon points={`0,48 ${points} 100,48`} fill={`url(#fill-${label.replace(/\W/g, "")})`} /><polyline points={points} fill="none" stroke={color} strokeWidth="1.6" vectorEffect="non-scaling-stroke" /></svg></div>;
}
