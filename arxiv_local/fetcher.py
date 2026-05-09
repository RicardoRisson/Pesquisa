# arxiv/arxiv_fetcher.py
import arxiv
from tqdm import tqdm

MAX_ARXIV = 20000

def fetch_arxiv(query: str, checkpoint: dict) -> list[dict]:
    client = arxiv.Client(delay_seconds=3.0)
    search = arxiv.Search(
        query=query,
        max_results=MAX_ARXIV,
        sort_by=arxiv.SortCriterion.Relevance,
    )

    results = []

    for result in tqdm(client.results(search), desc=f"[arXiv] {query}", unit="art"):
        arxiv_id = result.entry_id.split("/")[-1]  # e.g. "2401.12345v1"

        if arxiv_id in checkpoint["done_ids"]:
            continue

        abstract = result.summary.strip()
        if not abstract:
            continue

        results.append({
            "source":    "arxiv",
            "query":     query,
            "id":        arxiv_id,
            "url":       result.entry_id,
            "title":     result.title.strip(),
            "abstracts": {"english": abstract},  # arXiv is english-only
        })

    return results