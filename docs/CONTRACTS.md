# Praetor contracts

The only thing you may assume about another module. Source of truth for types: `core/schemas.py`
(pydantic v2, `extra="forbid"`). Only T0 edits this file and `core/schemas.py`; request changes under
`## Contract requests` in your `docs/STATUS/<name>.md`.

## Schemas (summary — see `core/schemas.py`)

| Model | Fields |
|---|---|
| Fact | id, kind(name\|address\|phone\|email\|handle\|employer\|relative_token\|account\|breach\|photo_meta\|listing\|inference), value, source_url?, source_kind(broker\|breach\|social\|public_record\|search), confidence 0-1, found_at |
| Node | id, type(person\|identifier\|account\|broker\|service\|asset\|relative_token\|event), label, attrs{}, public |
| Edge | src, dst, rel(listed_on\|recovers\|verifies\|reveals\|derived_from\|owns\|related_to), effort 0-1, fixable_by[fix_id]. `edge.key == "src->dst"` |
| ExposureGraph | id, persona_id ("self" for live scans), nodes[], edges[], built_at. Validates edges point at real nodes |
| Persona | id, name, goal_domain, skill 1-5, budget_steps, patience, laziness 0-1, attention_k, tools[], motive |
| AttackStep | edge_ids[edge.key], action, success_prob, minutes, cost_usd |
| AttackPath | id, persona_id, domain, steps[], total_minutes, total_cost_usd, success_prob, loss_low?/loss_high? (financial only), severity 0-4, fixable_elements[fix_id], narrative?, pretext_template? (must contain `SIMULATION`) |
| RiskFinding | id, domain, severity 0-4, title, evidence_node_ids[], path_ids[], loss_low?, loss_high? |
| Fix | id, kind (open set, catalog is truth), targets[], effort_minutes, paths_severed, procedure?, draft? |
| RemediationPlan | fixes[] (ordered), paths_before, paths_after, method(milp\|greedy), residual_notes |
| RoundResult | round, paths_remaining, by_persona{persona_id: n}, fixes_applied[], unlocked_techniques[] |
| LedgerEntry | id, ts, service(tokenfactory\|tavily\|nebius_job), purpose, bytes, payload_sha256, redactions, prev_hash, hash |
| Event (SSE) | type(progress\|round\|done\|error), run_id, data{}, ts |

Domains: `financial, identity, fraud, physical, social, surveillance, professional, inference` (`core.schemas.DOMAINS`).

### IDs everyone shares
- **Fix id** = `<kind>:<target_node_id>`, e.g. `optout:broker_peoplesearch`, `passkey:acct_email`. T2 writes these
  into `Edge.fixable_by`; T3 copies them into `AttackPath.fixable_elements`; T4's catalog defines the kinds.
- **Persona ids**: `opportunist`, `id_theft_reseller`, `targeted_fraudster`, `personal_threat`, `insider`.
- **Synthetic persona ids**: `pat-example-01` (+ 2 more from T2). Live scans use `persona_id="self"`.
- Fixtures: `data/fixtures/{exposure_graph,attack_paths,round_results}.json` — valid against the schemas (tested).

## API (T5)

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | /api/health | — | `{"ok": true, "demo_mode": bool}` |
| GET | /api/personas | — | synthetic persona list `[{id, name}]` |
| POST | /api/twin | TwinRequest `{persona_id}` or `{seeds, attest:true}` | ExposureGraph |
| POST | /api/attack | GraphRef `{graph_id}` | AttackResult `{paths, findings}` |
| POST | /api/remediate | GraphRef | RemediationPlan |
| POST | /api/league/run | LeagueRunRequest `{graph_id, rounds}` | RunRef `{run_id}` |
| GET | /api/events?run_id= | — | SSE stream of Event |
| GET | /api/ledger | — | `{entries: LedgerEntry[], verified: bool, summary}` |
| POST | /api/watch/run | — | RunRef |

`PRAETOR_DEMO_MODE=1`: `seeds` requests return 403 with a clear message. Errors: `{"detail": str}`.

## Module ownership + call graph

| Module | Owner | Public surface | Calls |
|---|---|---|---|
| core/schemas.py, docs/CONTRACTS.md, Makefile | T0 | types | — |
| core/llm | T1 | `chat(tier, messages, purpose, json_schema=None) -> str\|dict`, `BudgetExceeded`; `redact(text) -> (text, map)`, `rehydrate(text, map)` | ledger |
| core/ledger | T1 | `record(service, purpose, payload_bytes, redactions) -> LedgerEntry`, `verify_chain() -> bool`, `summary() -> dict`, `entries() -> list[LedgerEntry]` | — |
| core/recon | T2 | `search(query, attest) -> list[dict]` (Tavily shape), `extract(snippets) -> list[Fact]` | llm (NANO), ledger |
| core/graph, core/twin.py | T2 | `build_graph(facts, persona_id="self") -> ExposureGraph`; `build_twin(persona_id=None, seeds=None, attest=False) -> ExposureGraph`; `twin_gap(truth, twin) -> float`; `core.recon.synthetic.list_personas() -> [{id, name}]` | recon |
| core/personas | T3 | `load_personas() -> list[Persona]`, tech tree `techniques_for(round) -> list[str]` | — |
| core/attack | T3 | `run_attacks(graph, personas, seed=0, round=0) -> list[AttackPath]` | llm (ULTRA/SUPER, narration only) |
| core/risk | T3 | `score(graph, paths) -> list[RiskFinding]` | — |
| core/remediate | T4 | `plan(paths, catalog=None) -> RemediationPlan`; `apply(graph, fixes) -> ExposureGraph`; `draft_optouts(graph) -> list[Fix]` | recon (Tavily), llm (SUPER) |
| core/league | T4 | `run_league(graph, rounds, on_event=None) -> list[RoundResult]`; CLI `python -m core.league.job` | attack, risk, remediate |
| core/watch | T4 | `run_watch(...) -> list[RiskFinding]` | recon, league |
| apps/api | T5 | HTTP above | all core |
| apps/web | T6 | UI | apps/api only |
| agent/ | T7 | Hermes skills over HTTP | apps/api only |

Rule: core modules never import apps; `apps/web` and `agent/` talk only HTTP.

### build_twin errors (decided at gate 1)
`PermissionError` (demo mode + seeds → API 403) · `ValueError` (no attest / unknown persona → 4xx) · `NotImplementedError`
(live recon not built → 501). Fact-derived `Node.attrs` carry normalized `kind`/`key`; `twin_gap` relies on them.

## Guardrails encoded in schemas
No credential fields anywhere (extra fields rejected) · live twin needs `attest=True` · pretext templates must carry
`SIMULATION` · $ ranges only on financial paths · relatives are `relative_token` nodes only.
