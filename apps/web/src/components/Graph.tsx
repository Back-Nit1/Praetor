import type { AttackPath, ExposureGraph } from "../types";
import { fixTarget, layout, pathEdges } from "../lib";

const W = 124, H = 34;
const clip = (s: string, n = 19) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);

export function Graph({ graph, selected }: { graph: ExposureGraph; selected?: AttackPath }) {
  const { pos, width, height } = layout(graph, 180);
  // Physical paths highlight defense points only, never the route to the asset.
  const hot = selected && selected.domain !== "physical" ? pathEdges(selected) : new Set<string>();
  const defend = new Set(selected?.fixable_elements.map(fixTarget));
  const hotNodes = new Set([...hot].flatMap((k) => k.split("->")));
  const dim = selected !== undefined;

  return (
    <div className="overflow-x-auto" tabIndex={0} aria-label="Twin graph, scrollable">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-auto min-w-[680px] w-full" role="group" aria-label="Public digital twin graph">
        <defs>
          <marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" markerUnits="userSpaceOnUse" orient="auto">
            <path d="M0 0 8 4 0 8z" fill="currentColor" />
          </marker>
        </defs>
        <text x={width - 8} y={14} textAnchor="end" className="fill-muted font-mono text-[10px]" aria-hidden>
          {graph.persona_id === "self" ? "LIVE SCAN" : "SYNTHETIC · SIMULATION"}
        </text>
        {graph.edges.map((e) => {
          const a = pos.get(e.src), b = pos.get(e.dst);
          if (!a || !b) return null;
          const on = hot.has(`${e.src}->${e.dst}`);
          const x1 = a.x + W / 2, x2 = b.x - W / 2, mx = (x1 + x2) / 2;
          return (
            <path key={`${e.src}->${e.dst}`} d={`M${x1} ${a.y} C${mx} ${a.y} ${mx} ${b.y} ${x2} ${b.y}`} fill="none"
              markerEnd="url(#arrow)" strokeWidth={on ? 2.5 : 1.2}
              className={on ? "text-sev4" : "text-line"} stroke="currentColor" opacity={dim && !on ? 0.5 : 1}>
              <title>{`${e.src} ${e.rel.replace("_", " ")} ${e.dst}`}</title>
            </path>
          );
        })}
        {graph.nodes.map((n) => {
          const p = pos.get(n.id)!;
          const isDefense = defend.has(n.id);
          return (
            <g key={n.id} tabIndex={0} role="img" aria-label={`${n.type}: ${n.label}, ${n.public ? "public" : "not public"}${isDefense ? ", defense point" : ""}`}
              transform={`translate(${p.x - W / 2} ${p.y - H / 2})`} opacity={dim && !hotNodes.has(n.id) && !isDefense ? 0.75 : 1}>
              <rect width={W} height={H} rx={6} className="fill-raised" strokeWidth={isDefense ? 2.5 : 1.2}
                stroke={isDefense ? "var(--color-accent)" : hotNodes.has(n.id) ? "var(--color-sev4)" : "var(--color-line)"}
                strokeDasharray={n.public ? undefined : "4 3"} />
              <text x={W / 2} y={14} textAnchor="middle" className="fill-muted font-mono text-[8px] uppercase">{n.type.replace("_", " ")}</text>
              <text x={W / 2} y={26} textAnchor="middle" className="fill-fg text-[10px]">{clip(n.label)}</text>
              <title>{n.label}</title>
            </g>
          );
        })}
      </svg>
      <p className="mt-2 flex flex-wrap gap-x-4 text-xs text-muted">
        <span>Solid = public · dashed = not public</span>
        <span className="text-accent">Cyan outline = defense point</span>
        <span className="text-sev4">Red path = selected attack path</span>
      </p>
    </div>
  );
}
