# lead (T0)
Done: Phase 0 scaffold; gate 1 harness: `make e2e` -> scripts/e2e.py (build_twin->load_personas->run_attacks->score, schema round-trip, determinism, fixture-fallback guard). Contract decided: build_graph(facts, persona_id="self"), build_twin error map (CONTRACTS.md).
Gate 1: RED. main lacks core.twin (recon-twin) and core/ledger+llm (llm-ledger). Trial merge of recon-twin onto main: e2e OK, deterministic across PYTHONHASHSEED (sha256 61bcce50...), 3 paths / 7 findings.
Next: after recon-twin + llm-ledger merge, rerun make test-fast lint e2e; flip gate green.
Requests sent: recon-twin and llm-ledger owners run `scripts/merge_and_cleanup.sh <name>` (0.md/2.md blocker removed via .gitignore). api-infra: map PermissionError->403, ValueError->4xx, NotImplementedError->501, use list_personas() when switching adapter to core.
Blockers: LICENSE holder placeholder; no git remote.
