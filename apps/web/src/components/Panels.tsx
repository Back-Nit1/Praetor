import { useEffect, useRef } from "react";
import type { AttackPath, Domain, Fix, LedgerView, RemediationPlan, RiskFinding, RoundResult } from "../types";
import { DOMAINS } from "../types";
import { ATTACKERS, SEVERITY, domainSeverity, fixTarget, lossRange, pct, title, usd } from "../lib";
import { Empty, ErrorBox, SevBadge, SimBadge, Skeleton } from "./ui";

const fixLabel = (id: string) => `${title(id.split(":")[0])} · ${fixTarget(id)}`;

export function Attackers({ paths, selectedId, onSelect }: { paths: AttackPath[]; selectedId?: string; onSelect: (id: string) => void }) {
  return (
    <ul className="grid gap-2">
      {ATTACKERS.map((a) => {
        const mine = paths.filter((p) => p.persona_id === a.id);
        return (
          <li key={a.id} className="rounded border border-line bg-raised p-3">
            <div className="flex items-center justify-between gap-2">
              <span className="font-medium">{a.name}</span>
              {mine.length ? <SevBadge s={Math.max(...mine.map((p) => p.severity))} /> : <span className="text-xs text-muted">Failed — no viable path</span>}
            </div>
            <p className="text-xs text-muted">{a.note}</p>
            {mine.map((p) => (
              <button key={p.id} onClick={() => onSelect(p.id)} aria-pressed={p.id === selectedId}
                className={`mt-2 mr-2 rounded border px-2 py-1 text-xs hover:border-accent ${p.id === selectedId ? "border-accent text-accent" : "border-line"}`}>
                {title(p.domain)} path · {pct(p.success_prob)} success
              </button>
            ))}
          </li>
        );
      })}
    </ul>
  );
}

export function Timeline({ path }: { path?: AttackPath }) {
  if (!path) return <Empty>No attack path selected. Pick an attacker path to see its timeline.</Empty>;
  const attacker = ATTACKERS.find((a) => a.id === path.persona_id)?.name ?? path.persona_id;
  const physical = path.domain === "physical";
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <SevBadge s={path.severity} />
        <span>{title(path.domain)}</span><span className="text-muted">· {attacker}</span>
        <span className="font-mono text-xs text-muted">{pct(path.success_prob)} success · {path.total_minutes} min · {usd(path.total_cost_usd)} attacker cost</span>
      </div>
      {physical ? (
        <p className="mt-3 rounded border border-line bg-raised p-3 text-sm text-muted">
          Physical-risk results show severity and defenses only. Attack steps are intentionally not shown.
        </p>
      ) : (
        <>
          {path.narrative && <p className="mt-3 text-sm">{path.narrative}</p>}
          <ol className="mt-3 grid gap-2">
            {path.steps.map((s, i) => (
              <li key={i} className="rounded border border-line bg-raised p-2 text-sm">
                <div className="flex justify-between gap-2"><span>{i + 1}. {s.action}</span><span className="font-mono text-xs text-muted">{pct(s.success_prob)}</span></div>
                <div className="mt-1.5 h-1.5 rounded bg-line" aria-hidden><div className="h-full rounded bg-accent" style={{ width: `${Math.max(4, (s.minutes / (path.total_minutes || 1)) * 100)}%` }} /></div>
                <p className="mt-1 font-mono text-xs text-muted">{s.minutes} min · {usd(s.cost_usd)}</p>
              </li>
            ))}
          </ol>
        </>
      )}
      {path.pretext_template && (
        <figure className="mt-3 rounded border border-accent p-3">
          <figcaption className="mb-1 flex items-center gap-2 text-xs text-muted"><SimBadge /> Template with placeholders — never sent anywhere</figcaption>
          <blockquote className="font-mono text-xs">{path.pretext_template}</blockquote>
        </figure>
      )}
      <h3 className="mt-4 text-xs font-semibold uppercase tracking-wider text-muted">Defenses that sever this path</h3>
      <ul className="mt-1 flex flex-wrap gap-2">
        {path.fixable_elements.map((f) => <li key={f} className="rounded border border-accent px-2 py-0.5 text-xs text-accent">{fixLabel(f)}</li>)}
      </ul>
    </div>
  );
}

export function DomainCards({ findings }: { findings: RiskFinding[] }) {
  const sev = domainSeverity(findings);
  const loss = lossRange(findings);
  return (
    <div>
      <ul className="grid grid-cols-2 gap-2">
        {DOMAINS.map((d: Domain) => (
          <li key={d} className={`rounded border border-line bg-raised p-2 ${d === "financial" ? "col-span-2" : ""}`}>
            <div className="flex items-center justify-between gap-2 text-sm"><span>{title(d)}</span><SevBadge s={sev[d]} /></div>
            {d === "financial" && (
              <p className="mt-1 font-mono text-sm">
                {loss ? <>{usd(loss[0])} – {usd(loss[1])}</> : <span className="text-muted">No financial exposure found</span>}
                <span className="block text-xs text-muted">Illustrative estimate — not financial advice</span>
              </p>
            )}
          </li>
        ))}
      </ul>
      <p className="sr-only">Severity scale: {SEVERITY.join(", ")}</p>
    </div>
  );
}

export function Remediation({ plan }: { plan: RemediationPlan }) {
  if (!plan.fixes.length) return <Empty>No fixes needed — no attack paths were found.</Empty>;
  const minutes = plan.fixes.reduce((a, f) => a + f.effort_minutes, 0);
  return (
    <div>
      <p className="text-sm">
        <span className="font-mono">{plan.paths_before} → {plan.paths_after}</span> attack paths after {plan.fixes.length} fixes ·
        <span className="text-muted"> ~{minutes} min · {plan.method}</span>
      </p>
      <ol className="mt-3 grid gap-2">
        {plan.fixes.map((f: Fix, i) => (
          <li key={f.id} className="rounded border border-line bg-raised p-2 text-sm">
            <div className="flex justify-between gap-2"><span>{i + 1}. {fixLabel(f.id)}</span><span className="font-mono text-xs text-muted">severs {f.paths_severed} · {f.effort_minutes} min</span></div>
            {f.procedure && <p className="mt-1 text-xs text-muted">{f.procedure}</p>}
            {f.draft && <pre className="mt-1 whitespace-pre-wrap font-mono text-xs text-muted">{f.draft}</pre>}
          </li>
        ))}
      </ol>
      {plan.residual_notes && <p className="mt-2 text-xs text-muted">{plan.residual_notes}</p>}
      <p className="mt-2 text-xs text-muted">Opt-outs are drafted for you to submit. Praetor never submits them.</p>
    </div>
  );
}

export function League({ rounds }: { rounds: RoundResult[] }) {
  if (!rounds.length) return <Empty>No league rounds yet. Run a red/blue league to see attackers fail.</Empty>;
  const max = Math.max(1, ...rounds.map((r) => r.paths_remaining));
  const x = (i: number) => 30 + (rounds.length === 1 ? 0 : (i / (rounds.length - 1)) * 300);
  const y = (v: number) => 110 - (v / max) * 90;
  return (
    <div>
      <svg viewBox="0 0 350 130" className="h-auto w-full max-w-lg" role="img" aria-label={`Paths remaining by round: ${rounds.map((r) => `round ${r.round} ${r.paths_remaining}`).join(", ")}`}>
        <line x1="30" y1="110" x2="340" y2="110" stroke="var(--color-line)" />
        <line x1="30" y1="10" x2="30" y2="110" stroke="var(--color-line)" />
        <text x="26" y="24" textAnchor="end" className="fill-muted font-mono text-[9px]">{max}</text>
        <text x="26" y="112" textAnchor="end" className="fill-muted font-mono text-[9px]">0</text>
        <polyline fill="none" stroke="var(--color-accent)" strokeWidth={2} points={rounds.map((r, i) => `${x(i)},${y(r.paths_remaining)}`).join(" ")} />
        {rounds.map((r, i) => (
          <g key={r.round}>
            <circle cx={x(i)} cy={y(r.paths_remaining)} r={4} fill="var(--color-accent)" />
            <text x={x(i)} y={124} textAnchor="middle" className="fill-muted font-mono text-[9px]">R{r.round}</text>
          </g>
        ))}
      </svg>
      <table className="mt-2 w-full text-left text-xs">
        <caption className="sr-only">League rounds</caption>
        <thead className="text-muted"><tr><th className="py-1 pr-2">Round</th><th className="pr-2">Paths</th><th>Fixes applied / new attacker techniques</th></tr></thead>
        <tbody>
          {rounds.map((r) => (
            <tr key={r.round} className="border-t border-line align-top">
              <td className="py-1 pr-2 font-mono">{r.round}</td><td className="pr-2 font-mono">{r.paths_remaining}</td>
              <td>{[...r.fixes_applied.map(fixLabel), ...r.unlocked_techniques.map((t) => `⚡ ${title(t)}`)].join(", ") || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export type LedgerState = { status: "loading" } | { status: "error"; message: string } | { status: "ready"; data: LedgerView };

export function LedgerDrawer({ state, source, onClose, onRetry }: { state: LedgerState; source: string; onClose: () => void; onRetry: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const back = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("keydown", esc); back?.focus(); };
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-20 flex justify-end bg-black/60" onClick={onClose}>
      <aside role="dialog" aria-modal="true" aria-labelledby="ledger-title" onClick={(e) => e.stopPropagation()}
        className="h-full w-full max-w-xl overflow-y-auto border-l border-line bg-panel p-4">
        <div className="flex items-center justify-between">
          <h2 id="ledger-title" className="text-lg font-semibold">Data-flow ledger</h2>
          <button ref={closeRef} onClick={onClose} className="rounded border border-line px-3 py-1.5 hover:border-accent">Close</button>
        </div>
        <p className="mt-2 text-sm text-muted">
          Every outbound call is minimized and itemized: payload size and hash, never contents.
          {source === "api" ? " Live-mode search queries can contain identifiers." : " Fixture mode makes no outbound calls."}
        </p>
        <div className="mt-4">
          {state.status === "loading" && <Skeleton h="h-40" />}
          {state.status === "error" && <ErrorBox message={state.message} onRetry={onRetry} />}
          {state.status === "ready" && (state.data.entries.length === 0 ? <Empty>No outbound calls recorded.</Empty> : (
            <>
              <p className="mb-2 text-sm">Hash chain: <b className={state.data.verified ? "text-sev1" : "text-sev4"}>{state.data.verified ? "verified" : "BROKEN"}</b> · {state.data.entries.length} entries</p>
              <table className="w-full text-left text-xs">
                <thead className="text-muted"><tr><th className="py-1">#</th><th>Service</th><th>Purpose</th><th>Bytes</th><th>Redacted</th><th>Hash</th></tr></thead>
                <tbody>
                  {state.data.entries.map((e) => (
                    <tr key={e.id} className="border-t border-line">
                      <td className="py-1 font-mono">{e.id}</td><td>{e.service}</td><td>{e.purpose}</td>
                      <td className="font-mono">{e.bytes}</td><td className="font-mono">{e.redactions}</td><td className="font-mono" title={e.hash}>{e.hash.slice(0, 8)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ))}
        </div>
      </aside>
    </div>
  );
}
