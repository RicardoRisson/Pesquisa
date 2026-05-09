# tools/audit_langs.py
import json
from collections import Counter

INPUT_FILE = "data/dataset_raw.jsonl"

def audit():
    lang_counter = Counter()
    total = 0

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                for lang in entry.get("abstracts", {}).keys():
                    lang_counter[lang.lower().strip()] += 1
                total += 1
            except json.JSONDecodeError:
                continue

    print(f"[Audit] {total} entries scanned")
    print(f"[Audit] {len(lang_counter)} unique language labels found:\n")
    for lang, count in lang_counter.most_common():
        print(f"  {lang!r:<30} {count:>6} entries")


if __name__ == "__main__":
    audit()