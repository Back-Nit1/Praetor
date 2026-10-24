# llm-ledger (T1)
Done (M1): append-only hash-chained SQLite ledger; redaction/rehydration; tiered Token Factory client with retry, cache, budget, structured output, and per-attempt ledger records.
Done (M2): scripts/check_models.py lists live NVIDIA IDs from verbose endpoint metadata and recommends ULTRA/SUPER/NANO without embedded candidate IDs.
Done (M2): scripts/smoke_models.py makes one structured NANO and one SUPER call; metadata-only report shows each call's ledger status, timing, usage, and sanitized errors.
Tests: test-fast 71 passed / 2 network deselected; lint passed. Live tests skip without required configuration.
Notes: no prompt text, response text, prompt identifier, or key is emitted by validation reports. No model defaults changed without live evidence.
In progress: milestone merge blocked by unrelated uncommitted changes in the main worktree.
Next: run check_models then smoke when credentials and selected MODEL_NANO/MODEL_SUPER are configured.
Contract requests: none.
Blockers: NEBIUS_API_KEY is absent, so live behavior remains unvalidated; merge awaits owner resolution of the dirty main worktree.
