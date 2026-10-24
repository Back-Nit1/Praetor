# llm-ledger (T1)
Done (M1, offline): core/ledger (sqlite append-only + triggers, sha256 chain, record/entries/summary/verify_chain, path via
NEMESIS_LEDGER_DB, default data/private/ledger.sqlite); core/llm/redact.py (EMAIL/PHONE/ADDRESS/ID, stable <KIND_n>, rehydrate);
core/llm/client.py (Client(sdk) DI, chat(), tier env MODEL_ULTRA/SUPER/NANO, retry+backoff, json_schema, disk cache, ledger, budget).
Tests: tests/test_llm_ledger.py (20 pass in test-fast, no network).
Notes: ledger row per ATTEMPT (retries included), none for cache hits. Cache holds placeholder-form output only. redactions = unique
values redacted. Budget: NEMESIS_MAX_TOKENS ceiling (default 2M) always; NEMESIS_MAX_USD only for tiers with
PRICE_<TIER>_IN_PER_MTOK/_OUT_PER_MTOK set. Usage is per-process (in-memory). Names are NOT redacted (regex only).
In progress: —
Next: live smoke call + scripts/check_models.py (verify model ids, json_schema support on Token Factory), then name handling.
Contract requests: none.
Blockers: need NEBIUS_API_KEY + MODEL_ULTRA/MODEL_NANO ids for live work.
