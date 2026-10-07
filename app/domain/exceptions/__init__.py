__all__ = [
    "InitDataMalformedError",
    "InitDataSignatureInvalidError",
    "InitDataExpiredError",
    "TokenExpiredError",
    "TokenInvalidError",
    "UserBannedError",
    "CategoryNotFoundError",
    "RoleNotFoundError",
    "TagTitleInvalidError",
    "TagRejectedError",
    "ProfileNotFoundError",
    "ProfileAlreadyExistsError",
    "ProfileNotActivatableError",
    "ProfileHiddenError",
    "InvalidProfileTextError",
    "InvalidCountryError",
    "InvalidTimezoneError",
    "TooFewTagsError",
    "TooManyTagsError",
    "ProfileTagInvalidError",
    "InvalidExtraAttributesError",
]

from app.domain.exceptions.auth import (
    InitDataExpiredError,
    InitDataMalformedError,
    InitDataSignatureInvalidError,
    TokenExpiredError,
    TokenInvalidError,
)
from app.domain.exceptions.profile import (
    InvalidCountryError,
    InvalidExtraAttributesError,
    InvalidProfileTextError,
    InvalidTimezoneError,
    ProfileAlreadyExistsError,
    ProfileHiddenError,
    ProfileNotActivatableError,
    ProfileNotFoundError,
    ProfileTagInvalidError,
    TooFewTagsError,
    TooManyTagsError,
)
from app.domain.exceptions.taxonomy import (
    CategoryNotFoundError,
    RoleNotFoundError,
    TagRejectedError,
    TagTitleInvalidError,
)
from app.domain.exceptions.user import UserBannedError
