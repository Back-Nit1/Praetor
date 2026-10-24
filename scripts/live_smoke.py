"""Optional live smoke: your own seeds -> Tavily -> NANO -> Facts. Spends real quota; never run in CI.

    .venv/bin/python scripts/live_smoke.py --attest --name "Your Name" [--city C] [--email E ...] [--handle H ...]

Exits 2 with a list of what is missing (keys, MODEL_NANO, demo mode on, no --attest) before any request is made.
"""
import argparse
import os
import sys
from collections import Counter

from dotenv import load_dotenv


def main() -> int:
    load_dotenv()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--attest", action="store_true", help="these seeds are about me (self-only)")
    ap.add_argument("--name", required=True)
    ap.add_argument("--city")
    ap.add_argument("--email", action="append", default=[])
    ap.add_argument("--handle", action="append", default=[])
    ap.add_argument("--max-queries", type=int, default=4)
    a = ap.parse_args()

    from core.recon.search import demo_mode  # after load_dotenv so .env's demo flag is seen

    missing = [k for k in ("TAVILY_API_KEY", "NEBIUS_API_KEY", "MODEL_NANO") if not os.environ.get(k)]
    problems = [f"missing {k} in .env" for k in missing]
    if demo_mode():
        problems.append("demo mode is on: set PRAETOR_DEMO_MODE=0 (or NEMESIS_DEMO_MODE=0) in .env")
    if not a.attest:
        problems.append("pass --attest to confirm the seeds are your own")
    if problems:
        print("live smoke not run:\n  " + "\n  ".join(problems), file=sys.stderr)
        return 2

    from core import ledger
    from core.recon.live import live_facts
    from core.recon.search import Searcher
    from core.schemas import Seeds

    seeds = Seeds(name=a.name, city=a.city, emails=a.email, handles=a.handle)
    facts = live_facts(seeds, True, searcher=Searcher(True, max_queries=a.max_queries))
    print(f"{len(facts)} facts:", dict(Counter(f.kind for f in facts)))
    print("ledger (minimized and itemized, not 'nothing left your machine'):", ledger.summary()["by_service"])
    print("chain verified:", ledger.verify_chain())
    return 0


if __name__ == "__main__":
    sys.exit(main())
