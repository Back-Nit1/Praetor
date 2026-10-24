# Praetor — read this first (every terminal, every session)

## The problem
Our lives are leaking into the open web. Data brokers sell addresses, phones, relatives and
employers. Breaches spill emails and passwords. Photos, posts and public records reveal where
we live, who we know and how our accounts recover. Attackers chain these small leaks into big
harm: account takeover and fraud (financial), identity theft, stalking (physical), social
engineering of us and our families, tracking and profiling (surveillance).

Existing tools say "we removed 12 listings." Nobody shows you the attack you would actually face,
or the shortest path to being safe.

## What Praetor is
An always-on **personal security agent** (Personal AI track).
1. Builds a **public digital twin** of one person — only what a stranger could find online.
2. Runs **distinct simulated attackers** (opportunist, ID-theft reseller, targeted fraudster,
   personal threat, insider) against the twin, with human limits: laziness, bounded attention,
   dead ends, quit thresholds.
3. Scores damage by domain: financial, identity, fraud, physical, social, surveillance,
   professional, inference. Financial gets illustrative $ ranges; others get severity tiers.
4. Computes the **smallest set of fixes** that severs the most attack paths (min hitting set).
5. Applies fixes to the twin, re-attacks, repeats until attackers fail (red/blue league).
6. Keeps watching: scheduled re-scans, breach-triggered re-runs, a data-flow **ledger** of every
   byte that leaves the machine.

## Hackathon (why we make these choices)
Nebius x NVIDIA Global AI Hackathon, Personal AI track. **Deadline Fri Oct 30 2026, 1:00pm EDT.**
Judged equally on Technological Implementation, Design, Potential Impact, Quality of the Idea.
Hard requirements: runtime calls to **Nebius Token Factory** (or run on Nebius AI Cloud), at least
one **NVIDIA open model (Nemotron)**, public repo + MIT license + README, <=3 min public YouTube
demo, live demo URL. A functional runtime **Tavily** call also qualifies for a $3k bonus.

## Stack
Python 3.11 + FastAPI + networkx + pydantic · OpenAI SDK pointed at Token Factory
(OpenAI-compatible) · tavily-python · SQLite · React + Vite + TypeScript + Tailwind.
Model tiers (env-configured): ULTRA = deep reasoning, SUPER = default agents, NANO = bulk extraction.
Deploy: one Docker image on Nebius Serverless (Endpoint for API+UI, Jobs for league/watch runs).

## Read order (stop as soon as you have what you need)
1. This file. 2. `docs/CONTRACTS.md` (schemas + API — the only thing you may assume about other
modules). 3. `docs/STATUS/<your-name>.md` if resuming. Do NOT read `plan.md` unless you are the lead.

## Guardrails — non-negotiable (this is a defensive tool)
- **Self-only.** Live scans need `attest=True` and run only in the local CLI/Docker. The hosted demo
  accepts **synthetic personas only**. No code path takes a third party's name as a target.
- **Third parties are opaque.** Relatives/associates appear only as tokens (`relative_1`) from the
  user's own listings. Never search for or store details about them.
- **Synthetic data uses reserved values:** `example.com/.org`, phones `555-0100`–`555-0199`,
  addresses like "100 Example Street". Clearly fictional names. Never real people.
- **Pretext/scam outputs are templates** with placeholders, watermarked `SIMULATION`, never sent
  anywhere. Filled-in examples exist only for synthetic personas.
- **Physical-risk output = severity + fixes.** Never a "how to find/locate/time them" playbook.
- **No credentials, ever.** No password, SSN, card or ID-number fields in any schema or UI.
- **No ToS-violating collection:** no logins, no CAPTCHA bypass, no scraping behind forms. Tavily is
  the discovery layer. Opt-outs are **drafted** for the user to submit, not auto-submitted.
- **Minimize + itemize outbound data.** Redact/tokenize identifiers before any Token Factory call;
  log every outbound call to the ledger. Be honest: say "minimized and itemized", never "nothing
  left your machine" in live mode (search queries contain identifiers).
- Financial numbers are illustrative estimates — label them "not financial advice".
- Never commit `.env`, keys, real personal data, or `data/private/`.

## Token discipline (many terminals share one budget)
- Code lookup: use **jCodeMunch** (symbol search/outline) before reading whole files.
- Orientation: read `graphify-out/GRAPH_REPORT.md` before Grep/Glob sweeps. Build it code-only:
  `/graphify ./core ./apps --update`. Do NOT install the graphify git hook in worktrees (our 4-minute
  autocommits would rebuild constantly).
- **Ponytail** is on: write the least code that works; keep validation, security, error handling.
- Stay inside your owned paths. Need something from another module? Use its contract; if the
  contract is wrong, write the request in `docs/STATUS/<you>.md` under `## Contract requests`.
- Don't re-read a file after editing it. Don't narrate. Final message <= 5 lines.
- At ~60% context run `/compact`. Between milestones `/clear` — state lives in git + your STATUS file.
- No subagents unless the prompt says so.

## STATUS file (resume cheaply)
Keep `docs/STATUS/<name>.md` <= 15 lines: Done / In progress / Next / Contract requests / Blockers.
Update at each milestone commit.

## Git rules
- You work in your own worktree on branch `feat/<name>`. **Never edit or commit on `main`.**
- `scripts/autocommit.sh --all` commits every 4 minutes for you. Also commit yourself at every
  logical step (`feat(core/attack): ...`). Never leave work uncommitted for more than 4 minutes.
- Milestone merge (worktree stays, ~every 2-3 hours or when a contract-visible piece works):
  `scripts/merge_and_cleanup.sh <name>`
- Final merge (deletes worktree + branch; run from the main repo dir, not inside the worktree):
  `cd "$(git worktree list --porcelain | sed -n '1s/^worktree //p')" && scripts/merge_and_cleanup.sh <name> --final`
- Rebase conflict (exit 2)? Resolve in your worktree, `git rebase --continue`, re-run. Never force-push
  `main`, never `--no-verify`, never amend merged commits.
- Secret scan blocks a commit? Move the value to `.env` and retry.

## Definition of done (any task)
`make test-fast` passes · your STATUS file updated · merged to main via the script · no secrets ·
one-line summary to the user.
