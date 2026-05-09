def extract_pubmed_abstracts(article_data: dict) -> dict[str, str]:
    abstracts = {}

    # primary abstract — may be english or the article's original language
    if "Abstract" in article_data:
        lang = article_data.get("Language", ["en"])[0].lower()  # Language lives one level up
        text = " ".join(str(x) for x in article_data["Abstract"]["AbstractText"])
        if text:
            abstracts[lang] = text

    # OtherAbstract holds translations (e.g. portuguese, spanish)
    for other in article_data.get("OtherAbstract", []):
        lang = str(other.get("@Language", "unknown")).lower()
        text = " ".join(str(x) for x in other.get("AbstractText", []))
        if text:
            abstracts[lang] = text

    return abstracts  # e.g. {"en": "...", "pt": "...", "es": "..."}