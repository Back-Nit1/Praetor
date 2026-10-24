import type { AttackPath, Domain, ExposureGraph, RiskFinding } from "./types";
import { DOMAINS } from "./types";

export const SEVERITY = ["None", "Low", "Moderate", "High", "Critical"] as const;
export const sevColor = (s: number) => `var(--color-sev${Math.min(Math.max(s, 0), 4)})`;

// Attacker ids/names are fixed by the contract (core/personas/personas.yaml); the API only lists synthetic victims.
export const ATTACKERS = [
  { id: "opportunist", name: "Opportunist", note: "Low-effort, takes the easiest exposure" },
  { id: "id_theft_reseller", name: "Identity-theft reseller", note: "Correlates public identity attributes" },
  { id: "targeted_fraudster", name: "Targeted fraudster", note: "Persistent path to a financial asset" },
  { id: "personal_threat", name: "Personal threat", note: "Modeled for physical-safety severity only" },
  { id: "insider", name: "Insider", note: "Uses known workplace context" },
] as const;

export const title = (s: string) => s.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase());

export function domainSeverity(findings: RiskFinding[]): Record<Domain, number> {
  const out = Object.fromEntries(DOMAINS.map((d) => [d, 0])) as Record<Domain, number>;
  for (const f of findings) out[f.domain] = Math.max(out[f.domain], f.severity);
  return out;
}

export function lossRange(findings: RiskFinding[]): [number, number] | null {
  const fin = findings.filter((f) => f.domain === "financial" && f.loss_low != null && f.loss_high != null);
  if (!fin.length) return null;
  return [fin.reduce((a, f) => a + f.loss_low!, 0), fin.reduce((a, f) => a + f.loss_high!, 0)];
}

export const usd = (n: number) => `$${n.toLocaleString("en-US")}`;
export const pct = (p: number) => `${Math.round(p * 100)}%`;

export const fixTarget = (fixId: string) => fixId.split(":")[1] ?? fixId;

// Layered left-to-right layout: column = BFS depth from the person node (unreachable nodes go last).
export function layout(g: ExposureGraph, colW = 170, rowH = 70, padX = 76, padY = 34) {
  const depth = new Map<string, number>();
  const root = g.nodes.find((n) => n.type === "person")?.id ?? g.nodes[0]?.id;
  if (root) depth.set(root, 0);
  for (let queue = root ? [root] : []; queue.length; ) {
    const id = queue.shift()!;
    for (const e of g.edges) if (e.src === id && !depth.has(e.dst)) { depth.set(e.dst, depth.get(id)! + 1); queue.push(e.dst); }
  }
  const last = Math.max(0, ...depth.values()) + 1;
  const cols = new Map<number, string[]>();
  for (const n of g.nodes) {
    const d = depth.get(n.id) ?? last;
    cols.set(d, [...(cols.get(d) ?? []), n.id]);
  }
  const maxRows = Math.max(1, ...[...cols.values()].map((c) => c.length));
  const pos = new Map<string, { x: number; y: number }>();
  for (const [d, ids] of cols) {
    ids.forEach((id, i) => pos.set(id, { x: padX + d * colW, y: padY + ((maxRows - ids.length) / 2 + i) * rowH }));
  }
  return { pos, width: padX * 2 + Math.max(...cols.keys(), 0) * colW, height: padY * 2 + (maxRows - 1) * rowH };
}

export const pathEdges = (p: AttackPath) => new Set(p.steps.flatMap((s) => s.edge_ids));
