# Pesquisa — Abstract Scraper

A research data pipeline that collects, deduplicates, and classifies scientific abstracts from **PubMed**, **ArXiV** and **SciELO** across multiple languages.

---

## Overview

The pipeline runs queries against two sources in parallel, extracts multilingual abstracts, deduplicates by article ID, and normalizes language labels into a clean JSONL dataset.

```
.env: queries = ... → fetch.py ─┬─ pubmed.fetcher.py  → PubMed API (Entrez)
                            └─ scielo.fetcher.py  → SciELO (Playwright + aiohttp)
                                      ↓
                               data/dataset_clean.jsonl
                                      ↓
                            tools/classify.py
                                      ↓
                        data/dataset_clean.jsonl + data/report.json
```

---

## Project Structure

```
.
├── data/
│   ├── dataset_raw.jsonl     # raw collected abstracts
│   ├── dataset_clean.jsonl   # deduplicated and classified
│   └── report.json           # run statistics
├── pubmed/
│   ├── fetcher.py            # Entrez batch fetcher
│   └── utils.py              # abstract extraction, language normalization
├── arxiv_local/
│   ├── fetcher.py            # Arxiv API batch fetcher
├── scielo/
│   ├── fetcher.py            # Playwright + aiohttp scraper
│   ├── block_guard.py        # retry logic, block detection, headers
│   ├── cookie.py             # Playwright-based cookie refresh
│   └── utils.py              # abstract splitting, PID extraction
├── shared/
│   └── langs.py              # unified language code/name mappings
├── tools/
│   └── classify.py           # dedup + language classification
├── fetch.py                  # fetch — runs chosen fetchers in parallel
├── classify.py               # classify — classify data by queries
├── to_csv.py                 # convert selected file to csv
├── utils.py                  # checkpoint, JSONL save, hashing
├── .env                      # secrets and config (never committed)
├── requirements.txt          # all needed libs
└── .gitignore
```

---

## Setup

**Requirements**: Python 3.11+

```bash
pip install -r requirements.txt
```

**Configure `.env`:**

```env
ENTREZ_EMAIL=your@email.com
ENTREZ_API_KEY=your_ncbi_key        # optional — raises rate limit from 3 to 10 req/s
SCIELO_COOKIE=                      # auto-populated on first run
QUERIES=renal physiology,...        # example, populate with your queries
```

---

## Usage

**Run the full pipeline:**

```bash
python fetch.py
```

Fetches all queries from both sources in parallel, saves results to `data/dataset_raw.jsonl`, and checkpoints progress so interrupted runs resume where they left off.

**Classify and deduplicate:**

```bash
python classify.py
```

Reads `data/dataset_raw.jsonl`, removes duplicate IDs, normalizes language labels, and writes files classified by queries in `data/classified/` and `data/report.json`.

---

## Output Format

Each line in the output JSONL is one article:

```json
{
  "source": "scielo",
  "query": "renal physiology",
  "id": "S0080-62342026000100413",
  "url": "http://...",
  "title": "Impact of invasive mechanical ventilation...",
  "abstracts": {
    "portuguese": "RESUMO...",
    "spanish": "RESUMEN...",
    "english": "ABSTRACT..."
  },
  "languages": ["english", "portuguese", "spanish"],
  "multilingual": true
}
```

---

## Report Format

```json
{
  "total_raw": 79840,
  "total_after_dedup": 79123,
  "duplicates_removed": 717,
  "multilingual_entries": 636,
  "by_query": {
    "cardiovascular physiology": 9274,
    "cellular physiology": 8857,
    "digestive physiology": 9534,
    "endocrine physiology": 7908,
    "general physiology": 6729,
    "nervous physiology": 9058,
    "renal physiology": 9671,
    "reproductive physiology": 8637,
    "respiratory physiology": 9455
  },
  "by_source": {
    "pubmed": 78248,
    "scielo": 875
  },
  "by_language": {
    "english": 77549,
    "chinese": 785,
    "spanish": 478,
    "portuguese": 305,
  },
  "duplicate_ids": [
    "42104836",
    "42104080",
  ]
```

---

## Language Support

Abstracts are normalized to full language names (e.g. `"en"` → `"english"`, `"eng"` → `"english"`). Supported ISO 639-1 and ISO 639-2 codes cover 40+ languages across Germanic, Romance, Slavic, Semitic, East Asian, and South/Southeast Asian families.

---

## Block Handling (SciELO)

SciELO is behind Bunny CDN bot protection. The scraper handles this with:

- **Playwright** for all search pagination (real Chromium TLS fingerprint)
- **aiohttp** for individual article fetches (faster, CDN less aggressive on direct URLs)
- **Automatic cookie refresh** via Playwright when a block is detected
- **Block retry cap** of 3 attempts per page before aborting the query
- **Adaptive delay** that backs off when results look sparse

If the cookie expires between runs, it is refreshed automatically on the next execution.

---

## Checkpointing

Progress is saved after each query to a checkpoint file. Re-running the pipeline skips already-collected article IDs, so interrupted runs are safe to resume without duplicating data.

---

## Notes

- PubMed fetches up to 20000 results per query in batches of 200 via the Entrez API
- Arxiv fetches up to 20000 results per query in batches of 100 via the Arxiv API
- SciELO paginates until a page returns 0 results
- A free NCBI API key is recommended — get one at [ncbi.nlm.nih.gov/account](https://www.ncbi.nlm.nih.gov/account/)