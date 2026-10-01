import pytest

from app.domain.services import clean_tag_title, normalize_tag_title


class TestCleanTagTitle:
    def test_trims_and_collapses_whitespace(self):
        assert clean_tag_title("  Node   .js \t ") == "Node .js"

    def test_keeps_case(self):
        assert clean_tag_title("Node.js") == "Node.js"

    def test_applies_nfkc(self):
        # Full-width Latin letters fold to plain ASCII under NFKC.
        assert clean_tag_title("Ｐython") == "Python"

    def test_collapses_non_breaking_and_unicode_spaces(self):
        assert clean_tag_title("Machine  Learning") == "Machine Learning"


class TestNormalizeTagTitle:
    def test_lowercases(self):
        assert normalize_tag_title("Node.js") == "node.js"

    def test_casefolds_cyrillic(self):
        assert normalize_tag_title("ПИТОН") == "питон"

    def test_casefold_can_grow_the_string(self):
        # Why the normalized_title column is wider than title.
        assert normalize_tag_title("Straße") == "strasse"
        assert len(normalize_tag_title("ß" * 10)) == 20

    @pytest.mark.parametrize("title", ["C++", "C#", ".NET", "CI/CD", "UI/UX", "Node.js", "front-end"])
    def test_keeps_punctuation_used_by_it_tags(self, title):
        assert normalize_tag_title(title) == title.casefold()

    def test_c_family_stays_distinct(self):
        assert len({normalize_tag_title(t) for t in ("C", "C#", "C++")}) == 3

    def test_semantic_duplicates_are_not_merged(self):
        # Merging these is the job of moderation (stage 8), not of normalization.
        assert len({normalize_tag_title(t) for t in ("Node.js", "NodeJS", "Node Js")}) == 3

    @pytest.mark.parametrize("variant", ["NODE.JS", "node.js", "  Node.JS  ", "Ｎode.js"])
    def test_exact_duplicates_collapse_to_one_key(self, variant):
        assert normalize_tag_title(variant) == normalize_tag_title("Node.js")

    @pytest.mark.parametrize("title", ["Node.js", "  Python  ", "Straße", "Ｐython"])
    def test_is_idempotent(self, title):
        once = normalize_tag_title(title)
        assert normalize_tag_title(once) == once
