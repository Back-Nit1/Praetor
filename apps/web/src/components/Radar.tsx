import { DOMAINS } from "../types";
import type { Domain } from "../types";
import { SEVERITY, title } from "../lib";

const C = 130, R = 88;
const pt = (i: number, v: number) => {
  const a = (Math.PI * 2 * i) / DOMAINS.length - Math.PI / 2;
  return [C + Math.cos(a) * R * (v / 4), C + Math.sin(a) * R * (v / 4)] as const;
};

export function Radar({ sev }: { sev: Record<Domain, number> }) {
  const poly = DOMAINS.map((d, i) => pt(i, sev[d]).join(",")).join(" ");
  return (
    <svg viewBox="-40 0 340 260" className="mx-auto h-auto w-full max-w-[300px]" role="img"
      aria-label={`Risk radar. ${DOMAINS.map((d) => `${title(d)} ${SEVERITY[sev[d]]}`).join(", ")}`}>
      {[1, 2, 3, 4].map((r) => (
        <polygon key={r} points={DOMAINS.map((_, i) => pt(i, r).join(",")).join(" ")} fill="none" stroke="var(--color-line)" />
      ))}
      {DOMAINS.map((d, i) => {
        const [x, y] = pt(i, 4), [lx, ly] = pt(i, 5.0);
        return (
          <g key={d}>
            <line x1={C} y1={C} x2={x} y2={y} stroke="var(--color-line)" />
            <text x={lx} y={ly} textAnchor={lx < C - 4 ? "end" : lx > C + 4 ? "start" : "middle"} dominantBaseline="middle" className="fill-muted text-[9px]">{title(d)}</text>
          </g>
        );
      })}
      <polygon points={poly} fill="var(--color-accent)" fillOpacity={0.22} stroke="var(--color-accent)" strokeWidth={2} />
      {DOMAINS.map((d, i) => { const [x, y] = pt(i, sev[d]); return <circle key={d} cx={x} cy={y} r={3} fill="var(--color-accent)" />; })}
    </svg>
  );
}
