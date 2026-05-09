# cli.py
import argparse
import asyncio
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pesquisa",
        description="Coletor e exportador de resumos científicos",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- fetch ---
    fetch_parser = sub.add_parser("fetch", help="Coleta resumos do PubMed, SciELO e/ou arXiv")
    fetch_parser.add_argument(
        "--sources",
        nargs="+",
        choices=["pubmed", "scielo", "arxiv"],
        default=["pubmed", "scielo", "arxiv"],
        metavar="SOURCE",
        help="Fontes a coletar. Disponíveis: pubmed, scielo, arxiv. Padrão: todas",
    )
    fetch_parser.add_argument(
        "--queries",
        nargs="+",
        metavar="QUERY",
        help="Consultas a executar. Substitui as queries do .env se fornecido",
    )
    fetch_parser.add_argument(
        "--output",
        default="data/output.jsonl",
        metavar="FILE",
        help="Arquivo de saída JSONL (padrão: data/output.jsonl)",
    )

    # --- classify ---
    classify_parser = sub.add_parser("classify", help="Deduplica e classifica idiomas do JSONL")
    classify_parser.add_argument(
        "--input",
        default="data/output.jsonl",
        metavar="FILE",
        help="Arquivo JSONL de entrada (padrão: data/output.jsonl)",
    )
    classify_parser.add_argument(
        "--output",
        default="data/output_clean.jsonl",
        metavar="FILE",
        help="Arquivo JSONL de saída (padrão: data/output_clean.jsonl)",
    )
    classify_parser.add_argument(
        "--report",
        default="data/report.json",
        metavar="FILE",
        help="Arquivo de relatório JSON (padrão: data/report.json)",
    )

    # --- to-csv ---
    csv_parser = sub.add_parser("to-csv", help="Converte JSONL para CSV")
    csv_parser.add_argument(
        "--input",
        default="data/output_clean.jsonl",
        metavar="FILE",
        help="Arquivo JSONL de entrada (padrão: data/output_clean.jsonl)",
    )
    csv_parser.add_argument(
        "--output",
        default="data/output_clean.csv",
        metavar="FILE",
        help="Arquivo CSV de saída (padrão: data/output_clean.csv)",
    )

    # --- run (fetch + classify + to-csv in one shot) ---
    run_parser = sub.add_parser("run", help="Executa fetch → classify → to-csv em sequência")
    run_parser.add_argument(
        "--sources",
        nargs="+",
        choices=["pubmed", "scielo", "arxiv"],
        default=["pubmed", "scielo", "arxiv"],
        metavar="SOURCE",
        help="Fontes a coletar. Padrão: todas",
    )
    run_parser.add_argument(
        "--queries",
        nargs="+",
        metavar="QUERY",
        help="Consultas a executar. Substitui as queries do .env se fornecido",
    )

    # --- audit ---
    audit_parser = sub.add_parser("audit", help="Lista todos os rótulos de idioma únicos no JSONL")
    audit_parser.add_argument(
        "--input",
        default="data/output.jsonl",
        metavar="FILE",
        help="Arquivo JSONL a auditar (padrão: data/output.jsonl)",
    )

    return parser


async def cmd_fetch(args):
    import os
    from dotenv import load_dotenv
    from utils import load_checkpoint, save_checkpoint, save_jsonl_async, hash_text
    from pubmed.fetcher import fetch_pubmed
    from scielo.fetcher import fetch_scielo
    from arxiv_local.fetcher import fetch_arxiv

    load_dotenv()

    queries = args.queries or [
        q.strip() for q in os.getenv("QUERIES", "").split(",") if q.strip()
    ]

    if not queries:
        print("[CLI] Nenhuma query encontrada. Use --queries ou defina QUERIES no .env")
        sys.exit(1)

    fetchers = {
        "pubmed": lambda q, cp: asyncio.get_event_loop().run_in_executor(None, fetch_pubmed, q, cp),
        "scielo": lambda q, cp: fetch_scielo(q),
        "arxiv":  lambda q, cp: asyncio.get_event_loop().run_in_executor(None, fetch_arxiv, q, cp),
    }

    checkpoint = load_checkpoint()

    for q in queries:
        futures = [fetchers[s](q, checkpoint) for s in args.sources]
        results = await asyncio.gather(*futures)
        combined = [item for source_results in results for item in source_results]

        for item in combined:
            item_hash = hash_text(item["id"])
            if item_hash in checkpoint["done_ids"]:
                continue
            await save_jsonl_async(item, path=args.output)
            checkpoint["done_ids"].append(item_hash)
            save_checkpoint(checkpoint)

        print(f"[DONE] {q} → {len(combined)} artigos")


def cmd_classify(args):
    from classify import classify, load_jsonl, build_report
    from pathlib import Path
    import json

    print(f"[Classify] {args.input} → {args.output}")
    entries  = load_jsonl(args.input)
    deduped, dupes = classify(entries)  # adjust to match your classify.py exports
    report   = build_report(entries, deduped, dupes)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        for entry in deduped:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    with open(args.report, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"[Classify] {len(deduped)} entradas → {args.output}")
    print(f"[Classify] Relatório → {args.report}")


def cmd_to_csv(args):
    from to_csv import convert
    convert(args.input, args.output)


def cmd_audit(args):
    from audit_lang import audit
    audit(args.input)


async def cmd_run(args):
    # synthetic args for each step using defaults
    class FetchArgs:
        sources = args.sources
        queries = args.queries
        output  = "data/output.jsonl"

    class ClassifyArgs:
        input  = "data/output.jsonl"
        output = "data/output_clean.jsonl"
        report = "data/report.json"

    class CsvArgs:
        input  = "data/output_clean.jsonl"
        output = "data/output_clean.csv"

    await cmd_fetch(FetchArgs())
    cmd_classify(ClassifyArgs())
    cmd_to_csv(CsvArgs())


def main():
    parser = build_parser()
    args   = parser.parse_args()

    if args.command == "fetch":
        asyncio.run(cmd_fetch(args))
    elif args.command == "classify":
        cmd_classify(args)
    elif args.command == "to-csv":
        cmd_to_csv(args)
    elif args.command == "audit":
        cmd_audit(args)
    elif args.command == "run":
        asyncio.run(cmd_run(args))


if __name__ == "__main__":
    main()