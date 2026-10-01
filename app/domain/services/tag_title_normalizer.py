import unicodedata


def clean_tag_title(title: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", title).split())


def normalize_tag_title(title: str) -> str:
    return clean_tag_title(title).casefold()
