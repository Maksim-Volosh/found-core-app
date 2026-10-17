import hashlib


def build_embedding_input(
    category_title: str,
    role_title: str,
    tag_titles: list[str],
    bio: str,
    goals: str,
) -> str:
    # Tags are sorted so that the text, and therefore the hash, does not depend on the order they are stored in.
    return "\n".join(
        [
            f"Category: {category_title}",
            f"Role: {role_title}",
            f"Tags: {', '.join(sorted(tag_titles))}",
            f"Bio: {bio}",
            f"Goals: {goals}",
        ]
    )


def compute_input_hash(model: str, text: str) -> str:
    # The model is part of the hash: vectors of different models are not comparable and must be recomputed.
    return hashlib.sha256(f"{model}:{text}".encode()).hexdigest()
