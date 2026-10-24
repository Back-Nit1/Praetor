# recon-twin (T2)
Done M1 (offline): 3 synthetic personas, core/recon/{facts,synthetic}, core/graph/build, core/twin (build_twin, twin_gap).
Done M2 (fakes-tested, 92 tests green, lint clean): core/recon/search.py (Searcher: guard attest/self/demo-off/no relative tokens,
disk cache, query budget, timeout+retry, 1 ledger entry per request), extract.py (NANO json_schema -> Facts; grounded, schema-validated,
relatives only as opaque tokens, malformed output dropped), live.py (live_facts(seeds, attest)), scripts/live_smoke.py (`make smoke-live`).
Live smoke NOT run: no .env with TAVILY_API_KEY / NEBIUS_API_KEY / MODEL_NANO anywhere.
Next: wire live_facts into build_twin seeds path (replaces NotImplementedError; needs test update + API mapping of RuntimeError for missing keys).
Contract requests:
- `search(query, attest)` is now `Searcher(attest).search(query)`; `extract(snippets) -> list[Fact]` as contracted. Queries come only from `queries_for(Seeds)`.
- T4 may reuse Searcher for opt-out lookups (same guard applies).
- Env prefix: new code reads PRAETOR_* then NEMESIS_*; demo mode fails closed on either.
Blockers: main has uncommitted PRAETOR rename (not mine) -> merge_and_cleanup.sh refuses until lead commits it.
