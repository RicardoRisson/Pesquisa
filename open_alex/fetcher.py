# openalex/openalex_fetcher.py
import time
import requests
from tqdm import tqdm
from dotenv import load_dotenv
import os

load_dotenv()

BASE_URL    = "https://api.openalex.org/works"
PER_PAGE    = 200
MAX_RESULTS = 10000
DELAY       = 1.0  # segundos entre páginas — respeita o rate limit sem chave

def make_headers() -> dict:
    email = os.getenv("ENTREZ_EMAIL", "")
    # OpenAlex pede o email no User-Agent para tier "polite" (100k req/dia)
    return {"User-Agent": f"pesquisa/1.0 (mailto:{email})"}


def fetch_page(query: str, cursor: str = "*") -> dict | None:
    params = {
        "search":   query,
        "per_page": PER_PAGE,
        "cursor":   cursor,
        "filter":   "has_abstract:true",
        "select":   "id,doi,title,language,abstract_inverted_index,primary_location",
    }
    try:
        resp = requests.get(BASE_URL, params=params, headers=make_headers(), timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return None


def reconstruct_abstract(inverted_index: dict | None) -> str:
    """OpenAlex armazena o abstract como índice invertido {palavra: [posições]}."""
    if not inverted_index:
        return ""
    # reconstrói a ordem original das palavras
    positions = []
    for word, pos_list in inverted_index.items():
        for pos in pos_list:
            positions.append((pos, word))
    return " ".join(word for _, word in sorted(positions))


def fetch_openalex(query: str, checkpoint: dict) -> list[dict]:
    results = []
    cursor  = "*"
    total_fetched = 0

    with tqdm(desc=f"[OpenAlex] {query}", unit="art") as pbar:
        while total_fetched < MAX_RESULTS:
            data = fetch_page(query, cursor)

            if not data:
                break

            works = data.get("results", [])
            if not works:
                break

            for work in works:
                openalex_id = work.get("id", "").replace("https://openalex.org/", "")

                if not openalex_id or openalex_id in checkpoint["done_ids"]:
                    continue

                abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
                if not abstract:
                    continue

                lang = work.get("language") or "unknown"

                results.append({
                    "source":   "openalex",
                    "query":    query,
                    "id":       openalex_id,
                    "doi":      work.get("doi", ""),
                    "title":    work.get("title", "").strip(),
                    "abstracts": {lang: abstract},
                })

                pbar.update(1)

            total_fetched += len(works)

            # cursor-based pagination — sem cursor próximo significa última página
            next_cursor = data.get("meta", {}).get("next_cursor")
            if not next_cursor:
                break

            cursor = next_cursor
            time.sleep(DELAY)

    return results