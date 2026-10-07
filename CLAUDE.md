# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Mandatory development rules (do/don't) are in [`docs/rules.md`](docs/rules.md) — read it before writing or changing any code.** This file (`CLAUDE.md`) is the source of truth for product context and architecture; `docs/rules.md` is the normative rulebook and points back here for the concrete patterns (e.g. `Container`/DI).

## Project overview

FoundCore is a Telegram Mini App + bot for networking. It connects people across two domain blocks:

- **Tech & Product** — co-founders, developers, designers, investors, marketers, sales/bizdev, finance/legal.
- **Edu & Growth** — study mates, language partners, hackathon/pet-project teammates, mentors.

The original product spec (a `.docx` kept outside this repo) is summarized in this file; if a product or architecture decision isn't covered here, ask rather than guess.

**This iteration builds backend only** — no frontend work.

**Key pivot — no swipes.** The original swipe/mutual-match concept (Like/Skip, contact revealed only on mutual like) is cancelled. The current mechanic is a **feed with filters and search**: a user browses recommendations and/or applies filters; a contact opens immediately on button press, with no reciprocity required. The only feedback loop is a notification to the profile owner that "someone opened your contact" — there are no likes or matches.

Explicitly out of scope: a social network/chat/content platform as the core product, gamification, subscriptions, public reputation/levels, fully autonomous AI-matching (AI assists scoring but is never the sole judge of compatibility).

## Repository state

Stage 1 (`skeleton`), stage 2 (`auth-telegram`) and stage 3 (`taxonomy`) are fully implemented. Stage 2 shipped `POST /api/v1/auth/telegram` plus the JWT-verification dependency (`get_current_user`), which stage 3 is the first to actually consume — every taxonomy endpoint requires a valid token, there's no anonymous read access to the reference data. Stage 3 added the `categories`/`roles`/`role_fields`/`tags`/`tag_scopes` tables, all 5 taxonomy endpoints (see "API" below), an idempotent seed script (`scripts/dev_seed_taxonomy.py`), and Redis cache-aside for the read-heavy reference tables. Stage 4 (`profiles`) is implemented on `feat/profiles` (see "Profiles" below): `profiles`/`profile_tags` tables, 9 endpoints under `/api/v1/profiles`, `profiles` and `user.active_profile_id` in the `/auth/telegram` response. Everything else in "Development stages" below is not started yet. The schema is managed by Alembic (see "Migrations"); the app no longer creates tables itself. Tests: a pytest suite split into `tests/unit` (no Postgres/Redis, in-memory fakes) and `tests/integration` (real Postgres and Redis, guarded so it can only touch `*_test_db` and a non-default Redis DB). It covers the auth flow (`initData` and JWT hostile-input cases, the first-login race, ban/`token_version` over real HTTP, user repository, mappers), stage 3 (tag normalizer/validator, taxonomy use cases, `SqlAlchemyTaxonomyRepository`, the self-healing Redis cache, request bounds on all 5 taxonomy endpoints, the dev seed), transaction behavior (`IUnitOfWork`) and `Settings` (prod fail-fast); GitHub Actions runs it with coverage on every PR.

## User flow

- **Auth**: user opens the bot → Mini App → frontend gets Telegram `initData` → backend verifies the signature locally (HMAC-SHA256 from the bot secret, no call to Telegram's servers) → issues a JWT (24h, no refresh token — the Mini App just re-authenticates from fresh `initData` on expiry).
- A user with no Telegram username cannot be contacted by other users (no way to open a chat with them), so: (a) that user cannot view the feed themselves until they set a username, and (b) other users never see that user as a recommendation, since a contact they couldn't actually reach would be useless. The auth endpoint itself does not enforce this — it's checked once the profile form (anketa) is filled, which is where a username becomes required to proceed.
- **Profile/onboarding**: on first login the user accepts terms and fills a form built from the taxonomy reference tables (category → role → role-specific dynamic fields) plus the common fields described by `GET /profiles/form-config` (country, timezone, bio, goals, tags). Taxonomy-driven parts are never hardcoded on the frontend; the common fields are a fixed typed contract (see "Profiles").
- **Multi-profile**: a user can hold multiple profiles (one per category+role pair, e.g. a developer profile and a separate language-partner profile) and switch the active one via a menu. The active profile determines the feed, available filters, what counts as "already viewed," and whose name a contact is opened under.
- **Feed has two modes**: Discovery (no filters — semantic similarity + tag/role match within the same category) and Search (filters, three-tier cascade so the screen is never empty).
- **Viewed profiles ("grey cards")**: a profile the user already opened stays in place in the ranking but gets `is_viewed = true`; the frontend renders it grey. The flag is set on opening the full card, not on scrolling past it.
- **Contact opening**: opens immediately, no mutuality. The profile owner gets a bot notification naming who opened their contact (name, role, profile link). No random-profile backfill when filters exhaust — an explicit "nobody yet" state is shown instead.

## Taxonomy

Categories/roles/tags/fields live in Postgres and are cached in Redis; the taxonomy is data-driven and expands without backend code changes. The roles (and their fields/tags) are seeded by `scripts/dev_seed_taxonomy.py` (`founder`, `product_project`, `engineering`, `design`, `marketing`, `sales_bizdev`, `finance_legal` under Tech & Product; `study_mate`, `language_buddy`, `pet_project_partner`, `mentor_mentee` under Edu & Growth).

**`role_fields` vs `tags` — deliberate split.** `role_fields` only holds single-choice *structural* attributes that gate filtering (`grade`, `project_stage`, `specialization`, language `level`, `workload`, `format`, `frequency`) — always `field_type = select`. Skills, tools, stack, domain and similar open-ended or multi-value attributes are **tags**, not `role_fields` — they're unbounded and grow from user input, which `role_fields` (a fixed reference table maintained by admins) isn't designed for. `RoleFieldType` has `multi_select`/`number`/`text`/`boolean` members for future use, but the stage 3 seed only ever emits `select`.

**Common fields are duplicated per role, not shared by reference.** Tech & Product roles each get their own `workload` + `format` rows in `role_fields`; Edu & Growth roles each get their own `frequency` + `format` rows (`language_buddy` overrides `format` with its own call/chat/in-person options instead of the generic online/offline one, since it's a better fit for that role specifically). This is plain row duplication across roles, not a shared/inherited field — `role_fields` has no such concept, and adding one wasn't justified for 11 roles. See `scripts/dev_seed_taxonomy.py` for the exact per-role field list.

**Redis cache-aside: two independent repositories, orchestrated by the use case** (see `docs/rules.md`, "Repository responsibility" / "Caching (Redis)"):

```
                   Use Case
                  /        \
 ITaxonomyRepository      ITaxonomyCacheRepository
          ↓                         ↓
 SqlAlchemyTaxonomyRepository   RedisTaxonomyCacheRepository
          ↓                         ↓
      PostgreSQL                  Redis
```

`SqlAlchemyTaxonomyRepository` (`infrastructure/repositories/sqlalchemy_taxonomy.py`) only talks to Postgres. `ITaxonomyCacheRepository` (`domain/interfaces/taxonomy_cache.py`) is typed: `get_categories`/`set_categories`, `get_roles_by_category`/`set_roles_by_category`, `get_role_fields_by_role`/`set_role_fields_by_role`, all taking and returning domain entities. Its implementation `RedisTaxonomyCacheRepository` (`infrastructure/repositories/redis_taxonomy_cache.py`) owns everything Redis-specific: the keys (`taxonomy:categories`, `taxonomy:roles:{category_id}`, `taxonomy:role_fields:{role_id}`), entity ↔ JSON (de)serialization (including rebuilding `RoleFieldType` from its string value), the TTL (`TaxonomyConfig.cache_ttl_seconds`, 6h, passed to its constructor by `container.py`) and `RedisError` handling. For the use case, a cache miss, an unreadable cached value and a Redis outage all look the same: `None`. A corrupt or outdated value (bad JSON, missing/unknown field, renamed enum member) is logged and treated as a miss, and the use case's following `set_*` overwrites it, so the cache heals itself instead of failing for the whole TTL. The repository instance lives for one request: after its first `RedisError` it skips Redis for the rest of that request (one timeout at worst, not one per call), and `RedisConfig.socket_timeout` is 0.3 s. The `roles`/`fields` use cases check the cache **first** and only on a miss verify that the category/role exists (404) — a hit costs no Postgres query, and a deleted category may be served from cache until the TTL expires (accepted). The seed script clears `taxonomy:*` keys (own Redis client, errors only logged) after committing. All list queries have a deterministic tie-breaker (`sort_order, id`; `suggest`: `usage_count DESC, title, id`). So the use case is pure orchestration:

```python
async def execute(self) -> list[CategoryEntity]:
    cached = await self._taxonomy_cache_repository.get_categories()
    if cached is not None:
        return cached
    categories = await self._taxonomy_repository.get_categories()
    await self._taxonomy_cache_repository.set_categories(categories)
    return categories
```

A generic `ICacheRepository` (`get(key) -> Any` / `set(key, value, ttl)`) was tried and rejected in review: it leaked cache keys, `asdict`, enum rebuilding and TTL into the use cases and hid the real contract behind `Any`. `tags/suggest` is deliberately **not cached** — it's already backed by the `pg_trgm` index, and the query space (arbitrary substrings × category × role × caller) doesn't cache well.

**Tag title validation lives in a domain service and is validation only, not moderation.** `TagTitleValidator` (`domain/services/tag_title_validator.py`) takes `min_length`/`max_length`/`pattern` in its constructor (`TaxonomyConfig` values, injected by `container.py`) and checks only length, allowed characters via `re.fullmatch()` and that the title contains at least one letter or digit (so `...`, `+++`, `_` are rejected as empty of content). Request bounds are enforced earlier by pydantic/FastAPI: ids are `1..MAX_INT64` (`Int64Id` in `api/v1/schemas/common.py`, `Path`/`Query` `ge`/`le` in the router) so an out-of-range id is `422`, never a `500` from asyncpg; `title` is capped at 256 characters and the suggest `q` at 128 before any normalization runs. The default pattern `[\w\s+#./-]+` lets through IT tags like `C++`, `C#`, `.NET`, `Node.js`, `CI/CD`, `UI/UX`. There is **no stop-word check**: it was removed in review as primitive moderation with false positives. Content checks belong to the moderation flow (custom tag → `pending` → admin approves/rejects, stage 8), not to the validator.

**Tag identity: `id` is the identity, `title` is the display value, `normalized_title` is only for exact-duplicate detection.** Tags have no slug (the old lossy `slugify` was removed: `C`/`C#`/`C++` collapsed, Unicode titles could become empty, and nothing needs a public tag identifier — relations go through `tag_id`). `normalized_title` is `UNIQUE` and is produced by `normalize_tag_title` in `domain/services/tag_title_normalizer.py`: NFKC → trim/collapse whitespace → `casefold()`, nothing else — no transliteration, no stripping of `+ # . / -`. The stored `title` is `clean_tag_title` (NFKC + whitespace only, case kept). The column is `String(255)` because `casefold()` can make the string longer than `title` (64). `categories.slug`/`roles.slug` are unrelated admin-defined keys and stay.

Normalization deliberately does **not** detect semantic duplicates: `Node.js`, `NodeJS`, `Node Js` are three different tags until moderation (stage 8) merges them via a planned `merged_into_tag_id` (not implemented yet).

`POST /taxonomy/tags/custom` flow: clean title → validate → check category/role → look up by `normalized_title` → if found, reuse it (any status), otherwise insert a `PENDING` tag → idempotently add the caller's `(category, role)` scope (tag insert and scope insert share one transaction; the use case commits once at the end). A `REJECTED` match raises `TagRejectedError` → `409`. The response always carries the canonical `title`, so the frontend replaces what the user typed (`NODE.JS`) with the existing tag (`Node.js`). Race between SELECT and INSERT: `create_tag` is `INSERT ... ON CONFLICT (normalized_title) DO NOTHING RETURNING` and returns `None` on conflict; the use case then re-reads the tag. The repository never decides "duplicate means return existing" — that stays in the use case; `UNIQUE` is the final guarantee.

Known simplifications: (1) scopes are not moderated — submitting an existing tag from another category/role adds a scope there immediately; (2) `suggest` shows pending tags only to `created_by_user_id` (the original proposer), so a second user who got an existing pending tag from `POST` won't see it in `suggest` and simply re-submits the title to get the same tag again. TODO (a follow-up PR after profiles, which now exist): `suggest` can also include tags already used in the caller's profiles.

**`tag_scopes.role_id = NULL` means "scoped to the whole category"** (enforced idempotent via a `NULLS NOT DISTINCT` unique constraint on `(tag_id, category_id, role_id)`, so a repeat scope insert can't duplicate a category-wide row). The stage 3 seed only creates role-specific scopes (every seeded example tag belongs to one role), so category-wide scoping exists in the schema and in `suggest_tags`'s query logic but has no seeded example yet — the first real category-wide custom tag will be the first row to actually use it.

## Profiles

A user holds several profiles, at most one per (category, role); one of them is the **active** one (`users.active_profile_id`), which will drive the feed, the filters and whose name a contact is opened under.

**Content.** `country_code`, `timezone`, `bio`, `goals_description` (both 200..2000 characters after trimming), tags (**5..15**), and `extra_attributes` — the role's own `role_fields` (only `is_required` ones are mandatory; an empty value or `null` means "not set" and the key is dropped; only `select` is supported, other field types are rejected). There is no `languages` and no `looking_for`. All limits are `ProfileConfig` values (`core/config.py`), a plain `BaseModel`; the same values feed the validators and `form-config`, so frontend and backend limits cannot drift. Category and role cannot be changed after creation.

**Tags** live in `profile_tags(profile_id, tag_id)` with real foreign keys (both `ON DELETE CASCADE`: deleting a profile removes only the links, deleting a tag removes it from profiles). Allowed: `approved` or `pending` (also another user's pending tag, which `POST /taxonomy/tags/custom` may hand out), in the scope of the profile's category/role (a category-wide scope, `role_id IS NULL`, also fits). `rejected` → `409 TagRejectedError`; unknown/out-of-scope/duplicate ids → `400`. Duplicates are checked before the count, so five copies of one tag fail. A tag deleted later may leave a profile with fewer than 5 tags; the minimum is only enforced on save.

**Country and timezone.** All ISO 3166 countries that have a zone in `zone.tab` are accepted (`ProfileConfig.allowed_country_codes`, empty = all). `TimezoneCatalog` (`application/services/timezone_catalog.py`) reads `zone.tab`/`iso3166.tab` from the pinned `tzdata` package (the same source `ZoneInfo` uses). A timezone is valid only if it belongs to the chosen country (`RU` + `Asia/Tokyo` → `400`) and is checked only on write. Country names are English only (the frontend localizes by code); a zone label is the city from the IANA id; `utc_offset` (`+02:00`) is computed on the fly, never stored.

**`GET /profiles/form-config`** (auth required) returns `{bio, goals: {min_length, max_length}, tags: {min_count, max_count}, countries: [{code, name, timezones: [{id, label, utc_offset}]}]}`. Common fields are a fixed typed schema; a new common field means a schema change, a column, a migration and a validator.

**Lifecycle.** A new profile is `active` at once (there are no drafts; if drafts are ever needed they become a separate `profile_drafts` table). Statuses: `active | paused | hidden_by_admin`. The first profile becomes the active one; later ones do not change it.
- `activate`: only for an `active` profile; `paused` → `409`.
- `pause`: if it was the active profile, the pointer moves to the user's newest remaining `active` profile (`created_at DESC, id DESC`) or becomes `NULL`.
- `resume`: `paused → active`; becomes the active profile if the user has none.
- `delete`: physical; same pointer rule as `pause`.
- `hidden_by_admin` (set by moderation, stage 8): the owner cannot edit, resume or activate it → `409`.
- `pause`/`resume`/`activate` are idempotent (a repeat returns the profile, no error, no commit).
- A use case that moves the pointer also updates the `user.active_profile_id` it was given, so the response can report `is_active` without re-reading the user.

**Visibility.** Everything under `/profiles` belongs to the owner. Someone else's profile is `404`, never `403`. Other people's profiles will only be visible through the feed (stage 6).

**Create/update flow.** `ProfileContentValidator` (`application/services`) is shared by create and update: form rules (`ProfileFormValidator`, domain), role attributes (`ExtraAttributesValidator`, domain), then tags via `ITaxonomyRepository.get_tags_in_scope_by_ids` (returns any status; the status decision stays in the validator). Create is `INSERT ... ON CONFLICT (user_id, category_id, role_id) DO NOTHING RETURNING`; `None` → re-read → `ProfileAlreadyExistsError` → `409` whose body carries the existing profile (`{"detail": {"message", "profile"}}`). `PUT /profiles/{id}` is a full replace (`extra="forbid"`, so `category_id`/`role_id` in the body → `422`) and takes `SELECT ... FOR UPDATE` on the profile so two parallel PUTs do not collide on the `profile_tags` primary key. `IUserRepository.set_active_profile` is a narrow `UPDATE`, because `update` writes only Telegram fields.

**Contract for stage 6 (not implemented yet).** A user without an active profile gets `409 no_active_profile` from the feed (discovery and search) — distinct from `NO_CANDIDATES_YET` and `END_OF_FEED`. A paused profile never appears in other people's feeds. The frontend shows onboarding when the profile list is empty and a "resume" screen when profiles exist but all are paused.

**Follow-up PRs after profiles, in this order:** (1) a username gate — a dependency on top of `get_current_user` that fails with a machine-readable code on `GET /taxonomy/categories` and `POST /profiles`, so the user learns about the missing username before the form; (2) `terms_accepted_at` in the auth response and an endpoint to accept the terms, the form is shown only after acceptance and with a username; (3) `tags/suggest` also returns tags used in the caller's profiles. Not in this PR: embedding columns (stage 5), `DELETE /users/me`, the ~100-profile seed (needed before stage 6).

## Data model (`users`, taxonomy, profiles implemented; rest planned)

- **`users`** (implemented) — Telegram account: `id`, `telegram_id` (unique), `first_name`, `last_name`, `username`, `photo_url`, `language_code` (Telegram's UI language, not a profile language), `terms_accepted_at`, `is_admin`, `is_banned`, `ban_reason`, `token_version` (bumping this instantly invalidates issued JWTs on ban), `active_profile_id`, `created_at`, `last_active_at`, `deleted_at` (nullable, mapped to the entity but no logic reads or writes it yet — account deletion is planned to physically remove data, see "Moderation, security, analytics").
- **`profiles`** (implemented) — one row per (user, category, role); `user_id` FK (`ON DELETE CASCADE`) is deliberately **not unique**, which is what enables multi-profile. Columns: `category_id`/`role_id` (no `ondelete`: deleting a taxonomy row that profiles use must fail, not wipe profiles), `country_code`, `timezone`, `bio`, `goals_description`, `extra_attributes JSONB` (no server default), `status ENUM(active|paused|hidden_by_admin)`, `created_at`, `updated_at` (set by the application). `UNIQUE (user_id, category_id, role_id)` both prevents duplicate profiles and makes double-submit safe — a repeat form submission gets a 409 with the existing profile, no need to dedupe at the nginx layer; it also serves lookups by `user_id`, so there is no separate index. Other indexes: btree `(category_id, role_id, status)`, GIN on `extra_attributes`. `users.active_profile_id` is a real FK to `profiles.id` (`ON DELETE SET NULL`, `use_alter` because of the `users ↔ profiles` cycle).
- **`profile_tags`** (implemented) — `(profile_id, tag_id)` composite PK, both FKs `ON DELETE CASCADE`, index on `tag_id`. Replaces the earlier `tags TEXT[]` idea.
- **Planned `profiles` columns (stage 5):** `embedding vector(1536)`, `embedding_input_hash`, `embedding_model`, `embedding_status`.
- **Taxonomy tables** (implemented) — `categories`, `roles(category_id)`, `role_fields(role_id, key, label, field_type, options, is_required, is_filterable, sort_order)` (drive the dynamic form/filters), `tags(title, normalized_title UNIQUE, status: approved/pending/rejected, created_by_user_id, usage_count)`, `tag_scopes(tag_id, category_id, role_id)`. `tags.title` has a GIN trigram index (`ix_tags_title_trgm`, needs the `pg_trgm` extension — enabled via a `before_create` DDL event on `Base.metadata` since `create_all` doesn't create extensions) for `tags/suggest`'s substring search. See "Taxonomy" above for the `role_fields`/`tags` split and the cache.
- **Interaction tables** — `profile_views` (source of `is_viewed`), `contact_opens` (notification + daily-limit source), `reports`, `admin_actions`.
- **Indexes** — HNSW on `profiles.embedding` (`vector_cosine_ops`), GIN on `tags` and `extra_attributes`, btree on `(category_id, role_id, status)` and `last_active_at`.

## Feed algorithm (planned)

Everything is scored relative to the viewer's **active profile**.

```
score = (0.4 · cos_sim + 0.4 · tag_overlap + 0.2 · role_affinity) · activity_factor
tag_overlap    = |A∩B| / min(|A|, |B|)
role_affinity  = 1.0 same role · 0.5 other role, same category · 0.0 other category
activity_factor = 1.0 (active ≤7d) · 0.8 (≤30d) · 0.5 (>30d)
```

If a profile has no embedding yet, the semantic term is zeroed and its weight is redistributed between tags and role — the feed keeps working, just less precisely.

- **Discovery**: single tier, candidates are active profiles in the *same category only* (excluding self/hidden/banned), sorted by score. Never backfills from another category — if the category runs out, the feed just ends honestly.
- **Search**: filters apply immediately; results are filled by a three-tier cascade so the page is never empty:
  1. `EXACT_MATCH` — category, role, and requested custom attributes all match.
  2. `PARTIAL_MATCH` — category matches, or at least one shared tag.
  3. `RECOMMENDED_BY_BIO` — vector similarity only, filters ignored.

  Tiers are consumed in order up to the page target; within a tier, sort by score.
- **Feed session pagination**: on the first request (new filters, new active profile, or expired session) the backend ranks candidates up to a **cap of 200** (top-200 of the category for discovery; tiers 1→2→3 in order for search) and stores a lightweight `(profile_id, tier, score, reasons)` list in Redis for 30 minutes, keyed by profile+mode+filters+algorithm version. Each 20-card page just slices that cached list by offset and hydrates only those 20 profiles — vector computation is never repeated per page. The session resets on filter change, active-profile change, or algorithm version bump.
  - Known limitation: if a category genuinely has more than 200 active profiles, candidates ranked below #200 in that session are never shown to that viewer — an accepted tradeoff for cheap pagination, flagged as a future risk, not expected to bite at first-cohort scale.
- **Empty states** — two distinct cases, don't conflate them: `NO_CANDIDATES_YET` (empty from the first page — "we'll keep looking and notify you") vs `END_OF_FEED` (cache exhausted after showing something — neutral "you've seen everything for now," no notify promise). Both return via `has_more: false` + a reason code in the API response, never as an error.
- **Recommendation card** — public profile data, `match_score` (0–100), `match_type` (tier), `is_viewed`, and a list of deterministically-computed (no AI call) reasons, e.g. "3 shared tags: python, fastapi, postgres", "same role", "same timezone".

## Tech stack

**In use now** (listed in `requirements.txt`):

- Python 3.12, FastAPI, Pydantic v2 (+ `pydantic-settings`), `uvicorn`.
- SQLAlchemy 2.0 (async, `asyncpg`), `PyJWT` for auth tokens, `redis` (asyncio client), `tzdata` (pinned; country/timezone catalog for profiles).
- PostgreSQL 16 — source of truth. Local/dev image is `pgvector/pgvector:pg16` (plain `postgres` images don't have the extension). Only `pg_trgm` is actually used so far (tag search); the `vector` extension and a Python `pgvector` package come with stage 5.
- Redis 7 (`redis:7-alpine` in docker-compose) — taxonomy cache today; feed sessions, rate limiting and the job queue later.
- Docker Compose for local dev.
- Tests (`requirements-dev.txt`): `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx`, `asgi-lifespan`, `freezegun`. Config is in `pyproject.toml`; the test env is `.env.test` (separate `found_core_test_db` in the dev Postgres container, Redis on localhost DB 1 so tests never flush the dev cache). CI: `.github/workflows/tests.yml` (pgvector Postgres + Redis services, `pytest -v --cov=app --cov-report=term-missing`, no coverage threshold).
- Migrations: Alembic (async template, `asyncpg` — no second sync driver), applied by hand with `alembic upgrade head`. See "Migrations" below.

**Planned, not added yet** (not in `requirements.txt`):

- `pgvector` (Python package) — embedding column and similarity queries (stages 5–6).
- `arq` — background jobs (embeddings, notifications, analytics).
- PostHog — product analytics (stage 9).
- `ruff` + `mypy` for code quality.
- nginx in front of the app in prod (stage 10).

## Layered architecture

Clean Architecture variant, chosen specifically so a two-person team can work on different modules without git conflicts. Actual structure (as built, `app/`):

```
api/v1/
  routers/{auth,taxonomy,profiles}.py       <- HTTP layer, validation + delegation only, no __init__.py
  schemas/{auth,user,taxonomy,profile}.py  <- pydantic request/response schemas, __init__.py re-exports
  mappers/{auth,user,taxonomy,profile}.py  <- domain entity -> schema (and request -> domain form entity), no __init__.py
  dependencies/auth.py             <- request-scoped Depends() (e.g. get_current_user), no __init__.py
application/
  services/{telegram_init_data,jwt_service,timezone_catalog,profile_content_validator}.py  <- reusable cross-use-case services, no __init__.py. timezone_catalog.py reads zone.tab/iso3166.tab from tzdata; profile_content_validator.py is the validation shared by profile create and update (form + role attributes + tags via the taxonomy repository)
  use_cases/{auth,taxonomy,profile}.py     <- orchestration, __init__.py re-exports
domain/
  entities/{user,auth,taxonomy,profile}.py    <- dataclasses, __init__.py re-exports. auth.py holds the whole Telegram-auth/JWT flow (init_data payload, decoded token payload, auth result) in one file — a deliberate one-off for this small flow, not a general "always merge" rule; see "Request-scoped auth" below
  exceptions/{user,auth,taxonomy,profile}.py  <- __init__.py re-exports, same auth.py grouping as entities
  interfaces/{user,taxonomy,taxonomy_cache,profile,unit_of_work}.py  <- repository ABCs, __init__.py re-exports. taxonomy_cache.py is ITaxonomyCacheRepository, typed on domain entities. unit_of_work.py is IUnitOfWork (`commit()` only), see "Transactions" below
  enums/{taxonomy,profile}.py         <- plain StrEnum members shared by entities/models/schemas (RoleFieldType, TagStatus, ProfileStatus), __init__.py re-exports
  services/{tag_title_validator,tag_title_normalizer,profile_form_validator,extra_attributes_validator}.py  <- pure domain computation/validation, no infra dependency, __init__.py re-exports. The profile validators take their limits (and the country → timezones mapping) in the constructor and return a cleaned copy. tag_title_normalizer.py is plain functions (no config/state to justify a class). See "Domain services vs. application services" in docs/rules.md
  mappers/telegram_user.py            <- domain-to-domain mappings only: `map_telegram_user_payload_to_new_user_entity` (no __init__.py)
infrastructure/
  helpers/{db_helper,redis_helper}.py     <- DB/Redis client setup, flat (no nested db/ subdir). __init__.py re-exports the `db_helper` and `redis_helper` singletons (`from app.infrastructure.helpers import db_helper, redis_helper`)
  models/{base,user,taxonomy,profile}.py          <- SQLAlchemy 2.0 models, __init__.py re-exports Base + models. base.py also registers a `before_create` DDL event enabling `pg_trgm`, since `create_all` doesn't create extensions
  mappers/{user_mapper,taxonomy_mapper,profile_mapper}.py  <- SQLAlchemy model <-> domain entity, no __init__.py. Profile models have no relationships, so the profile mapper takes the tags as a separate argument
  repositories/{user,sqlalchemy_taxonomy,sqlalchemy_profile,redis_taxonomy_cache}.py  <- domain interface implementations, __init__.py re-exports. sqlalchemy_profile.py loads the tags of all requested profiles in one query (ordered by tag id) and locks the profile row in `update`. sqlalchemy_taxonomy.py is Postgres-only; redis_taxonomy_cache.py owns Redis keys, serialization, TTL and RedisError handling — see "Taxonomy" above and "Repository responsibility" in docs/rules.md
  unit_of_work.py                         <- SqlAlchemyUnitOfWork: IUnitOfWork over the request's AsyncSession
core/
  config.py                        <- Settings (pydantic-settings)
  composition/{container,di}.py    <- composition root, no __init__.py
```

Outside `app/`:

```
tests/
  conftest.py                      <- only loads .env.test BEFORE any app.* import (settings/db_helper are import-time singletons); nothing here touches a database, so unit tests need neither Postgres nor Redis
  unit/                            <- no DB/Redis: init_data validator (incl. an openssl-computed signature vector), JWT service, auth use cases, get_current_user, mappers, tag normalizer/validator, taxonomy use cases (with fakes), Settings (prod fail-fast)
  integration/                     <- real Postgres/Redis via the ASGI app. Its own conftest.py holds the guard (refuses a DB not ending in `_test_db` or Redis DB 0), the test DB + tables, per-test truncate, `session`, `redis_client` (fresh client per test, flushed first — the module-level `redis_helper.client` is bound to one event loop), `taxonomy_client` (app client using that Redis client), `taxonomy_data`. Tests: auth endpoint and flow (ban/`token_version` over real HTTP), protected route, user repository, unit of work, taxonomy repository, Redis cache repository (corrupt values, hung Redis), taxonomy endpoints (incl. Redis-down fallback and input bounds), the dev seed script, physical schema (indexes/constraints)
  fixtures/                        <- entity factories, init_data builders, direct DB helpers, fake user/taxonomy repositories (the fake user repository copies on read and writes only the columns the real one writes) and `FakeUnitOfWork`, ORM taxonomy seed helpers (`taxonomy_data.py`), `auth.py` (user + Bearer header)
scripts/                           <- dev-only: dev_gen_init_data.py, dev_seed_taxonomy.py
alembic.ini, migrations/           <- Alembic config, async env.py (URL from settings, Base.metadata) and versions/. Infrastructure artifact, deliberately outside app/
.github/workflows/tests.yml        <- CI: pytest against pgvector Postgres + Redis
.env.template / .env.test          <- `.env.template` is only a template to copy to `.env` (never read by the app); `.env.test` holds test overrides (found_core_test_db, Redis on localhost DB 1). `.dockerignore` keeps `.env`, `.git`, `.venv`, tests out of the image
requirements.txt / requirements-dev.txt, pyproject.toml (pytest config)
```

`__init__.py` rule: added only to packages that get imported from often across layers, and it re-exports via `__all__` so the import stays short (`from app.domain.entities import UserEntity`). Packages nobody imports directly from outside (mappers, routers, services, composition, dependencies) skip it — import the full module path instead.

Naming: a module is named after what it actually implements, not the nearest domain entity. `routers/auth.py`, `schemas/auth.py`, `mappers/auth.py` and `use_cases/auth.py` all used to be named `user.py` — but their content is the Telegram-auth flow (init_data validation, token issuing/verification), not generic User CRUD, so keeping them as `user.py` would have collided with real user-only concerns as soon as any got added (e.g. `UserPublicSchema`/`map_user_entity_to_user_public_schema`, which now correctly live in the `user.py` sibling of each split pair).

### Composition root (`core/composition/`)

`Container` is a plain class with **lazy factory methods**, not an eagerly-built `@dataclass`/`__post_init__` — cheaper (only what a given request needs gets constructed) and it scales to use cases that need a runtime parameter the constructor can't know in advance:

```python
class Container:
    def __init__(self, session: AsyncSession, redis_client: Redis):
        self.session = session
        self.redis_client = redis_client

    # ---------- services ----------
    def telegram_init_data_service(self) -> TelegramInitDataValidator: ...  # AuthConfig bot token + init_data TTL
    def jwt_service(self) -> JWTService: ...

    # ---------- unit of work ----------
    def unit_of_work(self) -> SqlAlchemyUnitOfWork: ...                       # same session as the repositories

    # ---------- repositories ----------
    def user_repo(self) -> SqlAlchemyUserRepository: ...
    def taxonomy_repo(self) -> SqlAlchemyTaxonomyRepository: ...              # session + TaxonomyConfig.suggest_limit, no Redis
    def taxonomy_cache_repo(self) -> RedisTaxonomyCacheRepository: ...        # redis_client + TaxonomyConfig.cache_ttl_seconds

    # ---------- domain services ----------
    def tag_title_validator(self) -> TagTitleValidator: ...  # built from TaxonomyConfig values

    # ---------- use cases ----------
    def auth_use_case(self) -> AuthenticateTelegramUserUseCase: ...
    def verify_access_token_use_case(self) -> VerifyAccessTokenUseCase: ...  # user_repo() + jwt_service(), used by get_current_user
    def get_categories_use_case(self) -> GetCategoriesUseCase: ...  # taxonomy_repo() + taxonomy_cache_repo()
    # ... plus get_roles_by_category / get_role_fields_by_role (same two repos), suggest_tags and create_custom_tag use cases
    # ... and for profiles: profile_repo(), timezone_catalog(), profile_form_validator() / extra_attributes_validator() (limits and the allowed-country → zones mapping come from ProfileConfig), profile_content_validator(), and the 9 profile use cases (auth_use_case() also gets profile_repo())
```

`redis_client` was added to the constructor once the first Redis-backed repository (`taxonomy_cache_repo`) showed up — before that, `Container` only ever needed a session. `taxonomy_repo` and `taxonomy_cache_repo` are separate factories on purpose (see "Repository responsibility" in `docs/rules.md`): a use case that needs both caching and Postgres access gets both and orchestrates them itself, e.g. `GetCategoriesUseCase(taxonomy_repository=self.taxonomy_repo(), taxonomy_cache_repository=self.taxonomy_cache_repo())`. Settings such as the TTL are wired into the repository here, never passed into the use case.

`di.py` wires it into FastAPI with the classic `Depends()`-as-default-value style (not `Annotated[...]`):

```python
async def get_container(session: AsyncSession = Depends(db_helper.session_getter)) -> Container:
    return Container(session=session, redis_client=redis_helper.client)
```

Routers call it as `container.auth_use_case().execute(...)` — never construct a use case or repository directly.

### Transactions

Repositories never commit: they `flush`/`execute` and return. The use case that owns a scenario commits once at the end via `IUnitOfWork.commit()` (`SqlAlchemyUnitOfWork` wraps the same `AsyncSession` the repositories use; `Container.unit_of_work()` builds it). So `CreateCustomTagUseCase` creates the tag and its scope in **one** transaction — a failure between the two leaves no orphan tag. On any exception nothing is committed and closing the request-scoped session (`db_helper.session_getter`) rolls back; `IUnitOfWork` has no `rollback()` on purpose until a long-lived session (e.g. a background job) needs one. Read-only use cases never commit. Unit tests substitute `FakeUnitOfWork` (counts commits); `tests/integration/test_unit_of_work.py` checks the real behavior against Postgres through a second session.

### Auth input hardening

Everything that reaches the auth flow is treated as hostile until its *shape* is checked, so malformed input ends as `400`/`401`, never `500`:

- **`initData`** (`TelegramInitDataValidator`): the signature is compared as bytes (non-ASCII `hash` is just a mismatch); a parameter sent twice (including `hash`) is malformed; `auth_date` must be ASCII digits (≤15) and not further in the future than `AuthConfig.init_data_max_future_skew_seconds` (60 s) — an old one is `expired`; `user` must be a JSON object with an integer `id` in `1..MAX_INT64` (`domain/constants.py`, not a bool/string), a non-empty `first_name`, optional string fields, lengths matching the `users` columns, and no NUL characters (Postgres rejects them). The request body caps `init_data` at 8192 characters.
- **JWT** (`JWTService.decode_access_token`): `exp`, `iat`, `sub`, `telegram_id`, `token_version` are required (a signed token without `exp` would never expire); their types are checked and a bad `sub` is `TokenInvalidError`, not a raw `ValueError`.
- **First login race**: `IUserRepository.create` is `INSERT ... ON CONFLICT (telegram_id) DO NOTHING RETURNING` and returns `None` when a parallel request created the user first; `AuthenticateTelegramUserUseCase` then re-reads the user and continues as a returning login (`is_new_user=false`). Of N simultaneous first logins exactly one reports `is_new_user=true`.

### Configuration and secrets

Settings come from the process environment and `.env` only (`.env.template` is a copy-me template, not a fallback; the app container gets `.env` through `env_file` in `docker-compose.yaml`). `APP_CONFIG__RUN__ENV` is `dev` (default), `test` or `prod`. With `prod`, `Settings` refuses to start (pydantic `ValidationError` listing every problem) if `auth.secret_key` is a known placeholder or shorter than 32 characters, `bot.token` is a placeholder (`""`, `key`, `123`), or `run.reload` is true — so a forgotten secret fails the first deploy instead of silently running with public keys. `BotConfig.token` has no default. `RunConfig` is a plain `BaseModel` (not `BaseSettings`) so its default instance never reads unprefixed variables such as a shell's `ENV`. The Docker image runs as a non-root user and `.env` is excluded by `.dockerignore`.

### Migrations

Alembic, in `migrations/` at the repo root. `migrations/env.py` is the async template: it takes the URL from `settings.db.url` (never from `alembic.ini`, so credentials stay in the environment) and uses `Base.metadata` as the target, so **every new model must be exported from `app/infrastructure/models/__init__.py`**, otherwise autogenerate won't see it. `compare_type` and `compare_server_default` are on. Revision files are named `YYYY_MM_DD_HHMM-<rev>_<slug>.py`.

Migrations are applied **manually** (`docker compose exec found_core_mini_app alembic upgrade head`); the app does not touch the schema on startup (a DB without `upgrade head` fails with `relation does not exist`). Running them automatically on deploy is stage 10. After a `git pull` that brings new revisions, run `upgrade head`.

Creating a revision: `docker compose exec -u "$(id -u):$(id -g)" found_core_mini_app alembic revision --autogenerate -m "..."` — the `-u` is needed because the container user can't write into the bind-mounted `migrations/versions/`. Autogenerate output is a draft and is always reviewed by hand: it does not emit extensions (`CREATE EXTENSION`, e.g. `pg_trgm` in the initial revision, `vector` in stage 5), and `downgrade()` must drop PG enum types explicitly because `drop_table` leaves them behind.

The `before_create` DDL event in `models/base.py` that enables `pg_trgm` fires only for `create_all`, so migrations create the extension explicitly.

**Tests don't use migrations**: the integration `conftest.py` still builds the test database with `create_all`, and there is no test comparing migrations with the models. A model change without a revision is therefore not caught by CI — check with `alembic check` ("No new upgrade operations detected") and review the revision file.

Seed data (taxonomy) is not part of migrations — `scripts/dev_seed_taxonomy.py` fills it after `upgrade head`. How reference data gets into production is a stage 10 question.

### Request-scoped auth (`api/v1/dependencies/auth.py`)

Any future protected endpoint declares `current_user: UserEntity = Depends(get_current_user)` — the same explicit per-route `Depends()` style as `Depends(get_container)`, never a global middleware (a second, parallel DI mechanism is exactly what `docs/rules.md` forbids).

```python
bearer_scheme = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    container: Container = Depends(get_container),
) -> UserEntity:
    try:
        return await container.verify_access_token_use_case().execute(credentials.credentials)
    except (TokenInvalidError, TokenExpiredError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except UserBannedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.ban_reason or str(exc)) from exc
```

It lives in `api/v1/dependencies/`, not `core/composition/di.py`: `di.py` is pure composition (build a `Container` from a session, no HTTP awareness), while this dependency does HTTP-layer work — parses the `Authorization: Bearer` header (`HTTPBearer`, not `OAuth2PasswordBearer`, since there's no OAuth2 password flow here) and translates domain exceptions into status codes, exactly like a router's own `try/except` does.

`VerifyAccessTokenUseCase` (`application/use_cases/auth.py`) does the actual check, and re-reads the user from Postgres by id on **every call** rather than trusting the token payload beyond `sub`/`token_version`:

```python
async def execute(self, token: str) -> UserEntity:
    payload = self._jwt_service.decode_access_token(token)
    user = await self._user_repository.get_by_id(payload.user_id)
    if user is None or user.token_version != payload.token_version:
        raise TokenInvalidError()
    if user.is_banned:
        raise UserBannedError(user.ban_reason)
    return user
```

Two separate checks, catching two separate situations:

- **`token_version` mismatch** → `401`. Catches a token issued *before* a ban/logout bump — the classic `token_version` revocation already described under "Data model".
- **live `is_banned`** → `403` with `ban_reason` in the body. Catches a token issued *after* the ban (e.g. the user re-authenticated with a fresh `initData` post-ban and got a new, version-matching token) — `token_version` alone would let that request through, since the version matches the freshly-issued token.

`is_banned`/`ban_reason` are deliberately **not** put in the JWT payload: a signed JWT can't change after issuing, so baking ban state into it would only take effect on the *next* login, not instantly. Reading the live DB row on every request is what makes a ban instant. This costs nothing extra — it's the same single indexed lookup by `users.id` that the `token_version` check already requires.

## API (Auth, Taxonomy and Profiles implemented, rest planned)

- **Auth** (implemented): `POST /api/v1/auth/telegram { init_data }` → local HMAC-SHA256 signature check (data-check-string per Telegram's algorithm, secret = `HMAC_SHA256(key=b"WebAppData", msg=bot_token)`, `initData` rejected if `auth_date` older than **300s**) → upsert user by `telegram_id` → JWT via **PyJWT**, `HS256`, **1440 min (24h)**, no refresh token (client just re-calls this endpoint with fresh `initData` on 401 elsewhere). Bot token is a dev placeholder (`APP_CONFIG__BOT__TOKEN=123`) until a real bot exists. Response: `access_token`, `token_type`, `is_new_user`, `user` (id, telegram_id, first_name, last_name, username, photo_url, is_admin, `is_banned`, `ban_reason`), `profiles` (the user's profiles ordered by `created_at, id`, each with `is_active`) and `user.active_profile_id`. A **banned user still authenticates successfully (200)** — `is_banned`/`ban_reason` are in the response so the frontend can render a ban screen instead of a bare error; this endpoint never blocks on ban or on missing username (see "User flow" for where username actually gets enforced). JWT verification on other (protected) endpoints is implemented as the reusable `Depends(get_current_user)` dependency (see "Request-scoped auth" above) — first actually consumed by the Taxonomy endpoints below.
- **Taxonomy** (implemented, all behind `Depends(get_current_user)` — no anonymous reads): `GET /taxonomy/categories`, `GET /taxonomy/categories/{id}/roles` (404 if the category doesn't exist), `GET /taxonomy/roles/{id}/fields` (404 if the role doesn't exist), `GET /taxonomy/tags/suggest?q=&category_id=&role_id=` (case-insensitive substring match via the `pg_trgm` GIN index on `tags.title`, query escaped so `%`/`_`/`\` match literally; returns approved tags in scope plus the caller's own pending ones; not cached — see "Taxonomy" below), `POST /taxonomy/tags/custom { title, category_id, role_id? }` → technical validation only (length 1–64 — single-letter tags like `C` and `R` are valid —, allowed characters incl. `+ # . /` for IT tags; no stop-word check, content is left to moderation — see "Taxonomy" above), dedupe by `normalized_title` (NFKC + casefold + whitespace collapse, see "Taxonomy"), new tags get status `pending`, usable by their author immediately (the author's own pending tags show up in their own `suggest` results). If a tag with the same normalized title already exists, it is returned (canonical `title` included) instead of creating a new one — also across users and for pending tags; a `rejected` match returns `409`. Re-submitting is safe (mirrors the double-submit-safe pattern used for `profiles`).
- **Profiles** (implemented, all behind `Depends(get_current_user)`; rules in "Profiles" above): `GET /profiles/form-config`, `POST /profiles` (201; `400` invalid content, `404` unknown category/role, `409` duplicate with the existing profile in the body or a rejected tag), `GET /profiles/me`, `GET /profiles/{id}` (`404` for a missing or foreign profile), `PUT /profiles/{id}` (full replace), `POST /profiles/{id}/activate`, `POST /profiles/{id}/pause|resume`, `DELETE /profiles/{id}` (204). `/form-config` and `/me` are declared before `/{id}`. Request bodies use `extra="forbid"`; `tag_ids` ≤ 50, `bio`/`goals_description` ≤ 4000, `extra_attributes` ≤ 32 keys (key ≤ 64, value ≤ 128), ids `1..MAX_INT64`. Planned: `DELETE /users/me`.
- **Feed & contacts**: `GET /feed?mode=discovery|search&...&cursor=&limit=20`, `GET /feed/cards/{profile_id}`, `POST /feed/views`, `POST /profiles/{id}/contact`, `POST /reports`.
- **Admin**: user/profile/report lists, tag moderation queue, ban/unban, hide profile, approve/reject/merge tag, inspect why a specific recommendation was made. Gated on `is_admin` of the user row that `get_current_user` re-reads from Postgres on every request — never on the `is_admin` claim in the JWT (a token can't change after issuing, so a demoted admin would keep access until it expires). The token deliberately carries no admin claim (an older token that still has one is accepted and the claim ignored); clients learn `is_admin` from `user.is_admin` in the `/auth/telegram` response.

## Embeddings — must work without an OpenAI key

Profile text (category, role, tags, bio, goals) is hashed; if the hash is unchanged, the embedding call is not repeated. Embeddings sit behind an `EmbeddingProvider` interface with two implementations:

- `OpenAIProvider` — `text-embedding-3-small`, 1536 dims, enabled by an API key.
- `StubProvider` — deterministic pseudo-random vector derived from the text hash; used while no OpenAI key is configured.

Switching providers is one environment variable, no code change — this lets the whole feed (including the semantic scoring term) be developed and tested before an OpenAI key exists. Provider unavailability never blocks the product: a profile is still created and ranked by tags/role, the semantic term is just temporarily skipped.

## Moderation, security, analytics

- Reports, bans (banning bumps `token_version`, instantly invalidating already-issued JWTs — the read side of this, `get_current_user`, is already implemented, see "Request-scoped auth"; the admin ban action itself that sets `is_banned`/bumps `token_version` is stage 8 work), admin profile hiding, custom-tag moderation queue (approve/reject/merge).
- Rate limiting at two levels: nginx by IP, application-level per-user in Redis (contact opens, tag creation, reports, autocomplete).
- Custom tags: technical validation at creation (length, allowed characters, implemented in stage 3); content checks (spam, forbidden words) via the moderation queue, not a stop-word list (dropped in stage 3 review); daily creation limit via per-user rate limiting (stage 8).
- Account deletion physically removes profiles, embeddings, and views.
- Analytics events go to PostHog in the background, never blocking the request: signup, onboarding step timings/abandonment, profile create/edit, profile switch, feed open, scroll depth, empty screen, card open (with tier + score), contact open, filters applied, tag created, report, account deletion. AI-cost accounting is out of scope for this iteration.

## Development stages

Each stage is its own `feat/...` branch and its own PR for review.

| # | Stage | Content |
|---|-------|---------|
| 1 | skeleton | ✅ Project scaffold, docker-compose (Postgres+pgvector, Redis), `.env.template`. CI: GitHub Actions runs pytest (`.github/workflows/tests.yml`); lint/type checks are not set up yet. |
| 2 | auth-telegram | ✅ `initData` validation, `users` table, `POST /auth/telegram` issuing JWT. ✅ Auth *dependency* (`get_current_user`) to verify JWT — first consumed by the stage 3 taxonomy endpoints. |
| 3 | taxonomy | ✅ Reference tables (`categories`, `roles`, `role_fields`, `tags`, `tag_scopes`) + idempotent seed, all 5 endpoints, Redis cache-aside (categories/roles/role fields, 6h TTL, falls back to Postgres if Redis is down). |
| 4 | profiles | Implemented on `feat/profiles` (✅ once merged): profile CRUD, multi-profile, active-profile switching, pause/resume, form-field validation, `form-config`, `profiles` in the auth response, taxonomy seed with 8–10 tags per role |
| 5 | embeddings | Embedding provider, stub, background queue, degradation |
| 6 | feed | Scoring, discovery + search tier cascade, feed sessions, card |
| 7 | contacts-notifications | Contact opening, limits, bot notification |
| 8 | moderation | Reports, bans, profile hiding, tag moderation |
| 9 | analytics | PostHog events |
| 10 | deploy | nginx, prod config, migrations on deploy, README |

Stage 6 depends on stages 3–5; stage 7 depends on stage 6. All other stages can proceed in parallel.

## Acceptance criteria

- Tests run against a real Postgres with `pgvector` — feed logic lives in SQL and can't be verified with mocks.
- Unit tests on the scoring formula: weights, `tag_overlap`, `activity_factor`, degradation with no embedding.
- Integration tests: cascade correctly falls through to tier 2/3 under narrow filters; empty screen shown instead of random profiles; page order is stable across repeated requests.
- `initData` verification: valid / malformed / expired (all implemented; covered by automated tests in `tests/unit/test_telegram_init_data_validator.py` and `tests/integration/test_auth_telegram_endpoint.py`; `scripts/dev_gen_init_data.py` generates payloads for manual checks).
- Access-token verification (`get_current_user`): valid / expired / malformed / revoked (`token_version` mismatch) / banned (live `is_banned` check, `403` with `ban_reason`) — all implemented in `VerifyAccessTokenUseCase`; covered by `tests/unit/test_auth_use_cases.py`, `tests/unit/test_get_current_user_dependency.py` and `tests/integration/test_protected_route.py`. The taxonomy endpoints are the first protected routes to actually exercise this dependency over HTTP.
- Auth endpoint does not reject on missing username or on ban (see "API" — Auth). Feed-side: a user with no username can't view the feed and is excluded from other users' feeds (see "User flow"); a banned user never appears in results.
- A repeat `POST /profiles` with the same role returns 409.
- Seed script for ~100 test profiles across both categories — the feed can't be evaluated visually without this.
- Taxonomy: `categories/{id}/roles` and `roles/{id}/fields` 404 on an unknown id; `tags/custom` rejects an empty (after whitespace cleanup)/too-long/invalid-character title (`400`); re-submitting the same title for the same category/role doesn't create a duplicate tag or scope row; `tags/suggest` returns a caller's own pending tags but not other users' pending tags — covered by `tests/unit/test_taxonomy_use_cases.py`, `tests/integration/test_taxonomy_repository.py` and `tests/integration/test_taxonomy_endpoints.py`.

## Risks and open questions

- **Cold start** — the feed is meaningless until the DB has 50–100 profiles in the relevant category; sourcing the first closed cohort by segment matters more than algorithm quality at launch.
- **200-candidate session cap** — profiles ranked below #200 in their category are never shown to a viewer in that session. A deliberate tradeoff for cheap pagination, not an accidental gap; not expected to matter at first-cohort scale, but raising the cap or adding an exploration slot for tail profiles will be needed as the audience grows.
- **Match-percentage calibration** — formula weights and cutoff thresholds will need tuning once real usage data exists.
- **Embedding stub** — validates feed mechanics but not semantic search quality; that's only visible once a real OpenAI key is wired in.
- **Contact privacy** — contacts open without reciprocity, so protection relies entirely on rate limits, logging, and moderation rather than mutual consent.
- **TODO — `is_embedded` on `role_fields`** — `extra_attributes` currently plays no role in Discovery or the scoring formula (only used for Search's `EXACT_MATCH` tier filtering). A cheap future improvement: a boolean flag on `role_fields` marking which field values get folded into the embedding input text (e.g. append `"grade: middle"` alongside `category, role, tags, bio, goals`), giving Discovery a partial semantic signal from `extra_attributes` without hand-rolling a per-`field_type` comparison function. An explicit scoring term instead (comparing fields directly, e.g. exact-match bonus for same `grade`) was considered and rejected — `field_type`s are heterogeneous (`select`, `multi_select`, `number`, `text`), each needing its own similarity function, and it would mean reweighing the fixed formula without real usage data to calibrate against (see "Match-percentage calibration" above). Not scheduled for any stage yet; keep in mind when designing `role_fields` in stage 3 so adding this column later isn't a breaking migration.
