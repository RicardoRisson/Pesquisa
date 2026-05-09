# tools/to_csv.py
import json
import csv
import argparse
from pathlib import Path

INPUT_FILE  = "data/output_clean.jsonl"
OUTPUT_FILE = "data/output_clean.csv"

KNOWN_LANGUAGES = [
    "english", "portuguese", "spanish", "french", "german", "italian",
    "russian", "polish", "czech", "slovak", "ukrainian", "bulgarian",
    "serbian", "croatian", "slovenian", "arabic", "hebrew", "chinese",
    "japanese", "korean", "hindi", "bengali", "tamil", "telugu",
    "malayalam", "thai", "vietnamese", "indonesian", "malay", "turkish",
    "persian", "greek", "hungarian", "georgian", "armenian", "swahili",
    "tagalog", "dutch", "swedish", "norwegian", "danish", "finnish",
    "afrikaans", "romanian", "catalan", "galician",
]

# base columns always present
BASE_COLUMNS = ["source", "query", "id", "url", "title", "languages", "multilingual"]

# one column per language for the abstract text
ABSTRACT_COLUMNS = [f"abstract_{lang}" for lang in KNOWN_LANGUAGES]

ALL_COLUMNS = BASE_COLUMNS + ABSTRACT_COLUMNS


def entry_to_row(entry: dict) -> dict:
    abstracts = entry.get("abstracts", {})
    row = {
        "source":      entry.get("source", ""),
        "query":       entry.get("query", ""),
        "id":          entry.get("id", ""),
        "url":         entry.get("url", ""),
        "title":       entry.get("title", ""),
        "languages":   "|".join(entry.get("languages", [])),  # e.g. "english|portuguese"
        "multilingual": entry.get("multilingual", False),
    }
    for lang in KNOWN_LANGUAGES:
        row[f"abstract_{lang}"] = abstracts.get(lang, "")
    return row


def convert(input_file: str, output_file: str):
    input_path  = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        print(f"[CSV] File not found: {input_path}")
        return

    rows = []
    errors = 0

    with open(input_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                rows.append(entry_to_row(entry))
            except json.JSONDecodeError as e:
                print(f"[CSV] Line {i} malformed, skipping: {e}")
                errors += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ALL_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[CSV] {len(rows)} entries written to {output_path}")
    if errors:
        print(f"[CSV] {errors} malformed lines skipped")


def parse_args():
    parser = argparse.ArgumentParser(description="Convert JSONL to CSV")
    parser.add_argument("--input",  default=INPUT_FILE,  help=f"Input JSONL (default: {INPUT_FILE})")
    parser.add_argument("--output", default=OUTPUT_FILE, help=f"Output CSV (default: {OUTPUT_FILE})")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    convert(args.input, args.output)