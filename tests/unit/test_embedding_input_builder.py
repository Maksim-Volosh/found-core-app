import re

from app.domain.services import build_embedding_input, compute_input_hash


def _text(**overrides) -> str:
    values = dict(
        category_title="Engineering",
        role_title="Backend developer",
        tag_titles=["Python", "FastAPI", "PostgreSQL"],
        bio="I build APIs.",
        goals="Find a product co-founder.",
    )
    values.update(overrides)
    return build_embedding_input(**values)


class TestBuildEmbeddingInput:
    def test_contains_every_part_of_the_profile(self):
        text = _text()

        assert "Engineering" in text
        assert "Backend developer" in text
        assert "I build APIs." in text
        assert "Find a product co-founder." in text

    def test_tags_are_sorted(self):
        assert "Tags: FastAPI, PostgreSQL, Python" in _text()

    def test_tag_order_does_not_change_the_text(self):
        # The tags come from the database in no guaranteed order; the hash must not depend on it.
        assert _text(tag_titles=["Python", "FastAPI"]) == _text(tag_titles=["FastAPI", "Python"])

    def test_different_content_gives_different_text(self):
        assert _text(bio="Another bio.") != _text()
        assert _text(tag_titles=["Python"]) != _text()


class TestComputeInputHash:
    def test_is_a_sha256_hex_digest(self):
        assert re.fullmatch(r"[0-9a-f]{64}", compute_input_hash("model", "text"))

    def test_is_stable(self):
        assert compute_input_hash("model", "text") == compute_input_hash("model", "text")

    def test_changes_with_the_model(self):
        assert compute_input_hash("model-a", "text") != compute_input_hash("model-b", "text")

    def test_changes_with_the_text(self):
        assert compute_input_hash("model", "text a") != compute_input_hash("model", "text b")

    def test_model_and_text_cannot_be_shifted_into_each_other(self):
        # The ":" separator keeps ("ab", "c") apart from ("a", "bc").
        assert compute_input_hash("ab", "c") != compute_input_hash("a", "bc")
