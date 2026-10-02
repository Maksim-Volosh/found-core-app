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
* Exception: when concurrent requests can hit a unique constraint (`users.telegram_id`, `tags.normalized_title`), `create()` uses `INSERT ... ON CONFLICT DO NOTHING RETURNING` and returns `XEntity | None`. `None` only means "another request inserted it first"; the use case re-reads and decides what to do.
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

### Repository responsibility

* A repository is responsible for exactly one data source/resource (one Postgres table family, one cache, etc.). Do not combine two infrastructure sources (e.g. Postgres and Redis) in a single repository class — split them and use both from the use case.
* A repository must not make use-case-level decisions and must not raise domain/application exceptions. It returns an entity, `None`, a list of entities, or the result of an operation — nothing more.
* Whether `None` means "not found" (and what to do about it, e.g. raise `CategoryNotFoundError`) is decided by the use case, not the repository.

### Transactions

* A repository never commits. It only prepares changes (`add`/`flush`/`execute`); the use case that owns the scenario commits **once, at the end**, through `IUnitOfWork` (`domain/interfaces/unit_of_work.py`).
* Use cases depend on `IUnitOfWork`, never on `AsyncSession`. The implementation (`SqlAlchemyUnitOfWork`) is built by `Container` from the same session as the repositories.
* Read-only use cases do not commit. On failure nothing is committed and the request-scoped session is closed by `db_helper.session_getter`, which rolls back — there is deliberately no `rollback()` on `IUnitOfWork` until a real need appears (e.g. a long-lived session in a background job).

### Configuration values

* Do not hardcode tunable values (TTLs, limits, size thresholds, regex patterns, etc.) as module-level constants inside a repository, use case, or domain service. They belong in `core/config.py`.
* A repository/use case/domain service receives these values through its constructor, wired up in `container.py` — the same way `jwt_service()`/`telegram_init_data_service()` already inject `AuthConfig` values. Do not import `settings` directly inside a use case or domain service body.

### Domain services vs. application services

* `domain/services/` — pure domain computation and business rules with **no infrastructure dependency**: slug generation, discount calculation, validating a domain value, etc. Usable from both use cases and application services.
* `application/services/` — logic reused across multiple use cases that **does** depend on an implementation/infrastructure detail (secrets, HMAC, an external format). Do not move something into `application/services` just because a use case happens to use it — decide first whether it's actually a pure domain rule (→ `domain/services`) before reaching for this layer.

### Request-scoped auth

* Protect an endpoint with `Depends(get_current_user)` (see `CLAUDE.md`, "Request-scoped auth") — never with middleware.
* Never trust mutable user state (ban status, `is_admin`/roles, token validity) from the JWT payload alone. Re-check it against the current DB row inside the auth dependency on every request.

### Request input

* Every id taken from a path, query or body is bounded to `1..MAX_INT64` (`Int64Id` in `api/v1/schemas/common.py`, or `Path`/`Query` with `ge`/`le`), so an out-of-range value is `422`, never a `500` from the database driver.
* Every free-text field has a `max_length` in the request schema, set above the business limit (which stays in the domain validator) so oversized bodies are rejected before any processing.
* Malformed external input (Telegram `initData`, JWT) ends as a domain error mapped to `400`/`401`, never an unhandled exception.

### Mappers

Use directional names:

```text
map_<source>_to_<target>
```

### Caching (Redis)

* Caching is a separate concern from data access. A data repository (e.g. `SqlAlchemyTaxonomyRepository`) must not know about Redis, cache keys, or TTLs. Use a separate cache repository typed on domain entities instead (`ITaxonomyCacheRepository` → `RedisTaxonomyCacheRepository`); it owns cache keys and serialization.
* Cache-aside orchestration (check cache → miss → read the data repository → populate the cache) lives in the **use case**, which holds both the data repository and the cache repository — not inside either repository.
* `RedisTaxonomyCacheRepository` catches `redis.exceptions.RedisError` internally, logs a warning, and returns `None`/no-ops on failure — a Redis outage may degrade latency, it must never break the request or raise up to the use case.
* A cached value that cannot be parsed or rebuilt into entities (corrupt JSON, outdated shape) is a miss, never an exception. After the first `RedisError` a cache repository instance stops calling Redis for the rest of its lifetime (one request).
* In a read use case, check the cache before any existence check against the data repository, so a cache hit costs no database query.
* Cache TTLs are config values (see "Configuration values" above), not hardcoded constants. The TTL is passed to the cache repository in `container.py`, not to the use case.

## 2. Code style

* Follow the style of the surrounding code.
* Use clear and explicit names.
* Keep functions and classes focused.
* Keep business logic out of HTTP handlers.
* Do not duplicate business logic between layers.
* Do not introduce abstractions, helpers, or patterns without a real need.
* Do not add docstrings or comments unless they explain something non-obvious.
* Write all comments and docstrings in English, regardless of the language used in chat or commit messages.
* Do not rewrite working code without a reason related to the current task.
* Prefer simple, readable solutions over clever ones.

## 3. Execution and validation

Claude must **never run commands, tests, linters, formatters, type checkers, builds, migrations, Docker commands, or other project operations on its own**.

After making changes:

* briefly explain what was changed;
* provide the exact commands the user should run to test or verify the changes manually;
* do not claim that the changes were tested or verified unless the user ran the commands and provided the results.
