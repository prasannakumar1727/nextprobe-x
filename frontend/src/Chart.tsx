type Pt = { x: number; y: number; color?: string; onClick?: () => void; title?: string };
export function Chart(p: { width: number; height: number; xLabel: string; yLabel: string; points?: Pt[]; line?: { x: number; y: number }[]; hlines?: { y: number; label: string }[];
  pred?: { x: number; lo: number; mid: number; hi: number }; hiddenX?: number[]; xMax?: number; multi?: { color: string; label: string; pts: { x: number; y: number }[] }[] }) {
  const m = { l: 48, r: 12, t: 10, b: 34 }, W = p.width, H = p.height;
  const xs: number[] = [0, ...(p.points ?? []).map(a => a.x), ...(p.multi ?? []).flatMap(s => s.pts.map(a => a.x)), ...(p.pred ? [p.pred.x] : [])];
  const ys: number[] = [...(p.points ?? []).map(a => a.y), ...(p.hlines ?? []).map(a => a.y), ...(p.multi ?? []).flatMap(s => s.pts.map(a => a.y)), ...(p.pred ? [p.pred.lo, p.pred.hi] : [])];
  const x1 = p.xMax ?? Math.max(...xs), x0 = Math.min(...xs), y0 = Math.min(0, ...ys), y1 = Math.max(...ys) * 1.05 || 1;
  const X = (v: number) => m.l + ((v - x0) / (x1 - x0 || 1)) * (W - m.l - m.r), Y = (v: number) => H - m.b - ((v - y0) / (y1 - y0 || 1)) * (H - m.t - m.b);
  const ticks = (a: number, b: number) => Array.from({ length: 5 }, (_, i) => a + ((b - a) * i) / 4);
  return <svg width={W} height={H} style={{ background: "#fff", border: "1px solid #cfd6de", maxWidth: "100%" }}>
    {ticks(y0, y1).map((t, i) => <g key={i}><line x1={m.l} x2={W - m.r} y1={Y(t)} y2={Y(t)} stroke="#e3e8ee" /><text x={m.l - 4} y={Y(t) + 4} fontSize="10" textAnchor="end" fontFamily="monospace">{t.toFixed(t < 10 ? 1 : 0)}</text></g>)}
    {ticks(x0, x1).map((t, i) => <text key={i} x={X(t)} y={H - m.b + 14} fontSize="10" textAnchor="middle" fontFamily="monospace">{t.toFixed(0)}</text>)}
    <text x={(W + m.l) / 2} y={H - 4} fontSize="11" textAnchor="middle">{p.xLabel}</text><text x={10} y={H / 2} fontSize="11" transform={`rotate(-90 10 ${H / 2})`} textAnchor="middle">{p.yLabel}</text>
    {p.hlines?.map(h => <g key={h.label}><line x1={m.l} x2={W - m.r} y1={Y(h.y)} y2={Y(h.y)} stroke="#b3261e" strokeDasharray="4 3" /><text x={W - m.r - 2} y={Y(h.y) - 3} fontSize="10" textAnchor="end" fill="#b3261e">{h.label}</text></g>)}
    {p.hiddenX?.map(hx => <g key={hx}><line x1={X(hx)} x2={X(hx)} y1={m.t} y2={H - m.b} stroke="#8a97a6" strokeDasharray="2 4" /><text x={X(hx)} y={m.t + 10} fontSize="10" textAnchor="middle" fill="#5b6675">{hx}h HIDDEN</text></g>)}
    {p.line && <polyline fill="none" stroke="#141c2b" strokeWidth="1.5" points={p.line.map(a => `${X(a.x)},${Y(a.y)}`).join(" ")} />}
    {p.pred && p.line && <><line x1={X(p.line[p.line.length - 1].x)} y1={Y(p.line[p.line.length - 1].y)} x2={X(p.pred.x)} y2={Y(p.pred.mid)} stroke="#2d4a6b" strokeDasharray="5 3" />
      <line x1={X(p.pred.x)} x2={X(p.pred.x)} y1={Y(p.pred.lo)} y2={Y(p.pred.hi)} stroke="#2d4a6b" strokeWidth="6" opacity=".35" /><circle cx={X(p.pred.x)} cy={Y(p.pred.mid)} r="4" fill="none" stroke="#2d4a6b" strokeWidth="2" /><text x={X(p.pred.x)} y={Y(p.pred.hi) - 4} fontSize="10" textAnchor="end" fill="#2d4a6b">predicted 168h</text></>}
    {p.multi?.map(s => <g key={s.label}><polyline fill="none" stroke={s.color} strokeWidth="1.8" points={s.pts.map(a => `${X(a.x)},${Y(a.y)}`).join(" ")} />{s.pts.map((a, i) => <circle key={i} cx={X(a.x)} cy={Y(a.y)} r="2.5" fill={s.color} />)}</g>)}
    {p.points?.map((a, i) => <circle key={i} cx={X(a.x)} cy={Y(a.y)} r={p.line ? 4 : 2.5} fill={a.color ?? "#2d4a6b"} opacity={p.line ? 1 : 0.7} onClick={a.onClick} style={{ cursor: a.onClick ? "pointer" : "default" }}><title>{a.title}</title></circle>)}
    {p.multi && <g>{p.multi.map((s, i) => <g key={s.label}><rect x={m.l + 6} y={m.t + 4 + i * 13} width="8" height="8" fill={s.color} /><text x={m.l + 18} y={m.t + 12 + i * 13} fontSize="10">{s.label}</text></g>)}</g>}
  </svg>;
}
