# Frontend (apps/web)
## Done
- Milestone 1: React+Vite+TS+Tailwind dashboard: twin graph, 5 attackers, timeline, 8-domain radar + cards, remediation, league chart, ledger drawer, SIMULATION labels.
- One API layer `src/api.ts`; `VITE_DATA_SOURCE=api|fixture` (default api, invalid = startup error, API failure never falls back to fixtures).
- Physical paths render severity + defenses only. No `<input>`/credential fields anywhere.
- Verified: `cd apps/web && npm test` -> 14 passed; `npm run build` (tsc --noEmit + vite build) -> OK; `make test-fast` -> 68 passed.
- Run: `cd apps/web && VITE_DATA_SOURCE=fixture npm run dev` (or `make dev` API + `npm run dev`; /api proxied to :8000).
## In progress
- None.
## Next
- Mobile pass on a real device; live-API run once core adapter merges; league re-run button.
## Contract requests
- Attacker persona metadata (name/motive/goal_domain) endpoint, e.g. GET /api/attackers; UI hardcodes the 5 contract ids/names in `src/lib.ts`.
- Fixture `/api/ledger` is empty, so the drawer only shows its empty state until the core adapter is used.
## Blockers
- None.
