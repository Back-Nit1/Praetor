# NEMESIS — build plan

Nebius x NVIDIA Global AI Hackathon · **Personal AI track** · solo build with parallel Claude Code terminals
Deadline: **Fri Oct 30 2026, 1:00pm EDT** (10:00am PDT). Target submit: **Fri 9:00am EDT**.
Written Sat Oct 24 2026. Sources at the bottom.

---

## 0. TL;DR

An always-on personal security agent. It builds a **public digital twin** of you (only what a stranger can
find online), unleashes **five human-like simulated attackers** on it, scores the damage across **financial,
identity, fraud, physical, social, surveillance, professional and inference risk**, computes the **smallest
set of fixes** that cuts the most attack paths, applies them, and re-attacks until the attackers fail. Then it
keeps watching. A **data-flow ledger** itemizes every byte that leaves the machine.

Kit contents:
| File | Purpose |
|---|---|
| `plan.md` | this file (lead terminal only) |
| `CLAUDE.md` | mission + guardrails + token/git rules; **every terminal auto-reads it** |
| `scripts/setup_worktrees.sh` | one worktree + branch per terminal, installs secret-scan hook |
| `scripts/autocommit.sh` | commits every 4 min in every `feat/*` worktree |
| `scripts/merge_and_cleanup.sh` | rebase → test → PR/merge into `main` → (final) delete worktree + branch |
| `scripts/precommit-secrets.sh` | blocks keys / `.env` from being committed |

Scripts were tested end-to-end in a scratch repo (worktrees, autocommit, secret block, milestone merge, final
cleanup, rebase-conflict exit, mid-rebase skip). The **PR path (`gh`) was not testable** here — try it once early.

---

## 1. Mission brief (what Claude Code must internalize)

**Problem.** Data about us is everywhere: brokers sell addresses/phones/relatives, breaches spill emails,
photos and posts reveal where we live, public records tie it together. Attackers chain small leaks into
account takeover, fraud, identity theft, stalking, and social engineering of us and our families. Existing
services report "12 listings removed" — they never show the *attack you'd really face* or the *shortest path
to safety*.

**Why it matters.** This is the most universal personal risk there is: financial, physical and social
wellbeing all depend on what strangers can learn about you. As more of life is mirrored online, the attack
surface grows faster than anyone can manually shrink it.

**How.** Digital twin → adversary simulation → risk radar → min-cut remediation → red/blue loop → always-on
watch, with privacy-by-design (self-only, local-first, redaction, ledger). Agents are **people-like**:
personas with motives, skill, laziness, limited attention, dead ends, and quit thresholds, so scores
reflect who would *realistically* come after you.

**Honest framing for judges.** Discovery is partial (Tavily is a search API, not a crawler; many brokers
block bots). The ledger says "minimized and itemized", not "nothing leaves your machine". Dollar figures
are illustrative. Residual risk never hits exactly zero and the UI shows what remains.

---

## 2. Scope tiers

**Tier A — the entry (must ship by Wed night)**
- Synthetic persona generator + offline fixtures (demo never flakes) · twin builder from facts
- Tavily recon (live, self-only, local) + Nano extraction
- 5 personas × 8 risk domains, deterministic path search + LLM narratives (Ultra)
- Dollar/severity scoring · min-hitting-set remediation · red/blue league loop (rounds chart)
- Ledger (hash-chained) + redaction · FastAPI + React UI (graph, radar, league chart, ledger)
- Deployed on Nebius (Endpoint for API+UI, Job for league run) · README, MIT, demo video

**Tier B — strong adds (Wed–Thu if on schedule)**
- Always-on watch (scheduled Nebius Job + in-app scheduler): re-scan diff, breach-news check via Tavily
- Opt-out drafting with live Tavily lookup of each broker's current procedure
- Canary aliases + **data-lineage map** (who sold your data to whom)
- Hermes Agent inside NemoClaw/OpenShell as the "always-on personal agent shell" (see T7, timeboxed)
- Pre-commit guard (browser/editor hook: "this photo/post narrows your location")

**Tier C — stretch (only if everything above is green)**
- Learned attacker priors: bandit over strategy templates across N synthetic personas, run as parallel Nebius Jobs
- Honeytokens / twin poisoning · life-event forecasting · ExposureBench release
- LoRA/fine-tune of a small attacker model (Token Factory advertises serverless fine-tuning; **verify before promising**)

**Out of scope (deliberately):** family/third-party lookups, auto-submitting opt-outs, logins/CAPTCHA, any
real-person target on the hosted demo.

### Risk domains
| Domain | What it exposes | Detector inputs | Output |
|---|---|---|---|
| Financial | takeover paths, payment-handle leaks, freeze gaps | recovery chain, breach hits, handles | $ range (illustrative) |
| Identity | can public data pass KBA ("previous address?") | listings, relatives tokens, DOB-year clues | severity tier |
| Fraud / social-eng | pretexts that would fool you/family/bank | employer, relatives tokens, accounts | templated pretext + tier |
| Physical | stalking/doxxing exposure | address listings, photo metadata, routines | tier + fixes only |
| Social | leakage via friends/tags | tags, shared accounts | tier |
| Surveillance | who profiles you | broker listings, trackers, face-search presence | tier |
| Professional | spear-phish / workplace pivot | employer, role, org clues | tier |
| Inference | what's *deducible* (finances, routine, relationship) | combined facts | tier, labeled "likely" |

### Attacker personas (each: goal, skill 1–5, budget_steps, patience, laziness, attention_k, tools)
1. **Opportunist** — cheapest path only, quits fast.
2. **ID-theft reseller** — wants clean, monetizable records.
3. **Targeted fraudster** — patient, deep, big-payout focus.
4. **Personal threat** (ex/stalker) — location + routine, cares nothing about credit.
5. **Insider/acquaintance** — has context you never posted publicly.
Tech tree: higher-skill personas unlock extra techniques each league round (so the loop doesn't trivially hit zero).

---

## 3. Hackathon requirements → how we satisfy them

| Requirement | Plan |
|---|---|
| Runs on Token Factory **or** AI Cloud | Runtime Token Factory calls (ULTRA/SUPER/NANO) **and** deployed on Serverless Endpoint + league on Serverless Job |
| ≥1 NVIDIA open model | Nemotron 3 Ultra / Super / Nano via Token Factory |
| Track fit (Personal AI) | always-on, persistent memory (twin + fix history), reusable skills (recon/attack/remediate/watch), tools & data user controls, private/local-first; NemoClaw/OpenShell/Hermes shell (T7) |
| Working demo URL | hosted **synthetic-persona** demo (see §13 on endpoint auth) |
| ≤3 min public YouTube video | script in §12 |
| Public repo, OSS license **visible at top (About section)** | MIT; set license in GitHub About |
| README with setup; highlight Nemotron, where Token Factory accelerated, other Nebius tools | T8 + generated from `make bench` numbers only |
| Feedback on Nebius/NVIDIA tools | keep `docs/FEEDBACK.md` notes daily (Nitu writes the final) |
| Pre-existing project explanation | everything is new this week; if you port code from older repos, declare it |
| Tavily bonus ($3k) | functional runtime Tavily calls in recon, opt-out procedure lookup, and breach watch |
| One Overall **or** one Track award, plus one Bonus | Personal AI track + Tavily bonus are compatible |

Judging (equal weight): Technological Implementation · Design · Potential Impact · Quality of Idea. Stage 1 is
pass/fail on genuine track fit.

---

## 4. Architecture

```
                         ┌─────────────────────────── React UI (Vite) ───────────────────────────┐
                         │ twin graph · attack timeline · risk radar · fixes · league chart · ledger│
                         └───────────────▲──────────────────────────────────────┬─────────────────┘
                                         │ REST + SSE (/api/events)             │
┌─────────────────────────────────────── FastAPI (apps/api) ────────────────────▼───────────────────┐
│  scheduler (APScheduler)   run store (SQLite)   demo-mode switch   serves built UI                 │
└──┬───────────┬────────────┬──────────────┬───────────────┬──────────────────┬──────────────────────┘
   │           │            │              │               │                  │
 recon      graph        attack         risk          remediate           league
 (Tavily +  (twin from   (personas +    (8 domain     (fix catalog +      (red/blue rounds,
 Nano       facts,       path search    detectors,    min hitting set,    tech tree, metrics)
 extract)   recovery     human limits)  $ + tiers)    opt-out drafts)
   │         edges)         │              │               │                  │
   └───────────┴────────────┴──────┬───────┴───────────────┴──────────────────┘
                                   │
                    core/llm  (Token Factory client: tier router, redact, cache, budget guard)
                                   │                          │
                            core/ledger (SQLite, hash-chained, every outbound call)
                                   │
        ┌──────────────────────────┴───────────────────────────┐
   Nebius Token Factory (Nemotron Ultra/Super/Nano)       Tavily API
```

**Always-on shell (Tier B, T7):** Hermes Agent running inside a NemoClaw/OpenShell sandbox with an egress
allowlist limited to {Token Factory, Tavily, the Nemesis API}. Nemesis tools are exposed to Hermes as skills.
Story: *even the privacy agent can't exfiltrate your data.* Fallback: `agent/lite/` (cron + memory file).

### Design decisions that matter
- **Deterministic engine + LLM narration.** Path search/scoring is networkx (cheap, reproducible, testable).
  LLMs do extraction (Nano), chain explanations and templated pretexts (Ultra/Super). This keeps the $50 of
  credits alive and makes league runs scale.
- **Public twin vs. private truth.** Attackers only touch the twin built from public findings. For synthetic
  personas we hold ground truth and score the twin's accuracy ("belief gap").
- **Min hitting set, not a to-do list.** Each attack path = set of fixable elements; choose min-effort set that
  hits every path (`scipy.optimize.milp` exact, greedy fallback).
- **Cache everything** (LLM + Tavily, keyed by hash) → reproducible demo, cheap reruns. Ledger still logs.
- **Budget guard:** hard stop at configured token/$ cap (`BudgetExceeded`).
- **Model routing:** ULTRA = attack-chain reasoning/remediation rationale; SUPER = persona agents, opt-out
  drafts; NANO = extraction/classification. Only confirmed model ID so far:
  `nvidia/nemotron-3-super-120b-a12b`. T1 must `GET /v1/models` and fill the rest (models get retired on a
  published schedule — keep IDs in env, never hard-coded).
- **Token Factory endpoint:** `https://api.tokenfactory.nebius.com/v1` (also seen:
  `https://api.tokenfactory.us-central1.nebius.com/v1/`). T1 verifies which one your key works on.

### Deploy on Nebius
- One Docker image (multi-stage: build UI → Python runtime serving API + static UI).
- **Serverless Endpoint** = hosted synthetic-persona demo. **Serverless Job** = league/bench runs (docs say jobs
  can be one-off or scheduled → also the weekly watch). CLI shape: `nebius ai job create --container-command …`.
- Unknowns to resolve on Day 2: container registry choice, whether an Endpoint is publicly reachable or
  auth-gated (the rules allow giving judges credentials in testing instructions), quotas.

---

## 5. Contracts (T0 writes these into `core/schemas.py` + `docs/CONTRACTS.md`; nobody else changes them)

```text
Fact          id, kind(name|address|phone|email|handle|employer|relative_token|account|breach|
              photo_meta|listing|inference), value, source_url, source_kind(broker|breach|social|
              public_record|search), confidence 0-1, found_at
Node          id, type(person|identifier|account|broker|service|asset|relative_token|event),
              label, attrs{}, public:bool
Edge          src, dst, rel(listed_on|recovers|verifies|reveals|derived_from|owns|related_to),
              effort 0-1 (attacker cost), fixable_by[fix_id]
ExposureGraph id, persona_id, nodes[], edges[], built_at
Persona       id, name, goal_domain, skill 1-5, budget_steps, patience, laziness 0-1,
              attention_k, tools[], motive
AttackStep    edge_ids[], action, success_prob, minutes, cost_usd
AttackPath    id, persona_id, domain, steps[], total_minutes, total_cost_usd, success_prob,
              loss_low, loss_high (financial only), severity 0-4, fixable_elements[fix_id],
              narrative (str|null), pretext_template (str|null, placeholders, "SIMULATION")
RiskFinding   id, domain, severity 0-4, title, evidence_node_ids[], path_ids[], loss_low?, loss_high?
Fix           id, kind(optout|alias_swap|recovery_change|freeze|privacy_setting|delete_account|
              passkey|rotate_security_qa|…), targets[], effort_minutes, paths_severed (int),
              procedure (str|null, from Tavily), draft (str|null, placeholders)
RemediationPlan  fixes[] ordered, paths_before, paths_after, method(milp|greedy), residual_notes
RoundResult   round, paths_remaining, by_persona{}, fixes_applied[], unlocked_techniques[]
LedgerEntry   id, ts, service(tokenfactory|tavily|nebius_job), purpose, bytes, payload_sha256,
              redactions, prev_hash, hash
```
**API:** `GET /api/health` · `GET /api/personas` · `POST /api/twin` {persona_id | seeds+attest} →
ExposureGraph · `POST /api/attack` {graph_id} → paths + findings · `POST /api/remediate` {graph_id} →
RemediationPlan · `POST /api/league/run` {rounds} → run_id · `GET /api/events` (SSE: progress, round results)
· `GET /api/ledger` · `POST /api/watch/run`.

---

## 6. Repo layout

```
nemesis/
  CLAUDE.md  README.md  LICENSE(MIT)  Makefile  Dockerfile  .env.example  .gitignore
  core/  schemas.py  llm/  ledger/  recon/  graph/  attack/  risk/  personas/  remediate/  league/  watch/
  apps/api/   apps/web/
  agent/      (NemoClaw + Hermes + OpenShell shell; agent/lite fallback)
  deploy/nebius/
  data/synthetic/  data/fixtures/
  docs/  CONTRACTS.md  STATUS/  design/  submission/
  scripts/  tests/
```
Make targets T0 creates: `dev`, `test`, `test-fast` (<30s, no network), `e2e` (synthetic persona, cached),
`bench` (numbers for README), `build`, `up`.

---

## 7. Skills & token strategy (you run several terminals — this is the budget)

**One-time setup (Nitu, ~15 min).** User-scope installs are shared by all terminals.
```bash
# Graphify — code → knowledge graph (code parsing is local/tree-sitter, no tokens)
pip install graphifyy && graphify install

# jCodeMunch — symbol-level code retrieval (MCP). I'm reading "code munch" as jCodeMunch.
claude mcp add -s user jcodemunch -- uvx jcodemunch-mcp
```
Inside Claude Code (Ponytail must be installed as a **plugin** — a bare SKILL.md was measured to never
self-activate; the plugin's hooks inject the ruleset):
```text
/plugin marketplace add DietrichGebert/ponytail
/plugin install ponytail@ponytail
```
Then in the **main repo during Phase 0** (so the config is committed and inherited by every worktree):
`graphify claude install` (adds a CLAUDE.md section + a PreToolUse hook that nudges toward the graph) and
`jcodemunch-mcp init` (writes MCP config + prompt policy). Keep our CLAUDE.md content first if they edit it.

**Frontend terminal only (keeps other terminals' context lean).** In the `frontend` worktree:
`npm i -g uipro-cli && uipro init --ai claude` (one source calls the package `ui-ux-pro-max-cli`; try that if
the first fails), or the plugin route `/plugin marketplace add nextlevelbuilder/ui-ux-pro-max-skill` then
`/plugin install ui-ux-pro-max@ui-ux-pro-max-skill`. Then add `.claude/skills/ui-ux-pro-max/` to
`.git/info/exclude` so it never merges into `main`. Also enable Anthropic's **frontend-design** skill in that
session (check `/plugin`). Use UI/UX Pro Max first to generate + persist a design system (T6 prompt), then
frontend-design for visual direction.

**Where the savings actually come from (ranked)**
1. **Contract-first + file ownership + STATUS files** — terminals never read each other's code. Biggest, free.
2. **jCodeMunch** — fetch one symbol instead of whole files.
3. **Graphify** — answer "how does X connect to Y" from the graph report. Update manually (`--update`), no
   git hook in worktrees (4-min autocommits would trigger constant rebuilds).
4. **Ponytail** — smaller diffs and less output.
5. **Discipline** — `/compact` at ~60%, `/clear` between milestones, terse final messages, no subagents.

**Calibrate expectations (advertised vs. independently measured)**
| Tool | Advertised | Independent note |
|---|---|---|
| Graphify | "71.5x" headline | a hands-on test measured **5–10x** on real repos |
| jCodeMunch | "95%+" on retrieval-heavy work | its own benchmark isolates **15–25%** at the tool layer |
| Ponytail | −54% code, −22% tokens | JetBrains 80-task test: **−15% code, −10% cost**; it doesn't self-activate unless installed as a plugin |

Also: Graphify's *docs/PDF* extraction uses LLM tokens — point it at code dirs only. jCodeMunch is free for
non-commercial use (fine here; read the license before using it on work projects). Model choice: a mid-tier
model for most terminals; a top model only for T3/T4 design work and integration debugging.

---

## 8. Parallel build workflow (worktrees · 4-minute commits · merge to main · cleanup)

**Rule: nobody commits on `main`** except T0's Phase-0 scaffold and the merge script.

```bash
# after Phase 0 is committed on main:
scripts/setup_worktrees.sh                   # creates ../nemesis-wt/<name> on feat/<name>
scripts/autocommit.sh --all                  # leave running in its own tab (every 240s)
cd ../nemesis-wt/<name> && claude            # one Claude Code terminal per worktree
```
- **4-minute commits.** Claude Code can't run a reliable timer, so `autocommit.sh` enforces it; agents also
  commit at every logical step. Commits blocked by the secret scan are retried next tick.
- **Merge early and often.** `scripts/merge_and_cleanup.sh <name>` = autosave → rebase on main → `make test-fast`
  → PR + merge via `gh` (or local `--no-ff` merge if no remote) → worktree stays and fast-forwards to main.
  Run it at every milestone so integration problems show up on Day 1, not Day 5.
- **Finish.** From the main repo dir: `scripts/merge_and_cleanup.sh <name> --final` merges, verifies the branch
  is fully in `main`, then deletes the worktree, local branch and remote branch.
- **Conflicts** exit with code 2 and leave the rebase in place for the agent to resolve and re-run.
- Merges are serialized with a lock, so two terminals can finish at once safely.
- Limitation: if `gh` isn't authenticated or the repo has required reviews/checks, PR merge fails — use
  `USE_PR=0` for local merges.

**Terminals** (start 1–6 on Day 0–1; others when their gate opens)
| # | Worktree | Owns | Starts |
|---|---|---|---|
| T0 | main repo (lead/integrator) | `core/schemas.py`, `docs/CONTRACTS.md`, Makefile, merges | now |
| T1 | `llm-ledger` | `core/llm/`, `core/ledger/` | after Phase 0 |
| T2 | `recon-twin` | `core/recon/`, `core/graph/`, `core/twin.py`, `data/` | after Phase 0 |
| T3 | `attack-engine` | `core/attack/`, `core/risk/`, `core/personas/` | after Phase 0 |
| T4 | `remediate-league` | `core/remediate/`, `core/league/`, `core/watch/` | after Phase 0 |
| T5 | `api-infra` | `apps/api/`, `deploy/`, `Dockerfile`, CI | after Phase 0 |
| T6 | `frontend` | `apps/web/`, `docs/design/` | after Phase 0 |
| T7 | `agent-shell` | `agent/` | Day 1, **timeboxed** |
| T8 | `docs-demo` | `README.md`, `docs/submission/` | Day 5 |

---

## 9. Timeline (EDT)

| Day | Goals | Gate |
|---|---|---|
| **Sat Oct 24 (today)** | Nitu: keys/credits/CLIs/skills. Phase 0 scaffold + contracts. Spin up T1,T2,T5,T6 | `make test-fast` green on main; worktrees exist |
| **Sun Oct 25** | T1 llm+ledger live; T2 synthetic persona + twin; T3 engine v1; T5 API skeleton; T6 UI on fixtures; first milestone merges | one synthetic persona flows twin → paths (offline) |
| **Mon Oct 26** | End-to-end on synthetic persona: twin → attack → scores → UI. T4 remediation. T7 spike starts | `make e2e` green; UI shows real data |
| **Tue Oct 27** | League loop + chart; live Tavily self-scan (local); **first Nebius deploy (Endpoint + Job)**. T7 go/no-go at noon | hosted URL works; league ran as a Job |
| **Wed Oct 28** | Tier B: watch, opt-out drafts, canary lineage. Ledger polish. Tests. Bench numbers | Tier A fully done by midnight |
| **Thu Oct 29** | **Feature freeze 12:00.** T8 README/submission. Record demo video evening | video uploaded (public YouTube) |
| **Fri Oct 30** | Final checks on a clean clone; submit **by 9:00am**; buffer for Devpost glitches | submitted |

If Tuesday's deploy isn't working, drop Tier B and fix deploy first. A working hosted demo beats extra features.

---

## 10. Prompts — copy/paste into each terminal

Every prompt below assumes `CLAUDE.md` (auto-loaded) and `docs/CONTRACTS.md`. Keep them as-is; they're short on purpose.

### Phase 0 — T0 bootstrap (main repo, run first, ~45 min)
```text
You are the lead on Nemesis. Read plan.md sections 1, 4, 5, 6 only. Then scaffold the repo on main:
1. Layout from plan.md §6 with empty packages (__init__.py), pyproject (python 3.11; fastapi, uvicorn,
   openai, tavily-python, networkx, scipy, pydantic>=2, httpx, apscheduler, pytest, ruff), .gitignore
   (.env*, !.env.example, data/private/, *.sqlite, .cache/, node_modules/, .venv/, dist/, graphify-out/cache),
   .env.example (NEBIUS_API_KEY, NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1, MODEL_ULTRA, MODEL_SUPER=
   nvidia/nemotron-3-super-120b-a12b, MODEL_NANO, TAVILY_API_KEY, NEMESIS_MAX_USD=15, NEMESIS_CACHE=1,
   NEMESIS_DEMO_MODE=1), MIT LICENSE with copyright holder "<COPYRIGHT HOLDER>", Makefile (dev, test, test-fast,
   e2e, bench, build, up — stubs that pass), minimal CI workflow.
2. core/schemas.py: pydantic models EXACTLY per plan.md §5. Write docs/CONTRACTS.md (schemas + API table +
   module ownership + who calls whom). Add tests/test_schemas.py (round-trip). Add 3 example JSON fixtures
   in data/fixtures/ (small ExposureGraph, AttackPath list, RoundResult list) so frontend and API can start mocked.
3. Copy CLAUDE.md and scripts/ from the kit (already in place) and docs/STATUS/.gitkeep.
4. Run `graphify claude install` and `jcodemunch-mcp init`; keep our CLAUDE.md content first; commit the result.
5. Run `make test-fast`, commit everything on main with clear messages, then run scripts/setup_worktrees.sh.
Be terse. Report: test status + worktree paths.
```

### T1 — `llm-ledger`
```text
Task: Token Factory client + privacy ledger. You own core/llm/ and core/ledger/. Read docs/CONTRACTS.md.
Build:
- core/llm/client.py: OpenAI SDK against NEBIUS_BASE_URL. chat(tier, messages, purpose, json_schema=None)
  with tier in {ULTRA,SUPER,NANO} -> MODEL_* env. Retries/backoff/timeouts, usage accounting, BudgetExceeded
  guard (NEMESIS_MAX_USD or token cap), on-disk cache keyed by sha256(model+messages) (NEMESIS_CACHE=0 disables).
- core/llm/redact.py: tokenize emails/phones/street addresses/ID-like strings to <EMAIL_1> etc. before any
  outbound call; reversible local map; rehydrate on return.
- core/ledger/: SQLite append-only, hash-chained LedgerEntry. record(service,purpose,payload_bytes,redactions),
  verify_chain(), summary() (counts, bytes, by-service). Both llm client and recon's Tavily wrapper call it.
- scripts/check_models.py: GET {base}/models, list nvidia/* ids, print suggested ULTRA/SUPER/NANO mapping
  (Ultra = largest Nemotron 3, Super = nemotron-3-super-120b-a12b, Nano = smallest). Run it live, update
  .env.example model ids, and note the verified base URL in docs/STATUS/llm-ledger.md.
- core/llm/smoke.py: one SUPER + one NANO call, prints replies, adds 2 ledger rows.
Tests (no network, httpx.MockTransport): retry, cache hit, budget guard, redact/rehydrate, tamper detection.
Done when: make test-fast green, smoke works live, milestone-merged. Merge early (after the client works) so
others can import it.
```

### T2 — `recon-twin`
```text
Task: recon + exposure graph + synthetic personas. You own core/recon/, core/graph/, core/twin.py, data/.
Read docs/CONTRACTS.md. Build:
- data/synthetic/: generator for N clearly fictional personas with ground-truth JSON and a simulated "public
  footprint" (broker listing text, breach mention, old profile, photo metadata) — reserved values only
  (example.com, 555-01xx, "100 Example Street"). Ship 3 personas incl. 'pat-example-01'. Offline fixtures
  in data/fixtures/ mimic Tavily result shape.
- core/recon/tavily_client.py: wrapper over tavily-python: disk cache, ledger.record() on every call, query
  budget cap, live mode requires attest=True AND is blocked when NEMESIS_DEMO_MODE=1 (hosted demo = synthetic only).
  Seeds = name/city/email-alias/handles of the USER only; never search third parties.
- core/recon/extract.py: NANO structured extraction (json_schema) of Facts from snippets; dedupe; confidence.
  Relatives become opaque relative_token facts; never searched.
- core/graph/build.py: Facts -> ExposureGraph with recovery-dependency edges by rules (email recovers accounts,
  phone verifies SMS 2FA, listing reveals address ...). effort weights per edge; fixable_by ids from
  core/remediate catalog ids listed in CONTRACTS (agree with T4 via STATUS file).
- core/twin.py: build_twin(persona_id|seeds,attest) -> ExposureGraph; twin_gap(truth, twin) -> belief-gap score.
Tests: offline fixture -> expected nodes/edges; attest enforcement; demo-mode block. Use the llm client from
main once T1 merges; until then mock it behind the same signature.
Done: make test-fast green; merged; STATUS updated.
```

### T3 — `attack-engine`
```text
Task: human-like attackers + risk scoring. You own core/attack/, core/risk/, core/personas/. Read
docs/CONTRACTS.md. Build:
- core/personas/*.yaml: the 5 personas in plan.md §2 (goal_domain, skill, budget_steps, patience, laziness,
  attention_k, tools, motive) + a tech tree (techniques unlocked by league round).
- core/attack/engine.py: deterministic, seeded path search over ExposureGraph (networkx) from public nodes to
  goal assets. Human limits: laziness = cost-weighted cheapest-first; attention_k = only top-k visible leads;
  patience = quit after N dead ends; budget_steps cap; imperfect inference = sometimes wrong-but-plausible
  belief logged. Output AttackPath with minutes/cost/success_prob. fixable_elements must be filled.
- core/risk/: detectors for all 8 domains (financial, identity, fraud, physical, social, surveillance,
  professional, inference) -> RiskFinding. loss_model.yaml for illustrative $ ranges (label: not financial advice).
  Physical-risk output is severity + fixes only.
- LLM use is narrow: ULTRA writes path narratives; SUPER writes pretext TEMPLATES (placeholders, 'SIMULATION'
  watermark, never sent). Filled examples only for synthetic personas. Cache all calls.
Tests: on 'pat-example-01' at least 3 personas find a path; opportunist quits on a hardened graph; same seed =
same output; every path has fixable_elements.
Done: make test-fast green; milestone-merge after engine v1 (offline, no LLM) so T4/T5/T6 can integrate.
```

### T4 — `remediate-league`
```text
Task: remediation + red/blue league + watch. You own core/remediate/, core/league/, core/watch/. Read
docs/CONTRACTS.md. Build:
- core/remediate/catalog.yaml: ~20 fix kinds (opt-out broker listing, alias swap, recovery-method change, hardware
  key/passkey, credit freeze, rotate security Q&A, delete old account, privacy settings ...) with effort_minutes and
  what they remove/alter in the graph. Publish fix ids in docs/STATUS/remediate-league.md for T2/T3.
- core/remediate/plan.py: min-effort hitting set over AttackPaths (scipy.optimize.milp exact; greedy fallback).
  Return RemediationPlan with paths_before/after and 'paths_severed' per fix.
- core/remediate/apply.py: apply a fix to the graph (remove/alter nodes/edges).
- core/remediate/optout.py: for each broker, Tavily-lookup the CURRENT opt-out procedure (cached, ledgered), then
  SUPER drafts the request with placeholders. Drafts only; never submit.
- core/league/: rounds loop: red replans on current graph -> blue applies top fixes under an effort budget ->
  red unlocks techniques (tech tree) -> record RoundResult. Emits progress events for SSE. CLI entry for Nebius
  Jobs: python -m core.league.job --personas N --rounds R --out results.json (no secrets in output).
- core/watch/: re-scan diff + breach-news check via Tavily (public news only); writes findings.
- Tier B: canary alias + lineage map. Tier C: bandit over strategy templates across N synthetic personas.
Tests: hitting set optimal on a small known instance; league paths_remaining is non-increasing except tech unlocks;
residual risk is reported, never forced to zero.
Done: make test-fast green; merged; STATUS updated.
```

### T5 — `api-infra`
```text
Task: FastAPI + deploy. You own apps/api/, deploy/, Dockerfile, CI. Read docs/CONTRACTS.md. Build:
- apps/api: endpoints exactly per CONTRACTS; SSE /api/events; run store (SQLite); APScheduler for watch;
  NEMESIS_DEMO_MODE=1 => synthetic personas only, live scans refused with a clear error; serves built UI.
  Until core modules merge, import with graceful fallbacks to data/fixtures so the UI can integrate Day 1.
- Dockerfile multi-stage (build apps/web -> Python runtime serving API+static). Non-root user, no secrets baked in.
- deploy/nebius/: scripts + README with the EXACT commands that worked: build/push image, create Serverless
  Endpoint, create Serverless Job (league), scheduled Job (watch). Docs: https://docs.nebius.com/llms.txt.
  Figure out and record: registry to use, whether the Endpoint is public or auth-gated, quotas. If anything
  needs Nitu's account/billing action, write it at the top of deploy/README.md as NITU TODO.
- CI: lint + make test-fast. Make targets dev/up/e2e wired.
Milestone: hosted Endpoint serving the synthetic demo by end of Tue Oct 27. Merge API skeleton in the first hours.
```

### T6 — `frontend`
```text
Task: the UI. You own apps/web/ and docs/design/. Read docs/CONTRACTS.md; develop against data/fixtures/ first.
Design process (token-lean): 1) run the UI/UX Pro Max design-system search for "personal security dashboard
cybersecurity trust" with --persist, copy the result to docs/design/MASTER.md and read ONLY that afterwards;
2) use the frontend-design skill for a distinctive, non-template visual direction. Don't reload both repeatedly.
Build (React+Vite+TS+Tailwind; Cytoscape.js or React Flow for the graph; Recharts for radar/league), desktop-first
1440px for the demo video, responsive to phone width:
- Twin graph (nodes colored by type, public vs private, attack-path highlight on hover)
- Attacker panel: five personas, who got in / how fast / who quit, animated step timeline
- Risk radar by domain (before vs after) + dollar-range vs severity-tier cards
- Fix list showing 'paths severed' per fix + one-click "apply & re-attack"
- League chart: attack paths remaining per round (the hero visual)
- Ledger drawer: itemized outbound calls + chain-verified badge + honest copy ("minimized and itemized")
- Pretext viewer with a loud SIMULATION watermark; demo-mode banner "synthetic persona"
- Loading/empty/error states; keyboard + contrast accessible. No credentials fields anywhere.
Done: Lighthouse accessibility >= 90, runs on fixtures offline, then wired to the API; merged.
```

### T7 — `agent-shell` (TIMEBOXED: 6h hard; go/no-go Tue noon)
```text
Task: always-on personal-agent shell using NVIDIA NemoClaw + OpenShell + Hermes Agent. You own agent/.
Read https://docs.nvidia.com/nemoclaw/ (use /llms.txt) and the NVIDIA blog "Deploy Self-Evolving Agents ...
Hermes Agent and NVIDIA NemoClaw". Goal: Hermes runs inside an OpenShell sandbox with an egress allowlist =
{Token Factory host, Tavily host, the Nemesis API}; Nemesis exposed to Hermes as skills (twin, attack, remediate,
watch) over HTTP; persistent memory/skills snapshot. Verify early: can inference route to Nebius Token Factory
(OpenAI-compatible)? Needs Docker; record exact install steps. Deliver agent/README.md, policy YAML, seed
SOUL/MEMORY, and a screen-recordable demo (agent tries a non-allowlisted host -> 403).
FALLBACK if sandbox + one real Nemesis tool call isn't working by Tue noon: build agent/lite/ (cron loop +
memory file + same skill interface), document why, and stop. Don't sink more time into it.
```

### T8 — `docs-demo` (Day 5)
```text
Task: submission docs. You own README.md and docs/submission/. Produce: README (what/why, quickstart, architecture
diagram, how Nemotron + Token Factory + Tavily + Nebius Serverless are used, guardrails/ethics, limitations,
license badge), docs/submission/DESCRIPTION.md (what we built, why, how it works), TOOLS.md (Token Factory
acceleration points, other Nebius tools), DEMO_SCRIPT.md (<=3:00 shot list from plan.md §12), FEEDBACK_DRAFT.md
(structured; mark every line Nitu must personally confirm), CHECKLIST.md. RULE: every number/claim must come from
`make bench` or a committed artifact — never invent metrics. Verify setup instructions by following them on a
fresh clone. Done: merged and linted for broken links.
```

### T0 — daily integrator prompt (paste each morning in the main-repo terminal)
```text
Integration check. 1) git worktree list; read each docs/STATUS/*.md (not the code). 2) On main: make test-fast and
make e2e; fix or assign failures. 3) Approve/apply contract-change requests (only you edit core/schemas.py and
docs/CONTRACTS.md; commit on a short-lived branch merged via the script). 4) Report: what merged, what's blocked,
top risk to the Fri 9am submit. Be terse. When a terminal says it's done, run scripts/merge_and_cleanup.sh <name> --final.
```

---

## 11. THIS IS WHAT THE DEVELOPER, AKA NITU, NEEDS TO DO HIMSELF

1. **Accounts/keys (today, first):** claim Token Factory credits via the promo form with code
   `NEBIUS-DEVPOST-GLOBAL26` ($25), join the free **Nebius Builders Program** (+$25 and Tavily/Academy credits),
   create a Token Factory API key and a Tavily key (`tvly-…`). Put them only in `.env` — never in chat or git.
2. **Tooling:** latest Claude Code, Node, Python 3.11+, `uv`, Docker, `gh auth login`, the Nebius CLI (`nebius`),
   git. Create the **public GitHub repo** (MIT) and `git remote add origin …`; set the license in the repo About.
3. **Install the skills** from §7 (Graphify, jCodeMunch, Ponytail user-scope; UI/UX Pro Max in the frontend worktree).
4. **Fill the LICENSE** copyright holder; decide how you want your name shown in the repo.
5. **Confirm Nebius AI Cloud works for you:** create a throwaway Job and Endpoint on Day 1. If billing/quota blocks you,
   ask in the Nebius Discord immediately. Check whether Endpoints can be public (see §13).
6. **Devpost:** register, start the project, pick **Personal AI**, paste submission text, add video + repo + demo URLs.
   Only you can submit.
7. **Privacy call:** decide whether to show a *live self-scan* in the video. Recommend: synthetic persona on screen;
   if you show your own scan, blur address/phone/relatives.
8. **Record + upload the 3-minute demo** to public YouTube (no copyrighted music, no third-party trademarks).
9. **Write the feedback section yourself** (real experience with Token Factory, Nemotron, NemoClaw…). Keep notes in
   `docs/FEEDBACK.md` as you go; T8 only drafts a skeleton. Also add a pre-existing-project note if you port any code
   from your earlier attacker/defender RL work.
10. **Judgment calls:** approve scope cuts Tuesday night; call the **feature freeze Thursday noon**; do the final clean-clone
    test and click Submit Friday by 9am.
11. **jCodeMunch license:** free for non-commercial; fine for the hackathon, read it before using on other work.

---

## 12. Demo (≤ 3:00) and submission checklist

**Shot list**
- 0:00 Hook (15s): "Here's an attack on a normal person built entirely from public data." Show the headline stat.
- 0:15 Twin builds live (30s): graph fills in; call out Tavily + Nano extraction.
- 0:45 Five attackers (45s): who got in in 40 minutes, who quit; open one pretext (SIMULATION watermark).
- 1:30 Risk radar + dollar/severity cards (20s).
- 1:50 Fix: min-cut list — "6 fixes, not 60" → apply & re-attack (30s); **league chart falling** (hero shot).
- 2:20 Ledger (20s): itemized outbound calls, chain verified. Say "minimized and itemized".
- 2:40 Always-on (15s): Hermes-in-OpenShell 403 on a blocked host (if T7 shipped) or the scheduled watch diff.
- 2:55 Close (5s): "Nemesis. Attack yourself before someone else does."
Must show: Token Factory + Nemotron in use, Nebius deploy. Narrate where Token Factory made it fast/cheap.

**Submission checklist**
- [ ] Track = Personal AI · [ ] description (what/why/how) · [ ] demo URL works on a clean browser
- [ ] public YouTube ≤3:00 · [ ] public repo, MIT visible in About, README with setup + Nemotron/Token Factory/Nebius/Tavily notes
- [ ] feedback section filled · [ ] pre-existing note (if any) · [ ] runtime Token Factory + Tavily calls verified in the ledger
- [ ] no secrets/real personal data in the repo (`git log -p | grep -E 'tvly-|AKIA'`) · [ ] clean-clone run-through

---

## 13. Risks & things to verify (I could not confirm these from the docs I read)

| Item | Why it matters | Action |
|---|---|---|
| Nemotron **Ultra/Nano model IDs** | only the Super ID was confirmed; models get retired on a schedule | T1 `check_models.py` first thing |
| **Endpoint public vs auth-gated** | judges need access; rules allow credentials in testing instructions | T5 resolves Day 2; fallback = credentials in instructions |
| Token Factory **fine-tuning availability/terms** | Tier C claim | check docs before promising |
| **NemoClaw → Token Factory routing**, Docker/OS needs | T7 feasibility | T7 verifies first; Tue noon gate |
| Credits ($25+$25) vs. LLM spend | league could burn them | cache + deterministic engine + budget guard |
| Tavily coverage of brokers | discovery is partial; many sites block bots | say so in README; demo on synthetic fixtures |
| Ledger honesty | live queries contain identifiers | copy says "minimized and itemized" |
| `gh` PR path untested | merge flow | try `merge_and_cleanup.sh` once on Day 0 with a trivial branch |
| Graphify/jCodeMunch/Ponytail gains | claims vs measured differ | don't budget on advertised numbers |
| Misuse of a "red team yourself" tool | reputation + judging | self-only, hosted = synthetic only, templates, no third parties (see CLAUDE.md) |

---

## Sources
- Hackathon: https://nebiusglobalaihackathon.devpost.com/ · /resources · /rules
- Token Factory API (OpenAI-compatible; Nemotron models; fine-tuning mentioned): https://docs.tokenfactory.nebius.com/api-reference/introduction · https://nebius.com/services/token-factory/nemotron
- Nebius Serverless AI (endpoints/jobs): https://docs.nebius.com/serverless · https://docs.nebius.com/serverless/jobs/manage.md
- NVIDIA NemoClaw docs: https://docs.nvidia.com/nemoclaw/ · Hermes + NemoClaw blog: https://developer.nvidia.com/blog/deploy-self-evolving-agents-for-faster-more-secure-research-with-a-hermes-agent-and-nvidia-nemoclaw/
- Tavily Python SDK: https://docs.tavily.com/sdk/python/quick-start.md
- Graphify: https://github.com/Nectrion/graphify · hands-on test: https://www.mejba.me/graphify-knowledge-graph-codebase-claude-code
- jCodeMunch: https://github.com/jgravelle/jcodemunch-mcp · https://pypi.org/project/jcodemunch-mcp/
- Ponytail: https://github.com/DietrichGebert/ponytail · JetBrains test: https://blog.jetbrains.com/ai/2026/07/ponytail-skill-claude-tested/
- UI/UX Pro Max: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
