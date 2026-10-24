// Mirrors core/schemas.py (docs/CONTRACTS.md). No credential fields exist in any schema.
export const DOMAINS = ["financial", "identity", "fraud", "physical", "social", "surveillance", "professional", "inference"] as const;
export type Domain = (typeof DOMAINS)[number];

export interface GNode { id: string; type: string; label: string; attrs: Record<string, unknown>; public: boolean }
export interface GEdge { src: string; dst: string; rel: string; effort: number; fixable_by: string[] }
export interface ExposureGraph { id: string; persona_id: string; nodes: GNode[]; edges: GEdge[]; built_at: string }

export interface AttackStep { edge_ids: string[]; action: string; success_prob: number; minutes: number; cost_usd: number }
export interface AttackPath {
  id: string; persona_id: string; domain: Domain; steps: AttackStep[];
  total_minutes: number; total_cost_usd: number; success_prob: number;
  loss_low: number | null; loss_high: number | null; severity: number;
  fixable_elements: string[]; narrative: string | null; pretext_template: string | null;
}
export interface RiskFinding {
  id: string; domain: Domain; severity: number; title: string;
  evidence_node_ids: string[]; path_ids: string[]; loss_low: number | null; loss_high: number | null;
}
export interface AttackResult { paths: AttackPath[]; findings: RiskFinding[] }
export interface Fix {
  id: string; kind: string; targets: string[]; effort_minutes: number; paths_severed: number;
  procedure: string | null; draft: string | null;
}
export interface RemediationPlan { fixes: Fix[]; paths_before: number; paths_after: number; method: "milp" | "greedy"; residual_notes: string }
export interface RoundResult { round: number; paths_remaining: number; by_persona: Record<string, number>; fixes_applied: string[]; unlocked_techniques: string[] }
export interface LedgerEntry {
  id: number; ts: string; service: "tokenfactory" | "tavily" | "nebius_job"; purpose: string;
  bytes: number; payload_sha256: string; redactions: number; prev_hash: string; hash: string;
}
export interface LedgerView { entries: LedgerEntry[]; verified: boolean; summary: Record<string, unknown> }
export interface PersonaRef { id: string; name: string }
export interface Health { ok: boolean; demo_mode: boolean }

export interface Dashboard {
  graph: ExposureGraph; attack: AttackResult; plan: RemediationPlan; league: RoundResult[];
}
