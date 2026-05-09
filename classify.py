# tools/classify.py
import json
from pathlib import Path
from collections import defaultdict
from shared.langs import normalize_lang_key
from utils import load_jsonl, RAW_FILE, CLEAN_FILE, REPORT_FILE

def dedup(entries: list[dict]) -> tuple[list[dict], list[dict]]:
    seen = {}
    dupes = []

    for entry in entries:
        eid = entry.get("id")
        if not eid:
            continue
        if eid in seen:
            dupes.append(entry)
        else:
            seen[eid] = entry

    return list(seen.values()), dupes


def classify_languages(entry: dict) -> dict:
    abstracts = entry.get("abstracts", {})

    normalized = {}
    for lang, text in abstracts.items():
        if text and text.strip():
            normalized[normalize_lang_key(lang)] = text.strip()

    entry["abstracts"]    = normalized
    entry["languages"]    = sorted(normalized.keys())
    entry["multilingual"] = len(normalized) > 1

    return entry


def build_report(original, deduped, dupes) -> dict:
    lang_counts = defaultdict(int)
    source_counts = defaultdict(int)
    multilingual = 0

    for entry in deduped:
        source_counts[entry.get("source", "unknown")] += 1
        for lang in entry.get("languages", []):
            lang_counts[lang] += 1
        if entry.get("multilingual"):
            multilingual += 1

    return {
        "total_raw":          len(original),
        "total_after_dedup":  len(deduped),
        "duplicates_removed": len(dupes),
        "multilingual_entries": multilingual,
        "by_source":          dict(source_counts),
        "by_language":        dict(sorted(lang_counts.items(), key=lambda x: -x[1])),
        "duplicate_ids":      [d["id"] for d in dupes],
    }


def main():
    print(f"[Classify] Loading {RAW_FILE}...")
    entries = load_jsonl(RAW_FILE)
    print(f"[Classify] Loaded {len(entries)} entries")

    deduped, dupes = dedup(entries)
    print(f"[Classify] {len(dupes)} duplicates removed → {len(deduped)} unique entries")

    classified = [classify_languages(e) for e in deduped]

    Path(CLEAN_FILE).parent.mkdir(parents=True, exist_ok=True)

    with open(CLEAN_FILE, "w", encoding="utf-8") as f:
        for entry in classified:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    report = build_report(entries, classified, dupes)
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"[Classify] Done → {CLEAN_FILE}")
    print(f"[Classify] Report:")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main() 