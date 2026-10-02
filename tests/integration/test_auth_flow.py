"""Login followed by a request to a real protected route (the taxonomy endpoints).

Unlike `test_protected_route.py` (which hand-crafts tokens on a throwaway app), these
tests get the token from `/auth/telegram` and use it on the real application.
"""

import time

from sqlalchemy import text

from scripts.dev_gen_init_data import build_init_data
from tests.fixtures.db_ops import bump_token_version, set_user_admin, set_user_banned
from tests.fixtures.init_data import BOT_TOKEN

LOGIN_URL = "/api/v1/auth/telegram"
PROTECTED_URL = "/api/v1/taxonomy/categories"


async def _login(client, telegram_id: int) -> dict:
    raw = build_init_data(BOT_TOKEN, telegram_id, int(time.time()), bad_hash=False)
    response = await client.post(LOGIN_URL, json={"init_data": raw})
    assert response.status_code == 200
    return response.json()


def _bearer(login_body: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {login_body['access_token']}"}


async def test_fresh_token_opens_a_protected_route(taxonomy_client):
    login = await _login(taxonomy_client, 940001)

    response = await taxonomy_client.get(PROTECTED_URL, headers=_bearer(login))

    assert response.status_code == 200


async def test_banned_user_logs_in_but_every_token_is_rejected_with_403(taxonomy_client, session):
    before_ban = await _login(taxonomy_client, 940002)
    await set_user_banned(session, before_ban["user"]["id"], "spam")

    after_ban = await _login(taxonomy_client, 940002)  # allowed: the frontend shows a ban screen

    assert after_ban["user"]["is_banned"] is True
    for login in (before_ban, after_ban):
        response = await taxonomy_client.get(PROTECTED_URL, headers=_bearer(login))
        assert response.status_code == 403
        assert response.json()["detail"] == "spam"


async def test_token_version_bump_revokes_old_token_but_a_new_login_works(taxonomy_client, session):
    old = await _login(taxonomy_client, 940003)
    assert (await taxonomy_client.get(PROTECTED_URL, headers=_bearer(old))).status_code == 200

    await bump_token_version(session, old["user"]["id"], 1)

    assert (await taxonomy_client.get(PROTECTED_URL, headers=_bearer(old))).status_code == 401
    fresh = await _login(taxonomy_client, 940003)
    assert (await taxonomy_client.get(PROTECTED_URL, headers=_bearer(fresh))).status_code == 200


async def test_relogin_does_not_unban_or_change_admin_flag_or_token_version(async_client, session):
    first = await _login(async_client, 940004)
    user_id = first["user"]["id"]
    await set_user_banned(session, user_id, "spam")
    await set_user_admin(session, user_id)
    await bump_token_version(session, user_id, 5)

    again = await _login(async_client, 940004)

    assert again["is_new_user"] is False
    assert again["user"]["is_banned"] is True
    assert again["user"]["ban_reason"] == "spam"
    assert again["user"]["is_admin"] is True
    row = (
        await session.execute(
            text("SELECT is_banned, ban_reason, is_admin, token_version FROM users WHERE id = :id"),
            {"id": user_id},
        )
    ).one()
    assert tuple(row) == (True, "spam", True, 5)
