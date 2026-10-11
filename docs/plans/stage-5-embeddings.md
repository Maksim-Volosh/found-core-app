# Этап 5: embeddings. Документ для исполнителя

Ветка: `feat/embeddings`. Перед началом прочитать `CLAUDE.md` и `docs/rules.md`: они обязательны. Этот документ ничего не отменяет, он уточняет этап 5.

## 0. Как работать с этим документом и что писать в PR

Это не готовое ТЗ «выполни и забудь». Решения приняты по итогам обсуждения и проверки кода. Поэтому:

1. **Любое ключевое решение можно пересмотреть, но только осознанно.** Если выбираешь другой вариант или столкнулся с проблемой, которой здесь нет, запиши в описание PR: что изменил, почему, какие альтернативы рассматривал.
2. **Описание PR отвечает не только на вопрос «что?», но и на вопрос «почему?».** Обязательные разделы PR:
   - **Что сделано**: кратко, по слоям.
   - **Ключевые решения и почему**: по таблице раздела 2. Для каждого: принято как в плане / изменено. Если изменено, то почему и что отброшено.
   - **Отклонения от плана и новые проблемы**: всё, что всплыло при реализации. Пустой раздел допустим, но тогда явно напиши «отклонений нет».
   - **Что не проверено или осталось рискованным**: честный список.
   - **Как проверить**: команды из раздела 8 и результаты, которые ты получил.
3. Если пункт плана оказался неверным, исправь план в самом PR (раздел «Отклонения»), а не только код.
4. Тесты и `alembic check` нужно **запускать самому и приложить результат**. «Работает» без прогона не принимается.

## 1. Контекст и цель

Фид (этап 6) ранжирует анкеты по формуле `0.4·cos_sim + 0.4·tag_overlap + 0.2·role_affinity`. Для `cos_sim` каждой анкете нужен **эмбеддинг**: вектор из 1536 чисел, полученный из текста category + role + tags + bio + goals. Похожие по смыслу тексты дают близкие векторы, а **cosine similarity** измеряет эту близость.

Этап 5 только готовит данные: провайдеры, хранение, фоновый пересчёт. Запросы сходства и фид относятся к этапу 6.

Требования из `CLAUDE.md` ("Embeddings"):
- Должно работать без ключа OpenAI: `StubProvider` генерирует детерминированный вектор из хеша текста.
- Смена провайдера делается переменной окружения, без правки кода.
- Недоступность провайдера не блокирует продукт: профиль создаётся и ранжируется по тегам и роли, семантика пропускается.
- Хеш входного текста: если он не изменился, провайдер повторно не вызывается.

## 2. Ключевые решения и почему

**Кто что решил.**
- **Утверждены пользователем:** 1 (Celery и понижение `redis`), 2 (отдельная таблица `profile_embeddings`), 5 (без дедупликации задач), 10 (эмбеддим все статусы), 12 (HNSW сейчас), 13 (httpx), 15 (stub в prod запрещён), 16 (приватность), 20 (без `rollback()`), 21 (отдельные БД Redis для кэша и брокера).
- **Следствия этих решений, предложены при проработке, отдельно не обсуждались:** все остальные. Исполнитель вправе их менять с обоснованием в PR.

| # | Решение | Почему | Что отброшено | Когда пересмотреть |
|---|---|---|---|---|
| 1 | Очередь: **Celery** (брокер Redis) + контейнеры `embedding_worker` и `embedding_beat`. Клиентскую библиотеку `redis` понижаем с `8.1.0` до **`6.4.0`**. Сервер Redis 7 не меняется. | Вызов OpenAI медленный и иногда падает, его нельзя делать внутри `POST /profiles`. Celery зрелый, умеет ретраи, расписание (beat), лимиты времени. Стабильный `kombu` (на нём Celery) требует `redis<6.5`, поэтому библиотеку приходится понизить; поддержка redis-py 8 есть только в предрелизе kombu 5.7.0a1 и открытом PR [celery/kombu#2639](https://github.com/celery/kombu/pull/2639). Наш код использует базовые операции (`get`, `set`, `flushdb`, `RedisError`), разницы 6.x и 8.x для него нет. | **arq**: требует `redis<6` и в режиме maintenance-only. **SAQ**: extra `redis<8.0`. **Своя очередь**: ретраи, расписание и остановку пришлось бы писать самим. **Очередь в Postgres без Redis-библиотек**: рабочая идея (статус в таблице уже есть), но выбор пользователя другой. **FastAPI BackgroundTasks**: теряет задачу при рестарте. | Когда стабильный kombu примет redis-py 8: можно вернуть `redis` на 8.x. |
| 2 | Вектор, хеш, модель и статус хранятся в отдельной таблице **`profile_embeddings`** той же БД | Вектор физически не попадает ни в один запрос профиля (`/auth/telegram`, `/profiles/me`, `get_by_id`): не нужны `deferred`, ловушка `MissingGreenlet` и тест на SQL-логи. `ProfileEntity`, мапперы, схемы API и фейк профилей **не меняются**. Sweep сканирует маленькую таблицу. | Колонки в `profiles` с `deferred=True` (рассматривался, пока не выбрали таблицу). Отдельная **база данных**: теряются транзакции и внешние ключи, удаление профиля пришлось бы синхронизировать вручную. | Если JOIN по первичному ключу в запросах фида окажется узким местом (этап 6). |
| 3 | Задачу ставим **после коммита** | Иначе воркер может взять задачу раньше, чем транзакция закрыта, и не найти профиль. Ошибка постановки не должна откатывать сохранённый профиль. | Постановка до коммита. | — |
| 4 | Постановка задачи **никогда не бросает исключений** (`IEmbeddingJobQueue.enqueue`) | Redis может быть недоступен, а профиль уже сохранён. Деградация обязана быть тихой, пользователь получает 201. | Пробросить ошибку и вернуть 5xx. | Никогда без пересмотра требования деградации. |
| 5 | Задачи не дедуплицируются | Дубликат безвреден: второй запуск видит совпавший хеш и выходит без вызова провайдера. Дедупликация по id риска не стоит: она теряла бы правку, пришедшую во время расчёта. | Блокировки и дедупликация. | Если дубликаты начнут стоить денег. |
| 6 | **Идемпотентность по хешу** `sha256(model + ":" + text)` | Не платить повторно, если текст не изменился (например, правка только таймзоны). Модель в хеше нужна, чтобы смена модели меняла хеш. | Сравнение текста целиком. | — |
| 7 | **Условная запись воркера** по `source_updated_at` (колонка таблицы `profile_embeddings`, копия `profiles.updated_at`, которую пишет use case при создании и правке) | Воркер читает профиль и несколько секунд ждёт OpenAI. Если за это время анкету изменили, безусловная запись затёрла бы статус `pending` на `ready` со старым вектором. Условие стоит **на строке самой таблицы эмбеддингов**, а не на `profiles`: тогда при конфликте двух транзакций Postgres перепроверяет условие на обновлённой версии той же строки. Условием на другой таблице так надёжно не получится. Касается **всех** записей воркера (`READY`, `FAILED`, вектор). | Условие по `profiles.updated_at` через подзапрос; блокировка строки на время вызова OpenAI. | Если появятся поля, влияющие на текст, но не меняющие `updated_at`. |
| 8 | **Sweep** (Celery beat, раз в 10 минут) | Процесс может упасть между коммитом и постановкой, Redis может лежать, ретраи могут кончиться. Sweep гарантирует, что ни одна анкета не останется без актуального вектора навсегда. | Положиться только на ретраи. | — |
| 9 | Sweep **захватывает** строки одним `UPDATE ... RETURNING` с `FOR UPDATE SKIP LOCKED` и сдвигает `updated_at` | Иначе при медленном воркере каждый sweep ставил бы те же id повторно. `SKIP LOCKED` защищает от параллельных sweep. | Простой `SELECT`. | — |
| 10 | Эмбеддим **профили в любом статусе** (active, paused, hidden_by_admin) | Эмбеддинг зависит только от текста. После `resume` анкета сразу попадает в фид с готовым вектором. | Только active. | — |
| 11 | Sweep также берёт `ready`-строки с `model` не равной текущей (и старше порога) | Иначе смена stub на OpenAI ничего не пересчитает. | Ручной скрипт (нужен только при смене формата текста). | — |
| 12 | **HNSW-индекс создаём в этапе 5** (`vector_cosine_ops`, `m=16`, `ef_construction=64`) | Решение пользователя: схема соответствует `CLAUDE.md`. Лимит HNSW в pgvector 2000 измерений, у нас 1536. | Отложить на этап 6. | Если на этапе 6 планы запросов индекс не используют (`EXPLAIN`). |
| 13 | OpenAI вызываем через **httpx напрямую** | Один `POST /v1/embeddings`. `httpx` переносим из dev-зависимостей. Легко мокать через `MockTransport`. | Официальный SDK (тяжёлый, сложнее мокать). | Если API усложнится. |
| 14 | `StubProvider`: `model = "stub-v1"`, нормализованный псевдослучайный вектор из sha256 | Позволяет разрабатывать фид без ключа. Отдельное имя модели отличает stub от OpenAI в хеше и в sweep. Stub-вектор **не имеет семантики**. | Нулевой вектор (ломает косинус). | — |
| 15 | Stub в prod **запрещён**: приложение не стартует (`provider == "stub"`, а также `openai` без ключа) | Решение пользователя: защита от тихой деградации. Следствие: первый prod-деплой возможен только с ключом OpenAI (учесть в этапе 10). | Разрешить stub с предупреждением. | Если деплой нужен раньше ключа. |
| 16 | Тексты `bio` и `goals` уходят в OpenAI | Решение пользователя: допустимо, отражаем в условиях использования (добавить в follow-up PR про `terms_accepted_at`). | Только stub. | При смене политики по данным. |
| 17 | Celery-задачи **синхронные**, внутри `asyncio.run(...)` с **новым движком БД и клиентом Redis на каждую задачу** (`NullPool`) | Celery не async. Каждый `asyncio.run` создаёт новый event loop, а пул asyncpg привязан к своему loop (тот же эффект уже описан в `tests/integration/conftest.py`), поэтому общий `db_helper.engine` в воркере ломается со второй задачи. Prefork-воркер к тому же форкается после импорта модулей. | Общий движок. | Если задач станет много и накладные расходы на соединение вырастут. |
| 18 | Постановка из API: `celery_app.send_task` в потоке (`asyncio.to_thread`) под `asyncio.wait_for`, `retry=False`, короткие таймауты брокера | `send_task` синхронный и при недоступном Redis по умолчанию долго пытается подключиться. Без ограничений запрос `POST /profiles` повис бы. | Вызов прямо из event loop. | — |
| 19 | `acks_late=True`, `worker_prefetch_multiplier=1`, `visibility_timeout` больше лимита задачи | Если воркер упал посреди задачи, сообщение вернётся в очередь; повторный запуск безопасен благодаря хешу и условной записи. Prefetch 1 не даёт одному воркеру копить задачи. Иначе Redis-транспорт повторно выдаст ещё выполняющуюся задачу. | Значения по умолчанию. | — |
| 20 | `IUnitOfWork.rollback()` **не добавляем** | `CLAUDE.md` откладывал его до первой долгоживущей сессии и называл воркер примером. Воркер открывает новую сессию на каждую задачу, закрытие сессии откатывает всё так же, как request-scoped `session_getter`. | `rollback()` в интерфейсе. | Если появится долгоживущая сессия. Абзац в `CLAUDE.md` обновить. |
| 21 | Один сервер Redis, но **разные логические БД**: кэш приложения в DB 0, брокер Celery в DB 2 (`EmbeddingConfig.broker_url`), тесты в DB 1 (кэш) и DB 3 (брокер) | Очередь и кэш не мешают друг другу: `FLUSHDB` кэша не стирает задачи, а ключи Celery не смешиваются с `taxonomy:*`. DB 1 под брокер брать **нельзя**: интеграционные тесты делают `flushdb()` в DB 1 и стёрли бы очередь разработки. DB-изоляция логическая: общие память, политика вытеснения и `FLUSHALL` остаются общими. | Брокер в той же БД, что и кэш. Отдельный сервер Redis (избыточно на этом этапе). | Если нагрузка или политика вытеснения кэша начнут мешать очереди: вынести брокер на отдельный сервер, поменяв только `broker_url`. |

## 3. Технические факты, которые нужно учесть

Предварительных проверок не требуется. Стек выбран, спорных вопросов не осталось:

1. **Очередь: Celery. Клиент `redis` понижается до 6.4.0** (сервер Redis 7 не меняется). Это делается в PR этапа 5: `requirements.txt` в репозитории пока содержит `redis==8.1.0`. Локально проверено, что полный набор тестов проходит на 6.4.0; в репозиторий это не коммитилось.
2. **Вектор через SQLAlchemy и asyncpg работает без регистрации кодека.** Listener `register_vector` для SQLAlchemy над asyncpg **вреден**: кодек ждёт список, а тип `VECTOR` передаёт строку, вставка падает с `expected list or ndarray`. В `db_helper` его не добавлять.
3. **Условная запись воркера** по `source_updated_at` на строке `profile_embeddings` корректно проигрывает гонку с параллельной правкой (решение 7).
4. **HNSW** с `vector_cosine_ops` создаётся на 1536 измерениях и используется запросом `<=>`.
5. **Alembic.** HNSW-индекс в миграции писать вручную через `op.create_index(..., postgresql_using="hnsw", postgresql_with=..., postgresql_ops=...)`: автогенерат может потерять класс оператора (известный случай [pgvector-python #118](https://github.com/pgvector/pgvector-python/issues/118)). В файл ревизии добавить `import pgvector.sqlalchemy`.

Пункты 2–5 подтверждены отдельными экспериментами (12 проверок, все прошли). Сами эксперименты в репозиторий **не входят**: их сценарии исполнитель покрывает обычными тестами репозитория (раздел 7).

## 4. Архитектура

```
API (use case)                       Redis (брокер)         Worker (Celery, отдельный контейнер)
create / update -> COMMIT -> send_task -------> очередь ---> embed_profile -> asyncio.run(EmbedProfileUseCase)
                                                                  -> провайдер -> UPDATE profile_embeddings
Beat (отдельный контейнер, один экземпляр): каждые 10 минут sweep -> claim -> send_task
```

- Воркер читает свежие данные из БД по `profile_id`, других аргументов у задачи нет.
- Фид использует вектор, только если `embedding IS NOT NULL` и `model` равна текущей. Статус нужен воркеру и операторам.
- Потерянная задача исправляется не позже чем через порог sweep плюс период beat (около 15 минут).
- Переименование категории, роли или тега в таксономии не пересчитывает эмбеддинги. Админ-реиндекс не входит в этап 5.

### Таблица `profile_embeddings`

| Колонка | Тип | Смысл |
|---|---|---|
| `profile_id` | BIGINT, PK, FK `profiles.id` ON DELETE CASCADE | Одна строка на профиль. |
| `embedding` | `vector(1536)`, NULL | Вектор. |
| `input_hash` | `varchar(64)`, NULL | Хеш входного текста. Заполнен тогда и только тогда, когда вектор есть. |
| `model` | `varchar(64)`, NULL | Модель, которой посчитан вектор. |
| `status` | enum `embedding_status`, NOT NULL, default `pending` | `pending`, `ready`, `failed`. |
| `source_updated_at` | timestamptz, NOT NULL | Копия `profiles.updated_at` на момент пометки `pending` (защита от гонки, решение 7). |
| `updated_at` | timestamptz, NOT NULL | Последнее изменение строки (в том числе claim); по нему работает sweep. |

Строку создаёт `CreateProfileUseCase` в той же транзакции, что и профиль. Миграция заполняет её для уже существующих профилей (`pending`). Это единственное место, где ревизия содержит данные: правило «только схема» из `docs/rules.md` здесь нарушается осознанно, объясни это в PR.

### Статусы и сценарии

| Ситуация | Что происходит |
|---|---|
| Создан профиль | В той же транзакции строка `pending`; после коммита задача. Воркер считает вектор и ставит `ready`. |
| Правка анкеты | `mark_pending` (upsert со свежим `source_updated_at`) до коммита, после коммита задача. Старый вектор остаётся годным. Если текст не менялся (только таймзона), хеш совпадает, провайдер не вызывается, статус возвращается в `ready`. |
| OpenAI вернул 429 или 5xx, таймаут | Celery `retry` с растущей паузой. На последней попытке статус `failed`. |
| Прочие 4xx (например, 401) или неверная длина вектора | Без повторов, статус `failed`. |
| Анкету изменили, пока воркер считал | Условная запись вернула `False`, задача повторяется через ~1 с. Если повторы кончились, строка остаётся `pending` и её подберёт sweep. |
| Redis лёг в момент создания | Профиль сохранён (201), задачи нет, статус `pending`. Sweep подберёт. |
| Воркер упал | Сообщение вернётся в очередь (`acks_late`). Повторный запуск безопасен. |
| Строки эмбеддинга нет (аномалия) | Воркер создаёт её со статусом `pending`, **сразу коммитит** и продолжает. Если упадёт после этого, строка уже есть, и её подберёт sweep. |
| Профиль удалён, пока задача ждала | Воркер не находит профиль и тихо выходит. Строка эмбеддинга удалена каскадом. |
| Смена провайдера или модели | Sweep берёт `ready`-строки с чужой `model` и пересчитывает. |

## 5. Реализация по слоям

### Domain
- `domain/constants.py`: `EMBEDDING_DIMENSIONS = 1536` (в конфиг не выносится: на него завязан тип колонки).
- `domain/enums/profile.py`: `EmbeddingStatus(StrEnum)`, экспорт в `enums/__init__.py`.
- `domain/entities/profile_embedding.py`: `ProfileEmbeddingEntity` (`profile_id`, `input_hash`, `model`, `status`, `source_updated_at`, `updated_at`). **Вектор в сущность не кладём.** `ProfileEntity` и `NewProfileEntity` не меняются.
- `domain/interfaces/embedding_provider.py`: `IEmbeddingProvider` (`model: str`, `async embed(text) -> list[float]`).
- `domain/interfaces/embedding_queue.py`: `IEmbeddingJobQueue.enqueue(profile_id) -> None`, не бросает исключений.
- `domain/interfaces/profile_embedding.py`, `IProfileEmbeddingRepository` (`bool` — результат операции, `rowcount == 1`):
  - `get(profile_id) -> ProfileEmbeddingEntity | None`;
  - `mark_pending(profile_id, source_updated_at) -> None` (`INSERT ... ON CONFLICT (profile_id) DO UPDATE`);
  - `save(profile_id, embedding, input_hash, model, expected_source_updated_at) -> bool` (ставит `ready`);
  - `set_outcome(profile_id, status, expected_source_updated_at) -> bool` (`READY` или `FAILED`);
  - `claim_stale(pending_before, failed_before, model, limit) -> list[int]`: один `UPDATE ... SET updated_at = now() WHERE profile_id IN (SELECT ... FOR UPDATE SKIP LOCKED LIMIT n) RETURNING profile_id`. Отбор: `pending` старше `pending_before`, `failed` старше `failed_before`, `ready` с `model <> :model` старше `pending_before`.
- `domain/exceptions/embedding.py` (шаблон из `docs/rules.md`): `EmbeddingProviderUnavailableError` (ретраится), `EmbeddingRejectedError` (не ретраится), `ProfileChangedDuringEmbeddingError` (ретраится).
- `domain/services/embedding_input_builder.py`: `build_embedding_input(category_title, role_title, tag_titles, bio, goals) -> str` (теги отсортированы по названию), `compute_input_hash(model, text) -> str`.

### Application
- `use_cases/embedding.py`:
  - `EmbedProfileUseCase.execute(profile_id, is_last_attempt)`:
    1. Прочитать профиль; нет профиля: тихий выход. Прочитать состояние эмбеддинга; нет строки (аномалия: в норме её создаёт `CreateProfileUseCase`, а миграция заполняет для старых анкет): `mark_pending`, **сразу `commit()`** и продолжить. Иначе при падении воркера до коммита вставка откатится, а sweep ищет только в `profile_embeddings` и такую анкету не найдёт. Это единственное место, где use case коммитит дважды; объясни исключение из правила «один коммит» в PR.
    2. Загрузить category и role (`ITaxonomyRepository.get_category_by_id`, `get_role_by_id`), собрать текст и хеш. Ожидаемое значение для условной записи: `profile.updated_at`.
    3. `input_hash` совпал и `model` совпала: вектор актуален. Если статус `ready`, выход; иначе `set_outcome(READY, expected)`, при `False` бросить `ProfileChangedDuringEmbeddingError`.
    4. `provider.embed(text)`. `Unavailable`: если `is_last_attempt`, то `set_outcome(FAILED, expected)` + коммит, иначе пробросить. `Rejected`: `FAILED` + коммит.
    5. `save(..., expected_source_updated_at=profile.updated_at)`: `False` значит `ProfileChangedDuringEmbeddingError`, `True` значит коммит.
  - `SweepStaleEmbeddingsUseCase.execute()`: `claim_stale(...)`, затем `commit()` (claim виден до постановки), затем `enqueue` для каждого id.
- `use_cases/profile.py`:
  - `CreateProfileUseCase`: `mark_pending(profile.id, profile.updated_at)` до коммита и `enqueue(profile.id)` после.
  - `UpdateProfileUseCase`: `mark_pending(profile_id, updated.updated_at)` до коммита и `enqueue` после.
  - `Pause`, `Resume`, `Activate`, `Delete` не меняются.

### Infrastructure
- `models/profile_embedding.py` (`ProfileEmbeddingModel`, экспорт в `models/__init__.py`): колонки по таблице раздела 4. Индексы: `ix_profile_embeddings_embedding_hnsw` (`postgresql_using="hnsw"`, `postgresql_ops={"embedding": "vector_cosine_ops"}`, `postgresql_with={"m": 16, "ef_construction": 64}`) и частичный `ix_profile_embeddings_status_updated_at` по `(status, updated_at)` с `WHERE status <> 'ready'`.
- `models/base.py`: второй `DDL("CREATE EXTENSION IF NOT EXISTS vector")` в `before_create`, иначе `create_all` в тестах упадёт.
- Миграция (`down_revision='ca773380d102'`): `CREATE EXTENSION IF NOT EXISTS vector`, enum, таблица, индексы (HNSW вручную), `INSERT ... SELECT` для существующих профилей, `import pgvector.sqlalchemy`. `downgrade()`: индексы, таблица, `DROP TYPE embedding_status`; расширение не дропаем (как `pg_trgm`). Миграцию проверить вручную (`docs/rules.md`, «Migrations»).
- `repositories/sqlalchemy_profile_embedding.py`: реализация интерфейса, один источник данных, без коммитов.
- `providers/stub_embedding.py` и `providers/openai_embedding.py`. OpenAI-провайдер открывает `httpx.AsyncClient` на вызов, конструктор принимает `transport` (в проде `None`, в тестах `MockTransport`). Маппинг ошибок: таймаут, сеть, 429, 5xx дают `Unavailable`; прочие 4xx и неверная длина вектора дают `Rejected`.
- `queues/celery_embedding_queue.py`: `CeleryEmbeddingJobQueue.enqueue` (решения 4 и 18): `asyncio.wait_for(asyncio.to_thread(celery_app.send_task, TASK_NAME, args=[profile_id], retry=False), timeout)`, ловит любые исключения.
- `app/worker/celery_app.py`: `Celery(...)` из `EmbeddingConfig.broker_url`, `task_acks_late`, `worker_prefetch_multiplier=1`, `task_ignore_result`, лимиты времени, `broker_connection_timeout` и `broker_transport_options` (`socket_connect_timeout`, `socket_timeout`, `visibility_timeout`), `beat_schedule` с `sweep_stale_embeddings` раз в `sweep_interval_seconds`.
- `app/worker/tasks.py`:
  - `embed_profile` (`bind=True`): синхронная обёртка. `asyncio.run` выполняет async-ядро, которое на каждую задачу создаёт `create_async_engine(..., poolclass=NullPool)` и клиент Redis, строит `Container` и вызывает use case, затем освобождает ресурсы. `Unavailable` и `ProfileChanged` превращаются в `self.retry(countdown=...)`; `is_last_attempt = self.request.retries >= max_retries`.
  - `sweep_stale_embeddings`: то же для `SweepStaleEmbeddingsUseCase`.
  - **Async-ядро вынести отдельной функцией**, чтобы тестировать его напрямую.

### Config и окружение
- `core/config.py`, `EmbeddingConfig` (plain `BaseModel`): `provider: Literal["stub","openai"] = "stub"`, `broker_url: str` (обязательное, без значения по умолчанию и без фолбэка на `redis.url`: так брокер нельзя случайно оставить в БД кэша), `openai_api_key: SecretStr | None = None`, `model = "text-embedding-3-small"`, `openai_base_url`, `request_timeout_seconds`, `enqueue_timeout_seconds`, `queue_name`, `task_max_retries`, `task_time_limit_seconds`, `retry_base_delay_seconds`, `sweep_interval_seconds` (600), `sweep_pending_after_seconds` (300), `sweep_failed_after_seconds` (3600), `sweep_batch_size`.
- `Settings._refuse_insecure_production_settings`: prod со `stub`, с `openai` без ключа, а также с `broker_url`, указывающим на ту же БД Redis, что и `redis.url`, отказывает в запуске. Тесты в `test_settings.py`.
- `container.py`: новые фабрики `profile_embedding_repo()`, `embedding_provider()`, `embedding_queue()`, `embed_profile_use_case()`, `sweep_stale_embeddings_use_case()`. `create_profile_use_case` и `update_profile_use_case` получают репозиторий эмбеддингов и очередь. Поскольку Celery-приложение это модульный синглтон на потоках (kombu синхронный), в `Container` и `di.py` менять параметры конструктора не нужно.
- `.env.template` (секция Embeddings, `APP_CONFIG__EMBEDDING__BROKER_URL` на DB 2 рядом с `APP_CONFIG__REDIS__URL` на DB 0), `.env.test` (`provider=stub`, брокер на **DB 3**; кэш тестов остаётся в DB 1).
- `requirements.txt`: **`redis==6.4.0`** (было `8.1.0`), `celery[redis]` и транзитивные пакеты закрепить через `==`, `pgvector==0.5.1`, `httpx` (перенос из dev).
- `docker-compose.yaml`: сервисы `embedding_worker` (`celery -A app.worker.celery_app worker -Q <queue> -c 2 -l info`) и `embedding_beat` (`celery -A app.worker.celery_app beat -l info --schedule /tmp/celerybeat-schedule`; **ровно один экземпляр**, образ работает от non-root). Оба: тот же образ, `env_file: .env`, `depends_on: [db, redis]`, `restart: unless-stopped`.

## 6. Контракт для этапа 6

- Использовать вектор можно, только если `embedding IS NOT NULL` и `model` равна текущей. Вектора stub и OpenAI несравнимы; во время переиндексации анкеты со старой моделью ранжируются без семантической части.
- Смена провайдера или модели переиндексируется sweep автоматически. Смена формата `build_embedding_input` меняет хеш, но sweep её не видит: нужен отдельный скрипт (не входит в этап 5).
- Seed на ~100 профилей (нужен до этапа 6) должен создавать строки `profile_embeddings` и запускать эмбеддинг.

## 7. Тесты

Правила из `docs/rules.md`, раздел 4, действуют полностью.

**Unit (`tests/unit`, без БД и Redis)**
- `test_embedding_input_builder`: стабильность при перестановке тегов, разный хеш при смене модели.
- `test_stub_embedding_provider`: детерминизм, длина 1536, единичная норма.
- `test_openai_embedding_provider` на `MockTransport`: 200, 429, 5xx, таймаут, 401, неверная длина.
- `test_embed_profile_use_case` с фейками: no-op при совпадении хеша; смена текста вызывает провайдера один раз; `Unavailable` на последней попытке даёт `FAILED`; `Rejected` даёт `FAILED`; удалённый профиль; отсутствующая строка эмбеддинга; **изменение между чтением и записью** (`save` вернул `False`, статус остаётся `pending`).
- `test_sweep_use_case`: выбор `pending`, `failed` и анкет с чужой моделью; claim перед постановкой.
- Расширить `test_profile_use_cases.py`: `mark_pending` и enqueue при create и update; нет enqueue при 409 и ошибке валидации; ошибка очереди не ломает ответ; `commits == 1`. Обновить позиционные конструкторы в `Env`.
- `test_settings.py`: prod со stub, prod с openai без ключа.
- Фейки в `tests/fixtures/`: `FakeEmbeddingProvider`, `FakeEmbeddingQueue`, `FakeProfileEmbeddingRepository` (копии при чтении, **условные записи**, как настоящий). `FakeProfileRepository` и `make_profile_entity` не меняются.

**Integration (`tests/integration`)**
- `test_profile_embedding_repository.py`: round-trip вектора на 1536 (без `register_vector`, см. раздел 3); `NULL`-вектор; чужая размерность отвергается Postgres; `save` и `set_outcome` возвращают `False` при чужом `source_updated_at`; **гонка**: незакоммиченный `mark_pending` держит блокировку строки, параллельный `save` ждёт её и после коммита ничего не пишет (статус остаётся `pending`); два параллельных `claim_stale` не отдают один id дважды; каскадное удаление; уникальность строки на профиль.
- `test_taxonomy_schema.py`: расширение `vector`, тип колонки, индексы; HNSW создаётся на 1536 измерениях, а запрос `ORDER BY embedding <=> ... LIMIT n` использует его (под `SET LOCAL enable_seqscan = off`) и первым возвращает идентичный вектор.
- `test_profile_endpoints.py`: в ответах нет полей embedding; `POST /profiles` отдаёт 201 при недоступном брокере; после создания строка эмбеддинга существует.
- `test_celery_embedding_queue.py`: `enqueue` кладёт сообщение в Redis (проверить `LLEN`); недоступный брокер не бросает исключение и возвращается быстрее таймаута.
- `test_embedding_task.py`: async-ядро end-to-end на настоящих Postgres и Redis с `FakeEmbeddingProvider`; тонкая sync-обёртка в eager-режиме (обычный sync-тест, без запущенного event loop).
- В `tests/integration/conftest.py` добавить `profile_embeddings` в `TRUNCATE`, а охранную проверку (отказ при Redis DB 0) распространить на `broker_url` (брокер тестов не должен быть DB 0 и DB 2); фикстура очищает БД брокера перед каждым тестом.

## 8. Как проверить (прикладывай результаты к PR)

```
docker compose up -d db redis
docker compose build && docker compose up -d
docker compose exec found_core_mini_app alembic upgrade head
docker compose exec found_core_mini_app alembic check      # ожидается: No new upgrade operations detected
docker compose exec found_core_mini_app pytest -v --cov=app --cov-report=term-missing
docker compose exec found_core_mini_app python scripts/dev_seed_taxonomy.py
```

Ручной сценарий:
1. Получить `initData` через `scripts/dev_gen_init_data.py`, получить токен, создать профиль через `POST /api/v1/profiles`.
2. В psql: `SELECT profile_id, status, model, vector_dims(embedding) FROM profile_embeddings;`. Ожидание: через 1–2 секунды `ready`, `stub-v1`, 1536.
3. `PUT` с изменением только таймзоны: хеш не меняется, провайдер не вызывается (лог воркера).
4. `PUT` с новым bio: хеш меняется, вектор пересчитан.
5. `docker compose stop redis`, затем `POST /profiles`: ответ 201 за долю секунды, статус `pending`. После `docker compose start redis` в течение 10–15 минут sweep переводит строку в `ready`.
6. `docker compose stop embedding_worker`, создать профиль, запустить воркер: задача выполняется.
7. Сменить `APP_CONFIG__EMBEDDING__PROVIDER` и перезапустить воркер и beat: sweep пересчитывает анкеты с другой моделью.

## 9. Документация

Обновить `CLAUDE.md`: таблица этапов, «Repository state», «Data model» (таблица `profile_embeddings` вместо «planned `profiles` columns»), «Tech stack» (Celery, `pgvector`, `httpx`, `redis` 6.4.0 и почему), «Embeddings», абзац про `rollback()` (решение 20), раздел про Redis (карта БД: 0 кэш, 1 тесты, 2 брокер Celery, 3 брокер тестов).

## 10. Порядок работы (коммиты)

1. Зависимости (понижение `redis` до 6.4.0, Celery, `pgvector`), конфиг; сразу прогнать полный набор тестов после понижения.
2. Domain и фейки.
3. Модель, миграция, репозиторий.
4. Провайдеры.
5. Use cases и контейнер.
6. Очередь, Celery-приложение, задачи, docker-compose.
7. Integration-тесты и `CLAUDE.md`.

## 11. Не входит в этап 5

Follow-up PR после профилей (username-gate, `terms_accepted_at`, `tags/suggest` по тегам профилей: записаны в `CLAUDE.md`, делаются **после** этапа 5), seed на ~100 профилей, запросы сходства и фид (этап 6), админский реиндекс при переименовании таксономии и при смене формата входного текста, `is_embedded` для `role_fields`.
