// The only module that talks to the API (or fixtures). Source is chosen explicitly by
// VITE_DATA_SOURCE; a failed request is surfaced as ApiError and never retried against fixtures.
import type {
  AttackResult, ExposureGraph, Health, LedgerView, PersonaRef, RemediationPlan, RoundResult,
} from "./types";

export type Source = "api" | "fixture";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export interface Client {
  source: Source;
  health(): Promise<Health>;
  personas(): Promise<PersonaRef[]>;
  twin(personaId: string): Promise<ExposureGraph>;
  attack(graphId: string): Promise<AttackResult>;
  remediate(graphId: string): Promise<RemediationPlan>;
  league(graphId: string, rounds: number): Promise<RoundResult[]>;
  ledger(): Promise<LedgerView>;
}

export function resolveSource(raw: string | undefined): Source {
  if (raw === undefined || raw === "" || raw === "api") return "api";
  if (raw === "fixture") return "fixture";
  throw new Error(`VITE_DATA_SOURCE must be "api" or "fixture", got "${raw}"`);
}

export function createClient(source: Source, base = "", fetchImpl: typeof fetch = (...a) => fetch(...a)): Client {
  return source === "fixture" ? fixtureClient() : apiClient(base, fetchImpl);
}

function apiClient(base: string, fetchImpl: typeof fetch): Client {
  async function call<T>(path: string, body?: unknown): Promise<T> {
    let res: Response;
    try {
      res = await fetchImpl(`${base}${path}`, body === undefined ? undefined : {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
      });
    } catch {
      throw new ApiError(0, `API unreachable${base ? ` at ${base}` : ""}`);
    }
    if (!res.ok) {
      const detail = await res.json().then((j: { detail?: unknown }) => String(j.detail ?? ""), () => "");
      throw new ApiError(res.status, detail || `HTTP ${res.status}`);
    }
    return res.json() as Promise<T>;
  }

  // The API streams every league round as an SSE "round" event, then "done" (or "error").
  function league(graphId: string, rounds: number): Promise<RoundResult[]> {
    return call<{ run_id: string }>("/api/league/run", { graph_id: graphId, rounds }).then(({ run_id }) =>
      new Promise<RoundResult[]>((resolve, reject) => {
        const out: RoundResult[] = [];
        const es = new EventSource(`${base}/api/events?run_id=${encodeURIComponent(run_id)}`);
        const end = (fn: () => void) => { es.close(); fn(); };
        const payload = (e: Event) => (JSON.parse((e as MessageEvent<string>).data) as { data: Record<string, unknown> }).data;
        es.addEventListener("round", (e) => out.push(payload(e) as unknown as RoundResult));
        es.addEventListener("done", () => end(() => resolve(out)));
        es.addEventListener("error", (e) => {
          const data = (e as MessageEvent<string>).data;
          end(() => reject(new ApiError(0, data ? String(payload(e).detail) : "league stream interrupted")));
        });
      }));
  }

  return {
    source: "api",
    health: () => call("/api/health"),
    personas: () => call("/api/personas"),
    twin: (persona_id) => call("/api/twin", { persona_id }),
    attack: (graph_id) => call("/api/attack", { graph_id }),
    remediate: (graph_id) => call("/api/remediate", { graph_id }),
    league,
    ledger: () => call("/api/ledger"),
  };
}

// Mirrors apps/api FixtureServiceAdapter so both modes show identical data.
function fixtureClient(): Client {
  const load = async () => {
    const [g, p, r] = await Promise.all([
      import("@fixtures/exposure_graph.json"), import("@fixtures/attack_paths.json"), import("@fixtures/round_results.json"),
    ]);
    return { graph: g.default as unknown as ExposureGraph, paths: p.default as unknown as AttackResult["paths"], rounds: r.default as unknown as RoundResult[] };
  };
  return {
    source: "fixture",
    health: async () => ({ ok: true, demo_mode: true }),
    personas: async () => {
      const { graph } = await load();
      return [{ id: graph.persona_id, name: graph.nodes.find((n) => n.type === "person")?.label ?? graph.persona_id }];
    },
    twin: async (id) => {
      const { graph } = await load();
      if (id !== graph.persona_id) throw new ApiError(404, `unknown synthetic persona: ${id}`);
      return graph;
    },
    attack: async () => {
      const { paths } = await load();
      const findings = paths.map((p) => ({
        id: `finding-${p.id}`, domain: p.domain, severity: p.severity,
        title: `${p.domain[0].toUpperCase()}${p.domain.slice(1)} exposure`,
        evidence_node_ids: [...new Set(p.steps.flatMap((s) => s.edge_ids.flatMap((e) => e.split("->"))))],
        path_ids: [p.id], loss_low: p.loss_low, loss_high: p.loss_high,
      }));
      return { paths, findings };
    },
    remediate: async () => {
      const { paths } = await load();
      return greedyPlan(paths);
    },
    league: async () => (await load()).rounds,
    ledger: async () => ({ entries: [], verified: true, summary: { entries: 0, bytes: 0, by_service: {} } }),
  };
}

export function greedyPlan(paths: AttackResult["paths"]): RemediationPlan {
  let remaining = paths.map((p) => new Set(p.fixable_elements));
  const fixes: RemediationPlan["fixes"] = [];
  while (remaining.length) {
    const counts = new Map<string, number>();
    remaining.forEach((s) => s.forEach((f) => counts.set(f, (counts.get(f) ?? 0) + 1)));
    const best = [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0];
    if (!best) break;
    const [id, n] = best;
    const [kind, target = id] = id.split(":");
    fixes.push({ id, kind, targets: [target], effort_minutes: 15, paths_severed: n, procedure: null, draft: null });
    remaining = remaining.filter((s) => !s.has(id));
  }
  return { fixes, paths_before: paths.length, paths_after: remaining.length, method: "greedy", residual_notes: "Fixture-backed estimate." };
}
