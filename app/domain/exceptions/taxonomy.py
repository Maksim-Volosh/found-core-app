class CategoryNotFoundError(Exception):
    message = "Category not found."

    def __init__(self) -> None:
        super().__init__(self.message)


class RoleNotFoundError(Exception):
    message = "Role not found."

    def __init__(self) -> None:
        super().__init__(self.message)


class TagTitleInvalidError(Exception):
    message = "Tag title is invalid."

    def __init__(self) -> None:
        super().__init__(self.message)
