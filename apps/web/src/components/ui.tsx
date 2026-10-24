import type { ReactNode } from "react";
import { SEVERITY, sevColor } from "../lib";

export function Panel({ id, title, aside, className = "", children }: { id: string; title: string; aside?: ReactNode; className?: string; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className={`rounded-lg border border-line bg-panel p-4 ${className}`}>
      <div className="mb-3 flex items-baseline justify-between gap-2">
        <h2 id={id} className="text-xs font-semibold uppercase tracking-wider text-muted">{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  );
}

// Severity is always text + color, never color alone.
export function SevBadge({ s }: { s: number }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded border px-1.5 py-0.5 font-mono text-xs" style={{ borderColor: sevColor(s), color: sevColor(s) }}>
      <span aria-hidden className="inline-block size-2 rounded-full" style={{ background: sevColor(s) }} />
      {SEVERITY[s] ?? `S${s}`}
    </span>
  );
}

export const SimBadge = ({ children = "SIMULATION" }: { children?: ReactNode }) => (
  <span className="rounded border border-accent px-1.5 py-0.5 font-mono text-[11px] font-bold tracking-widest text-accent">{children}</span>
);

export const Empty = ({ children }: { children: ReactNode }) => (
  <p className="rounded border border-dashed border-line px-3 py-6 text-center text-sm text-muted">{children}</p>
);

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded border border-sev4 bg-raised p-4 text-sm">
      <p className="font-semibold text-sev4">Request failed</p>
      <p className="mt-1 text-fg">{message}</p>
      <p className="mt-1 text-muted">No fixture data is substituted. Fix the API or set VITE_DATA_SOURCE=fixture explicitly.</p>
      {onRetry && <button onClick={onRetry} className="mt-3 rounded border border-line bg-panel px-3 py-1.5 hover:border-accent">Retry</button>}
    </div>
  );
}

export const Skeleton = ({ h = "h-24" }: { h?: string }) => <div role="status" aria-label="Loading" className={`skeleton ${h} w-full`} />;
