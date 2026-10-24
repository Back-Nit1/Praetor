# recon-twin (T2)
Done (M1, offline): 3 synthetic personas (pat-example-01, robin-sample-02, casey-placeholder-03) in data/synthetic/<id>/{truth,public}.json;
core/recon/{facts,synthetic}.py (normalize+dedup, relative tokenizing, loaders); core/graph/build.py; core/twin.py (build_twin, twin_gap).
Pat graph == data/fixtures/exposure_graph.json (tested). 29 tests green, lint clean.
In progress: —
Next: live recon (Tavily search + NANO extract -> Facts) behind attest; wire into build_twin seeds path.
Contract requests:
- build_graph gains optional `persona_id="self"` kwarg (contract: `build_graph(facts)`); backwards compatible.
- build_twin errors for T5 to map: PermissionError (demo mode + seeds -> 403), ValueError (no attest / bad persona -> 4xx), NotImplementedError until live recon lands.
- T5 `GET /api/personas` can use `core.recon.synthetic.list_personas()` -> [{id, name}].
- Node.attrs carries `kind`/`key` (normalized) on fact-derived nodes; twin_gap relies on it.
Blockers: main has untracked 0.md, which blocks merge_and_cleanup.sh ("main has uncommitted changes").
