import { useCallback, useEffect, useState } from "react";
import { ApiError, type Client } from "./api";
import { Graph } from "./components/Graph";
import { Attackers, DomainCards, League, LedgerDrawer, Remediation, Timeline, type LedgerState } from "./components/Panels";
import { Radar } from "./components/Radar";
import { Empty, ErrorBox, Panel, SimBadge, Skeleton } from "./components/ui";
import { domainSeverity } from "./lib";
import type { Dashboard, PersonaRef } from "./types";

type Load<T> = { status: "loading" } | { status: "error"; message: string } | { status: "ready"; data: T };
const msg = (e: unknown) => (e instanceof ApiError || e instanceof Error ? e.message : String(e));

export function App({ client }: { client: Client }) {
  const [personas, setPersonas] = useState<Load<PersonaRef[]>>({ status: "loading" });
  const [personaId, setPersonaId] = useState<string>();
  const [dash, setDash] = useState<Load<Dashboard>>({ status: "loading" });
  const [pathId, setPathId] = useState<string>();
  const [ledger, setLedger] = useState<LedgerState | null>(null);

  const loadPersonas = useCallback(() => {
    setPersonas({ status: "loading" });
    client.personas().then(
      (data) => { setPersonas({ status: "ready", data }); setPersonaId((cur) => cur ?? data[0]?.id); },
      (e) => setPersonas({ status: "error", message: msg(e) }),
    );
  }, [client]);
  useEffect(loadPersonas, [loadPersonas]);

  const loadDash = useCallback(() => {
    if (!personaId) return;
    setDash({ status: "loading" });
    setPathId(undefined);
    client.twin(personaId).then(async (graph) => {
      const [attack, plan, league] = await Promise.all([client.attack(graph.id), client.remediate(graph.id), client.league(graph.id, 5)]);
      setDash({ status: "ready", data: { graph, attack, plan, league } });
      setPathId(attack.paths.slice().sort((a, b) => b.severity - a.severity)[0]?.id);
    }).catch((e) => setDash({ status: "error", message: msg(e) }));
  }, [client, personaId]);
  useEffect(loadDash, [loadDash]);

  const openLedger = useCallback(() => {
    setLedger({ status: "loading" });
    client.ledger().then((data) => setLedger({ status: "ready", data }), (e) => setLedger({ status: "error", message: msg(e) }));
  }, [client]);
  const closeLedger = useCallback(() => setLedger(null), []);

  const d = dash.status === "ready" ? dash.data : undefined;
  const selected = d?.attack.paths.find((p) => p.id === pathId);
  const synthetic = personaId !== "self";

  return (
    <div className="mx-auto max-w-[1440px] px-4 pb-10">
      <header className="flex flex-wrap items-center gap-3 py-4">
        <h1 className="text-xl font-semibold tracking-tight">Praetor</h1>
        <span className="text-sm text-muted">Personal security agent · red/blue league</span>
        <span className="ml-auto rounded border border-line px-2 py-1 font-mono text-xs text-muted">
          {client.source === "fixture" ? "FIXTURE MODE (offline)" : "LIVE API"}
        </span>
        {personas.status === "ready" && personas.data.length > 0 && (
          <label className="flex items-center gap-2 text-sm">
            <span className="text-muted">Synthetic persona</span>
            <select value={personaId} onChange={(e) => setPersonaId(e.target.value)} className="rounded border border-line bg-raised px-2 py-1.5">
              {personas.data.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </label>
        )}
        <button onClick={openLedger} className="rounded border border-line bg-raised px-3 py-1.5 text-sm hover:border-accent">Ledger</button>
      </header>

      <div role="note" className="mb-4 flex flex-wrap items-center gap-2 rounded border border-accent bg-raised px-3 py-2 text-sm">
        <SimBadge>{synthetic ? "SYNTHETIC · SIMULATION" : "SIMULATION"}</SimBadge>
        <span>{synthetic ? "Fictional persona with reserved example data. Attackers are simulated; nothing here targets a real person." : "Simulated attackers run against your own public footprint."} Financial figures are illustrative — not financial advice.</span>
      </div>

      {personas.status === "error" ? <ErrorBox message={personas.message} onRetry={loadPersonas} />
        : personas.status === "ready" && personas.data.length === 0 ? <Empty>No synthetic personas available.</Empty>
        : dash.status === "error" ? <ErrorBox message={dash.message} onRetry={loadDash} />
        : !d ? <div className="grid gap-4 xl:grid-cols-12"><div className="xl:col-span-8"><Skeleton h="h-80" /></div><div className="xl:col-span-4"><Skeleton h="h-80" /></div></div>
        : (
          <main className="grid gap-4 xl:grid-cols-12">
            <Panel id="h-graph" title="Public digital twin" className="xl:col-span-8" aside={<span className="font-mono text-xs text-muted">{d.graph.nodes.length} nodes · {d.graph.edges.length} edges</span>}>
              <Graph graph={d.graph} selected={selected} />
            </Panel>
            <Panel id="h-att" title="Simulated attackers" className="xl:col-span-4">
              <Attackers paths={d.attack.paths} selectedId={pathId} onSelect={setPathId} />
            </Panel>
            <Panel id="h-time" title="Selected attack timeline" className="xl:col-span-5"><Timeline path={selected} /></Panel>
            <Panel id="h-radar" title="Risk radar" className="xl:col-span-3"><Radar sev={domainSeverity(d.attack.findings)} /></Panel>
            <Panel id="h-dom" title="Damage by domain" className="xl:col-span-4"><DomainCards findings={d.attack.findings} /></Panel>
            <Panel id="h-rem" title="Smallest fix set" className="xl:col-span-6"><Remediation plan={d.plan} /></Panel>
            <Panel id="h-league" title="League: paths remaining" className="xl:col-span-6"><League rounds={d.league} /></Panel>
          </main>
        )}

      {ledger && <LedgerDrawer state={ledger} source={client.source} onClose={closeLedger} onRetry={openLedger} />}
    </div>
  );
}
