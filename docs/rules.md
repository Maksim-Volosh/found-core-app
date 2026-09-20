# FoundCore Development Rules

These are mandatory development and code style rules.

## 1. Architecture

Follow the architecture and patterns defined in `CLAUDE.md`.

### Domain entities

* Domain entities belong only in `app/domain/entities/`.
* Do not define domain entities or equivalent dataclasses in `api/`, `application/`, or `infrastructure/`.
* Keep unrelated entities in separate modules. Whether a group of entities/exceptions is "related" enough to share one module (e.g. a whole small flow in one file) or needs its own file is a per-case call, not a fixed formula — see `CLAUDE.md` for the current file map and reasoning.

### Module naming

* Name a module after what it actually implements, not after the nearest domain entity — e.g. a router/use case/mapper that is really about the auth flow belongs in `auth.py`, not `user.py`, even where it touches the `User` entity.

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
* `__init__` may take extra parameters to carry context the caller needs (e.g. a ban reason) — only the `message` class attribute stays fixed.

### Dependency Injection

Use the `Container` and `Depends()` patterns defined in `CLAUDE.md`.

Do not introduce another DI or composition pattern.

### Request-scoped auth

* Protect an endpoint with `Depends(get_current_user)` (see `CLAUDE.md`, "Request-scoped auth") — never with middleware.
* Never trust mutable user state (ban status, roles, token validity) from the JWT payload alone. Re-check it against the current DB row inside the auth dependency on every request.

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
