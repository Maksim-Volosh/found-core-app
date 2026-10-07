from app.domain.entities import ProfileEntity


class ProfileNotFoundError(Exception):
    # Also raised for a profile that belongs to another user, so its existence is not revealed.
    message = "Profile not found."

    def __init__(self) -> None:
        super().__init__(self.message)


class ProfileAlreadyExistsError(Exception):
    message = "A profile for this category and role already exists."

    def __init__(self, profile: ProfileEntity) -> None:
        super().__init__(self.message)
        self.profile = profile


class ProfileNotActivatableError(Exception):
    message = "Only an active profile can be made the current one."

    def __init__(self) -> None:
        super().__init__(self.message)


class ProfileHiddenError(Exception):
    message = "This profile was hidden by moderation."

    def __init__(self) -> None:
        super().__init__(self.message)


class InvalidProfileTextError(Exception):
    message = "Profile text is invalid."

    def __init__(self, field: str) -> None:
        super().__init__(self.message)
        self.field = field


class InvalidCountryError(Exception):
    message = "Country is not supported."

    def __init__(self) -> None:
        super().__init__(self.message)


class InvalidTimezoneError(Exception):
    message = "Timezone does not belong to the selected country."

    def __init__(self) -> None:
        super().__init__(self.message)


class TooFewTagsError(Exception):
    message = "Not enough tags."

    def __init__(self) -> None:
        super().__init__(self.message)


class TooManyTagsError(Exception):
    message = "Too many tags."

    def __init__(self) -> None:
        super().__init__(self.message)


class ProfileTagInvalidError(Exception):
    # Unknown id, a tag outside the profile's category/role scope, or the same tag listed twice.
    message = "Profile tags are invalid."

    def __init__(self) -> None:
        super().__init__(self.message)


class InvalidExtraAttributesError(Exception):
    message = "Role-specific attributes are invalid."

    def __init__(self) -> None:
        super().__init__(self.message)
