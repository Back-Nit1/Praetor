"""Live recon: the user's own seeds -> Tavily -> NANO extraction -> Facts. Local CLI/Docker only."""
from core.recon.extract import extract
from core.recon.search import Searcher, check_live, queries_for
from core.schemas import Fact, Seeds


def live_facts(seeds: Seeds, attest: bool, *, searcher: Searcher | None = None) -> list[Fact]:
    check_live(attest)  # before anything is generated or sent
    searcher = searcher or Searcher(attest)
    snippets = {r["url"]: r for q in queries_for(seeds) for r in searcher.search(q) if r.get("url")}  # dedup by URL
    return extract(list(snippets.values()))
