import re

from app.domain.exceptions import TagTitleInvalidError


class TagTitleValidator:
    def __init__(self, min_length: int, max_length: int, pattern: str) -> None:
        self._min_length = min_length
        self._max_length = max_length
        self._pattern = re.compile(pattern, re.UNICODE)

    def validate(self, title: str) -> None:
        if not self._min_length <= len(title) <= self._max_length:
            raise TagTitleInvalidError()
        if self._pattern.fullmatch(title) is None:
            raise TagTitleInvalidError()
        if not any(char.isalnum() for char in title):
            raise TagTitleInvalidError()
