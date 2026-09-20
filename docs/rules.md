# FoundCore Development Rules

These are mandatory development and code style rules.

## 1. Architecture

Follow the architecture and patterns defined in `CLAUDE.md`.

### Domain entities

* Domain entities belong only in `app/domain/entities/`.
* Do not define domain entities or equivalent dataclasses in `api/`, `application/`, or `infrastructure/`.
* Keep unrelated entities in separate modules.

### Entity identity

* `NewXEntity` must not have an `id` field.
* `XEntity` must have a required `id: int`.
* `IRepository.create()` accepts `NewXEntity` and returns `XEntity`.
* Do not use `id: int | None` instead.

### Optional fields

Use `| None` only when the value can actually be absent according to business rules or an external contract.

Do not add optional fields or defaults for convenience.

### Domain exceptions

Use this pattern:

```python
class SomeError(Exception):

    message = "Something went wrong."

    def __init__(self) -> None:
        super().__init__(self.message)
```

* Inherit directly from `Exception`.
* Keep the message as a class attribute.
* Raise without passing a message.

### Dependency Injection

Use the `Container` and `Depends()` patterns defined in `CLAUDE.md`.

Do not introduce another DI or composition pattern.

### Mappers

Use directional names:

```text
map_<source>_to_<target>
```

## 2. Code style

* Follow the style of the surrounding code.
* Use clear and explicit names.
* Keep functions and classes focused.
* Keep business logic out of HTTP handlers.
* Do not duplicate business logic between layers.
* Do not introduce abstractions, helpers, or patterns without a real need.
* Do not add docstrings or comments unless they explain something non-obvious.
* Do not rewrite working code without a reason related to the current task.
* Prefer simple, readable solutions over clever ones.

## 3. Execution and validation

Claude must **never run commands, tests, linters, formatters, type checkers, builds, migrations, Docker commands, or other project operations on its own**.

After making changes:

* briefly explain what was changed;
* provide the exact commands the user should run to test or verify the changes manually;
* do not claim that the changes were tested or verified unless the user ran the commands and provided the results.
