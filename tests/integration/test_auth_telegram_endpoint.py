import asyncio
import time

import pytest
from sqlalchemy import text

from app.infrastructure.repositories.user import SqlAlchemyUserRepository
from scripts.dev_gen_init_data import build_init_data
from tests.fixtures.db_ops import set_user_banned
from tests.fixtures.init_data import (
    BOT_TOKEN,
    bad_hash_init_data,
    expired_init_data,
    init_data_missing_field,
    init_data_with_duplicate_hash,
    init_data_with_hash_value,
    init_data_with_user_payload,
    init_data_with_username,
)

URL = "/api/v1/auth/telegram"


async def test_new_user_gets_200_and_is_persisted(async_client, session):
    raw = build_init_data(BOT_TOKEN, 700001, int(time.time()), bad_hash=False)

    response = await async_client.post(URL, json={"init_data": raw})

    assert response.status_code == 200
    body = response.json()
    assert body["is_new_user"] is True
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["profiles"] == []
    assert body["user"]["telegram_id"] == 700001

    repo = SqlAlchemyUserRepository(session)
    assert await repo.get_by_telegram_id(700001) is not None


async def test_replaying_same_payload_is_not_a_new_user(async_client):
    raw = build_init_data(BOT_TOKEN, 700002, int(time.time()), bad_hash=False)

    first = await async_client.post(URL, json={"init_data": raw})
    second = await async_client.post(URL, json={"init_data": raw})

    assert first.json()["is_new_user"] is True
    assert second.json()["is_new_user"] is False
    assert first.json()["user"]["id"] == second.json()["user"]["id"]


async def test_different_telegram_id_creates_a_distinct_user(async_client):
    raw_a = build_init_data(BOT_TOKEN, 700003, int(time.time()), bad_hash=False)
    raw_b = build_init_data(BOT_TOKEN, 700004, int(time.time()), bad_hash=False)

    resp_a = await async_client.post(URL, json={"init_data": raw_a})
    resp_b = await async_client.post(URL, json={"init_data": raw_b})

    assert resp_a.json()["user"]["id"] != resp_b.json()["user"]["id"]


async def test_relogin_reflects_updated_username(async_client):
    first = await async_client.post(URL, json={"init_data": init_data_with_username(700005, "name_one")})
    second = await async_client.post(URL, json={"init_data": init_data_with_username(700005, "name_two")})

    assert first.json()["user"]["username"] == "name_one"
    assert second.json()["user"]["username"] == "name_two"
    assert first.json()["user"]["id"] == second.json()["user"]["id"]


async def test_tampered_hash_returns_401(async_client):
    response = await async_client.post(URL, json={"init_data": bad_hash_init_data(700006)})

    assert response.status_code == 401
    assert "signature" in response.json()["detail"].lower()


async def test_expired_auth_date_returns_401(async_client):
    response = await async_client.post(URL, json={"init_data": expired_init_data(700007)})

    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


async def test_incomplete_but_signed_payload_returns_400(async_client):
    response = await async_client.post(URL, json={"init_data": init_data_missing_field(700008, "user")})

    assert response.status_code == 400


async def test_empty_init_data_field_returns_422(async_client):
    response = await async_client.post(URL, json={"init_data": ""})

    assert response.status_code == 422


async def test_missing_init_data_key_returns_422(async_client):
    response = await async_client.post(URL, json={})

    assert response.status_code == 422


async def test_banned_user_still_authenticates_with_fresh_token(async_client, session):
    telegram_id = 700009
    first = await async_client.post(
        URL, json={"init_data": build_init_data(BOT_TOKEN, telegram_id, int(time.time()), bad_hash=False)}
    )
    user_id = first.json()["user"]["id"]

    await set_user_banned(session, user_id, "spam")

    response = await async_client.post(
        URL, json={"init_data": build_init_data(BOT_TOKEN, telegram_id, int(time.time()), bad_hash=False)}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["is_banned"] is True
    assert body["user"]["ban_reason"] == "spam"
    assert body["access_token"]


async def test_five_parallel_first_logins_create_one_user(async_client, session):
    # Used to fail: every request saw "no such user", then all but one hit the unique telegram_id.
    telegram_id = 700011
    raws = [build_init_data(BOT_TOKEN, telegram_id, int(time.time()), bad_hash=False) for _ in range(5)]

    responses = await asyncio.gather(*[async_client.post(URL, json={"init_data": raw}) for raw in raws])

    assert [r.status_code for r in responses] == [200] * 5
    assert sum(r.json()["is_new_user"] for r in responses) == 1
    assert len({r.json()["user"]["id"] for r in responses}) == 1
    assert (await session.execute(text("SELECT count(*) FROM users"))).scalar_one() == 1


@pytest.mark.parametrize("hash_value", ["é", "\u202E", "abc"])
async def test_wrong_or_non_ascii_hash_returns_401_not_500(async_client, hash_value):
    response = await async_client.post(URL, json={"init_data": init_data_with_hash_value(700012, hash_value)})

    assert response.status_code == 401


async def test_hash_sent_twice_returns_400(async_client):
    response = await async_client.post(URL, json={"init_data": init_data_with_duplicate_hash(700013)})

    assert response.status_code == 400


async def test_auth_date_far_in_the_future_returns_400(async_client):
    raw = init_data_with_user_payload({"id": 700014, "first_name": "Test"}, auth_date=str(int(time.time()) + 3600))

    response = await async_client.post(URL, json={"init_data": raw})

    assert response.status_code == 400


@pytest.mark.parametrize(
    "user",
    [
        {"id": "700015", "first_name": "Test"},
        {"id": 0, "first_name": "Test"},
        {"id": 2**63, "first_name": "Test"},
        {"id": 700015, "first_name": 5},
        {"id": 700015, "first_name": "a" * 256},
        {"id": 700015, "first_name": "bad\x00name"},
        [],
    ],
)
async def test_signed_but_invalid_user_returns_400_not_500(async_client, session, user):
    response = await async_client.post(URL, json={"init_data": init_data_with_user_payload(user)})

    assert response.status_code == 400
    assert (await session.execute(text("SELECT count(*) FROM users"))).scalar_one() == 0


async def test_oversized_init_data_returns_422(async_client):
    response = await async_client.post(URL, json={"init_data": "a=" + "b" * 9000})

    assert response.status_code == 422


async def test_response_never_leaks_token_version(async_client):
    raw = build_init_data(BOT_TOKEN, 700010, int(time.time()), bad_hash=False)

    response = await async_client.post(URL, json={"init_data": raw})

    assert "token_version" not in response.json()["user"]
