# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Mandatory development rules (do/don't) are in [`docs/rules.md`](docs/rules.md) — read it before writing or changing any code.** This file (`CLAUDE.md`) is the source of truth for product context and architecture; `docs/rules.md` is the normative rulebook and points back here for the concrete patterns (e.g. `Container`/DI).

## Project overview

FoundCore is a Telegram Mini App + bot for networking. It connects people across two domain blocks:

- **Tech & Product** — co-founders, developers, designers, investors, marketers, sales/bizdev, finance/legal.
- **Edu & Growth** — study mates, language partners, hackathon/pet-project teammates, mentors.

The full spec is `FoundCore_TZ.docx` at the repo root — read it before making product/architecture decisions that aren't covered below.

**This iteration builds backend only** — no frontend work.

**Key pivot — no swipes.** The original swipe/mutual-match concept (Like/Skip, contact revealed only on mutual like) is cancelled. The current mechanic is a **feed with filters and search**: a user browses recommendations and/or applies filters; a contact opens immediately on button press, with no reciprocity required. The only feedback loop is a notification to the profile owner that "someone opened your contact" — there are no likes or matches.

Explicitly out of scope: a social network/chat/content platform as the core product, gamification, subscriptions, public reputation/levels, fully autonomous AI-matching (AI assists scoring but is never the sole judge of compatibility).

## Repository state

Stage 1 (`skeleton`), stage 2 (`auth-telegram`) and stage 3 (`taxonomy`) are fully implemented. Stage 2 shipped `POST /api/v1/auth/telegram` plus the JWT-verification dependency (`get_current_user`), which stage 3 is the first to actually consume — every taxonomy endpoint requires a valid token, there's no anonymous read access to the reference data. Stage 3 added the `categories`/`roles`/`role_fields`/`tags`/`tag_scopes` tables, all 5 taxonomy endpoints (see "API" below), an idempotent seed script (`scripts/dev_seed_taxonomy.py`), and Redis cache-aside for the read-heavy reference tables. Everything else in "Development stages" below is not started yet. No Alembic yet (see "Tech stack"), no tests.

## User flow (from the spec)

- **Auth**: user opens the bot → Mini App → frontend gets Telegram `initData` → backend verifies the signature locally (HMAC-SHA256 from the bot secret, no call to Telegram's servers) → issues a JWT (24h, no refresh token — the Mini App just re-authenticates from fresh `initData` on expiry).
- A user with no Telegram username cannot be contacted by other users (no way to open a chat with them), so: (a) that user cannot view the feed themselves until they set a username, and (b) other users never see that user as a recommendation, since a contact they couldn't actually reach would be useless. The auth endpoint itself does not enforce this — it's checked once the profile form (anketa) is filled, which is where a username becomes required to proceed.
- **Profile/onboarding**: on first login the user accepts terms and fills a form built dynamically from the taxonomy reference tables (category → role → role-specific dynamic fields → bio/goals) — never hardcoded on the frontend.
- **Multi-profile**: a user can hold multiple profiles (one per category+role pair, e.g. a developer profile and a separate language-partner profile) and switch the active one via a menu. The active profile determines the feed, available filters, what counts as "already viewed," and whose name a contact is opened under.
- **Feed has two modes**: Discovery (no filters — semantic similarity + tag/role match within the same category) and Search (filters, three-tier cascade so the screen is never empty).
- **Viewed profiles ("grey cards")**: a profile the user already opened stays in place in the ranking but gets `is_viewed = true`; the frontend renders it grey. The flag is set on opening the full card, not on scrolling past it.
- **Contact opening**: opens immediately, no mutuality. The profile owner gets a bot notification naming who opened their contact (name, role, profile link). No random-profile backfill when filters exhaust — an explicit "nobody yet" state is shown instead.

## Taxonomy

Categories/roles/tags/fields live in Postgres and are cached in Redis; the taxonomy is data-driven and expands without backend code changes. See section 3 of the TZ for the full role tables (`founder`, `product_project`, `engineering`, `design`, `marketing`, `sales_bizdev`, `finance_legal` under Tech & Product; `study_mate`, `language_buddy`, `pet_project_partner`, `mentor_mentee` under Edu & Growth).

**`role_fields` vs `tags` — deliberate split.** `role_fields` only holds single-choice *structural* attributes that gate filtering (`grade`, `project_stage`, `specialization`, language `level`, `workload`, `format`, `frequency`) — always `field_type = select`. Skills, tools, stack, domain and similar open-ended or multi-value attributes are **tags**, not `role_fields` — they're unbounded and grow from user input, which `role_fields` (a fixed reference table maintained by admins) isn't designed for. `RoleFieldType` has `multi_select`/`number`/`text`/`boolean` members for future use, but the stage 3 seed only ever emits `select`.

**Common fields are duplicated per role, not shared by reference.** Tech & Product roles each get their own `workload` + `format` rows in `role_fields`; Edu & Growth roles each get their own `frequency` + `format` rows (`language_buddy` overrides `format` with its own call/chat/in-person options instead of the generic online/offline one, since it's a better fit for that role specifically). This is plain row duplication across roles, not a shared/inherited field — `role_fields` has no such concept, and adding one wasn't justified for 11 roles. See `scripts/dev_seed_taxonomy.py` for the exact per-role field list.

**Redis cache-aside** lives inside `SqlAlchemyTaxonomyRepository` (`app/infrastructure/repositories/taxonomy.py`), not in the use case or router — callers don't know or care whether a read hit Postgres or Redis:

```python
async def get_categories(self) -> list[CategoryEntity]:
    cached = await self._cache_get("taxonomy:categories")
    if cached is not None:
        return [CategoryEntity(**item) for item in cached]
    entities = [...]  # query Postgres
    await self._cache_set("taxonomy:categories", [asdict(e) for e in entities])
    return entities
```

`_cache_get`/`_cache_set` catch `redis.exceptions.RedisError`, log a warning, and let the caller fall through to Postgres — a Redis outage degrades latency, it never breaks the request. Cached keys: `taxonomy:categories`, `taxonomy:roles:{category_id}`, `taxonomy:role_fields:{role_id}`, all `SET ... EX 21600` (6h). `tags/suggest` is deliberately **not cached** — it's already backed by the `pg_trgm` index, and the query space (arbitrary substrings × category × role × caller) doesn't cache well.

**`tag_scopes.role_id = NULL` means "scoped to the whole category"** (enforced idempotent via a `NULLS NOT DISTINCT` unique constraint on `(tag_id, category_id, role_id)`, so a repeat scope insert can't duplicate a category-wide row). The stage 3 seed only creates role-specific scopes (every TZ example tag belongs to one role), so category-wide scoping exists in the schema and in `suggest_tags`'s query logic but has no seeded example yet — the first real category-wide custom tag will be the first row to actually use it.

## Data model (`users`, taxonomy implemented; rest planned)

- **`users`** (implemented) — Telegram account: `id`, `telegram_id` (unique), `username`, profile fields, `terms_accepted_at`, `is_admin`, `is_banned`, `ban_reason`, `token_version` (bumping this instantly invalidates issued JWTs on ban), `active_profile_id`, timestamps.
- **`profiles`** (planned) — one row per (user, category, role); `user_id` FK is deliberately **not unique**, which is what enables multi-profile. Key columns: `tags TEXT[]`, `extra_attributes JSONB`, `languages VARCHAR(8)[]`, `country_code`, `timezone`, `bio`, `goals_description`, `looking_for`, `embedding vector(1536)`, `embedding_input_hash`, `embedding_model`, `embedding_status`, `status ENUM(draft|active|paused|hidden_by_admin)`. `UNIQUE (user_id, category_id, role_id)` both prevents duplicate profiles and makes double-submit safe — a repeat form submission gets a 409 with the existing profile, no need to dedupe at the nginx layer.
- **Taxonomy tables** (implemented) — `categories`, `roles(category_id)`, `role_fields(role_id, key, label, field_type, options, is_required, is_filterable, sort_order)` (drive the dynamic form/filters), `tags(slug, title, status: approved/pending/rejected, created_by_user_id, usage_count)`, `tag_scopes(tag_id, category_id, role_id)`. `tags.title` has a GIN trigram index (`ix_tags_title_trgm`, needs the `pg_trgm` extension — enabled via a `before_create` DDL event on `Base.metadata` since `create_all` doesn't create extensions) for `tags/suggest`'s substring search. See "Taxonomy" above for the `role_fields`/`tags` split and the cache.
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

## Tech stack (planned)

- Python 3.12, FastAPI, Pydantic v2.
- SQLAlchemy 2.0 (async, `asyncpg`), `PyJWT` for auth tokens. Alembic is the intended migration tool but **not wired up yet** — tables are created via `Base.metadata.create_all()` in `app/main.py`'s `lifespan` (explicitly commented as temporary; only creates missing tables, never migrates existing ones). Switch to real Alembic migrations before this matters for anything beyond the `users` table.
- PostgreSQL 16 with `pgvector` — source of truth. Local/dev image is `pgvector/pgvector:pg16` (plain `postgres` images don't have the extension).
- Redis 7 (`redis:7-alpine` in docker-compose) — taxonomy cache, feed sessions, rate limiting, background job queue.
- `arq` — background jobs (embeddings, notifications, analytics).
- PostHog — product analytics.
- `pytest` + `httpx` for tests, `ruff` + `mypy` for code quality.
- Docker Compose for local dev; nginx in front of the app in prod.

## Layered architecture

Clean Architecture variant, chosen specifically so a two-person team can work on different modules without git conflicts. Actual structure (as built, `app/`):

```
api/v1/
  routers/{auth,taxonomy}.py       <- HTTP layer, validation + delegation only, no __init__.py
  schemas/{auth,user,taxonomy}.py  <- pydantic request/response schemas, __init__.py re-exports
  mappers/{auth,user,taxonomy}.py  <- domain entity -> schema, no __init__.py
  dependencies/auth.py             <- request-scoped Depends() (e.g. get_current_user), no __init__.py
application/
  services/{telegram_init_data,jwt_service,slugify}.py  <- reusable cross-use-case services, no __init__.py. slugify.py is a plain function (no config/state to justify a class), unlike the other two
  use_cases/{auth,taxonomy}.py     <- orchestration, __init__.py re-exports
domain/
  entities/{user,auth,taxonomy}.py    <- dataclasses, __init__.py re-exports. auth.py holds the whole Telegram-auth/JWT flow (init_data payload, decoded token payload, auth result) in one file — a deliberate one-off for this small flow, not a general "always merge" rule; see "Request-scoped auth" below
  exceptions/{user,auth,taxonomy}.py  <- __init__.py re-exports, same auth.py grouping as entities
  interfaces/{user,taxonomy}.py       <- repository ABCs, __init__.py re-exports
  enums/taxonomy.py                   <- plain StrEnum members shared by entities/models/schemas (RoleFieldType, TagStatus), __init__.py re-exports
  mappers/                            <- only if a domain-to-domain mapping is actually needed
infrastructure/
  helpers/{db_helper,redis_helper}.py     <- DB/Redis client setup, flat (no nested db/ subdir)
  models/{base,user,taxonomy}.py          <- SQLAlchemy 2.0 models, __init__.py re-exports Base + models. base.py also registers a `before_create` DDL event enabling `pg_trgm`, since `create_all` doesn't create extensions
  mappers/{user_mapper,taxonomy_mapper}.py  <- SQLAlchemy model <-> domain entity, no __init__.py
  repositories/{user,taxonomy}.py         <- domain interface implementations, __init__.py re-exports. taxonomy.py additionally owns the Redis cache-aside logic for its own reads — see "Taxonomy" above
core/
  config.py                        <- Settings (pydantic-settings)
  composition/{container,di}.py    <- composition root, no __init__.py
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
    def jwt_service(self) -> JWTService: ...

    # ---------- repositories ----------
    def user_repo(self) -> SqlAlchemyUserRepository: ...
    def taxonomy_repo(self) -> SqlAlchemyTaxonomyRepository: ...  # needs both session and redis_client

    # ---------- use cases ----------
    def auth_use_case(self) -> AuthenticateTelegramUserUseCase: ...
```

`redis_client` was added to the constructor once the first Redis-backed repository (`taxonomy_repo`) showed up — before that, `Container` only ever needed a session.

`di.py` wires it into FastAPI with the classic `Depends()`-as-default-value style (not `Annotated[...]`):

```python
async def get_container(session: AsyncSession = Depends(db_helper.session_getter)) -> Container:
    return Container(session=session, redis_client=redis_helper.client)
```

Routers call it as `container.auth_use_case().execute(...)` — never construct a use case or repository directly.

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

## API (Auth and Taxonomy implemented, rest planned)

- **Auth** (implemented): `POST /api/v1/auth/telegram { init_data }` → local HMAC-SHA256 signature check (data-check-string per Telegram's algorithm, secret = `HMAC_SHA256(key=b"WebAppData", msg=bot_token)`, `initData` rejected if `auth_date` older than **300s**) → upsert user by `telegram_id` → JWT via **PyJWT**, `HS256`, **1440 min (24h)**, no refresh token (client just re-calls this endpoint with fresh `initData` on 401 elsewhere). Bot token is a dev placeholder (`APP_CONFIG__BOT__TOKEN=123`) until a real bot exists. Response: `access_token`, `token_type`, `is_new_user`, `user` (id, telegram_id, first_name, last_name, username, photo_url, is_admin, `is_banned`, `ban_reason`), `profiles: []` (stub — real list wired up once the `profiles` stage exists). A **banned user still authenticates successfully (200)** — `is_banned`/`ban_reason` are in the response so the frontend can render a ban screen instead of a bare error; this endpoint never blocks on ban or on missing username (see "User flow" for where username actually gets enforced). JWT verification on other (protected) endpoints is implemented as the reusable `Depends(get_current_user)` dependency (see "Request-scoped auth" above) — first actually consumed by the Taxonomy endpoints below.
- **Taxonomy** (implemented, all behind `Depends(get_current_user)` — no anonymous reads): `GET /taxonomy/categories`, `GET /taxonomy/categories/{id}/roles` (404 if the category doesn't exist), `GET /taxonomy/roles/{id}/fields` (404 if the role doesn't exist), `GET /taxonomy/tags/suggest?q=&category_id=&role_id=` (ILIKE substring match via the `pg_trgm` GIN index on `tags.title`; returns approved tags in scope plus the caller's own pending ones; not cached — see "Taxonomy" below), `POST /taxonomy/tags/custom { title, category_id, role_id? }` → basic anti-spam validation (length, allowed characters; a stop-word list is wired up via `TaxonomyConfig.tag_stop_words`, empty by default until curated), slug via Cyrillic transliteration, status `pending`, usable by its author immediately (the author's own pending tags show up in their own `suggest` results). Re-submitting the same title for the same category/role is safe — returns the existing tag/scope instead of erroring (mirrors the double-submit-safe pattern used for `profiles`).
- **Profiles**: `POST /profiles`, `GET /profiles/me`, `GET /profiles/{id}`, `PATCH /profiles/{id}`, `POST /profiles/{id}/activate`, `POST /profiles/{id}/pause|resume`, `DELETE /profiles/{id}`, `DELETE /users/me`.
- **Feed & contacts**: `GET /feed?mode=discovery|search&...&cursor=&limit=20`, `GET /feed/cards/{profile_id}`, `POST /feed/views`, `POST /profiles/{id}/contact`, `POST /reports`.
- **Admin**: user/profile/report lists, tag moderation queue, ban/unban, hide profile, approve/reject/merge tag, inspect why a specific recommendation was made. Gated on an admin flag in the JWT.

## Embeddings — must work without an OpenAI key

Profile text (category, role, tags, bio, goals, looking-for) is hashed; if the hash is unchanged, the embedding call is not repeated. Embeddings sit behind an `EmbeddingProvider` interface with two implementations:

- `OpenAIProvider` — `text-embedding-3-small`, 1536 dims, enabled by an API key.
- `StubProvider` — deterministic pseudo-random vector derived from the text hash; used while no OpenAI key is configured.

Switching providers is one environment variable, no code change — this lets the whole feed (including the semantic scoring term) be developed and tested before an OpenAI key exists. Provider unavailability never blocks the product: a profile is still created and ranked by tags/role, the semantic term is just temporarily skipped.

## Moderation, security, analytics

- Reports, bans (banning bumps `token_version`, instantly invalidating already-issued JWTs — the read side of this, `get_current_user`, is already implemented, see "Request-scoped auth"; the admin ban action itself that sets `is_banned`/bumps `token_version` is stage 8 work), admin profile hiding, custom-tag moderation queue (approve/reject/merge).
- Rate limiting at two levels: nginx by IP, application-level per-user in Redis (contact opens, tag creation, reports, autocomplete).
- Custom-tag anti-spam: length, allowed characters, stop-words, daily limit.
- Account deletion physically removes profiles, embeddings, and views.
- Analytics events go to PostHog in the background, never blocking the request: signup, onboarding step timings/abandonment, profile create/edit, profile switch, feed open, scroll depth, empty screen, card open (with tier + score), contact open, filters applied, tag created, report, account deletion. AI-cost accounting is out of scope for this iteration.

## Development stages

Each stage is its own `feat/...` branch and its own PR for review.

| # | Stage | Content |
|---|-------|---------|
| 1 | skeleton | ✅ Project scaffold, docker-compose (Postgres+pgvector, Redis), `.env.template`. CI checks not set up yet. |
| 2 | auth-telegram | ✅ `initData` validation, `users` table, `POST /auth/telegram` issuing JWT. ✅ Auth *dependency* (`get_current_user`) to verify JWT built — not yet consumed by any route, since no protected endpoints exist until stage 3+. |
| 3 | taxonomy | ✅ Reference tables (`categories`, `roles`, `role_fields`, `tags`, `tag_scopes`) + idempotent seed, all 5 endpoints, Redis cache-aside (categories/roles/role fields, 6h TTL, falls back to Postgres if Redis is down). |
| 4 | profiles | Profile CRUD, multi-profile, switching, form-field validation |
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
- `initData` verification: valid / malformed / expired (all implemented and covered by `scripts/dev_gen_init_data.py`).
- Access-token verification (`get_current_user`): valid / expired / malformed / revoked (`token_version` mismatch) / banned (live `is_banned` check, `403` with `ban_reason`) — all implemented in `VerifyAccessTokenUseCase`; exercised manually for now (no automated script yet). The taxonomy endpoints are the first protected routes to actually exercise this dependency over HTTP.
- Auth endpoint does not reject on missing username or on ban (see "API" — Auth). Feed-side: a user with no username can't view the feed and is excluded from other users' feeds (see "User flow"); a banned user never appears in results.
- A repeat `POST /profiles` with the same role returns 409.
- Seed script for ~100 test profiles across both categories — the feed can't be evaluated visually without this.
- Taxonomy: `categories/{id}/roles` and `roles/{id}/fields` 404 on an unknown id; `tags/custom` rejects a too-short/too-long/invalid-character title (`400`); re-submitting the same title for the same category/role doesn't create a duplicate tag or scope row; `tags/suggest` returns a caller's own pending tags but not other users' pending tags — all exercised manually for now (no automated tests yet).

## Risks and open questions

- **Cold start** — the feed is meaningless until the DB has 50–100 profiles in the relevant category; sourcing the first closed cohort by segment matters more than algorithm quality at launch.
- **200-candidate session cap** — profiles ranked below #200 in their category are never shown to a viewer in that session. A deliberate tradeoff for cheap pagination, not an accidental gap; not expected to matter at first-cohort scale, but raising the cap or adding an exploration slot for tail profiles will be needed as the audience grows.
- **Match-percentage calibration** — formula weights and cutoff thresholds will need tuning once real usage data exists.
- **Embedding stub** — validates feed mechanics but not semantic search quality; that's only visible once a real OpenAI key is wired in.
- **Contact privacy** — contacts open without reciprocity, so protection relies entirely on rate limits, logging, and moderation rather than mutual consent.
- **TODO — `is_embedded` on `role_fields`** — `extra_attributes` currently plays no role in Discovery or the scoring formula (only used for Search's `EXACT_MATCH` tier filtering). A cheap future improvement: a boolean flag on `role_fields` marking which field values get folded into the embedding input text (e.g. append `"grade: middle"` alongside `category, role, tags, bio, goals, looking-for`), giving Discovery a partial semantic signal from `extra_attributes` without hand-rolling a per-`field_type` comparison function. An explicit scoring term instead (comparing fields directly, e.g. exact-match bonus for same `grade`) was considered and rejected — `field_type`s are heterogeneous (`select`, `multi_select`, `number`, `text`), each needing its own similarity function, and it would mean reweighing the fixed formula without real usage data to calibrate against (see "Match-percentage calibration" above). Not scheduled for any stage yet; keep in mind when designing `role_fields` in stage 3 so adding this column later isn't a breaking migration.
