import re

from app.domain.exceptions import TagTitleInvalidError


class TagTitleValidator:
    def __init__(self, min_length: int, max_length: int, pattern: str, stop_words: list[str]) -> None:
        self._min_length = min_length
        self._max_length = max_length
        self._pattern = re.compile(pattern, re.UNICODE)
        self._stop_words = stop_words

    def validate(self, title: str) -> None:
        if not (self._min_length <= len(title) <= self._max_length):
            raise TagTitleInvalidError()
        if not self._pattern.match(title):
            raise TagTitleInvalidError()
        lowered = title.lower()
        if any(word in lowered for word in self._stop_words):
            raise TagTitleInvalidError()
