import asyncio
import time

import pytest
from sqlalchemy import text

from app.domain.constants import MAX_INT64
from app.domain.enums import TagStatus
from scripts.dev_gen_init_data import build_init_data
from tests.fixtures.auth import create_user_with_headers
from tests.fixtures.init_data import BOT_TOKEN
from tests.fixtures.taxonomy_data import add_tag

BASE = "/api/v1/profiles"


@pytest.fixture
async def user_a(session):
    return await create_user_with_headers(session, telegram_id=940001)


@pytest.fixture
async def user_b(session):
    return await create_user_with_headers(session, telegram_id=940002)


@pytest.fixture
async def tag_ids(session, taxonomy_data):
    """Six approved tags scoped to the engineering role."""
    t = taxonomy_data
    scope = [(t.tech_category_id, t.engineering_role_id)]
    return [(await add_tag(session, f"tag-{i}", scopes=scope)).id for i in range(6)]


def _payload(taxonomy_data, available_tag_ids, **overrides) -> dict:
    payload = {
        "category_id": taxonomy_data.tech_category_id,
        "role_id": taxonomy_data.engineering_role_id,
        "country_code": "DE",
        "timezone": "Europe/Berlin",
        "bio": "b" * 200,
        "goals_description": "g" * 200,
        "tag_ids": available_tag_ids[:5],
        "extra_attributes": {"grade": "junior"},
    }
    payload.update(overrides)
    return payload


def _update_payload(taxonomy_data, available_tag_ids, **overrides) -> dict:
    payload = _payload(taxonomy_data, available_tag_ids, **overrides)
    del payload["category_id"], payload["role_id"]
    return payload


async def _create(client, headers, taxonomy_data, available_tag_ids, **overrides):
    response = await client.post(BASE, json=_payload(taxonomy_data, available_tag_ids, **overrides), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


async def _my_profiles(client, headers) -> list[dict]:
    response = await client.get(f"{BASE}/me", headers=headers)
    assert response.status_code == 200
    return response.json()


class TestAuthIsRequired:
    @pytest.mark.parametrize(
        "method, path",
        [
            ("GET", "/form-config"),
            ("GET", "/me"),
            ("POST", ""),
            ("GET", "/1"),
            ("PUT", "/1"),
            ("POST", "/1/activate"),
            ("POST", "/1/pause"),
            ("POST", "/1/resume"),
            ("DELETE", "/1"),
        ],
    )
    async def test_missing_token_returns_401(self, taxonomy_client, method, path):
        response = await taxonomy_client.request(method, f"{BASE}{path}")

        assert response.status_code == 401


class TestFormConfig:
    async def test_returns_limits_and_countries_with_timezones(self, taxonomy_client, user_a):
        _, headers = user_a

        response = await taxonomy_client.get(f"{BASE}/form-config", headers=headers)

        assert response.status_code == 200
        body = response.json()
        assert body["bio"] == {"min_length": 200, "max_length": 2000}
        assert body["goals"] == {"min_length": 200, "max_length": 2000}
        assert body["tags"] == {"min_count": 5, "max_count": 15}
        germany = next(c for c in body["countries"] if c["code"] == "DE")
        assert germany["name"] == "Germany"
        assert "Europe/Berlin" in [tz["id"] for tz in germany["timezones"]]


class TestCreateProfile:
    async def test_first_profile_is_created_active_with_tags(self, taxonomy_client, taxonomy_data, tag_ids, user_a):
        user, headers = user_a

        profile = await _create(taxonomy_client, headers, taxonomy_data, tag_ids)

        assert profile["status"] == "active"
        assert profile["is_active"] is True
        assert [t["id"] for t in profile["tags"]] == tag_ids[:5]
        assert profile["extra_attributes"] == {"grade": "junior"}
        assert "user_id" not in profile

    async def test_tag_usage_counts_creations_and_survives_deletion(
        self, taxonomy_client, taxonomy_data, tag_ids, session, user_a
    ):
        _, headers = user_a

        profile = await _create(taxonomy_client, headers, taxonomy_data, tag_ids)

        async def usage() -> dict[int, int]:
            rows = await session.execute(text("SELECT id, usage_count FROM tags"))
            return dict(rows.all())

        counts = await usage()
        assert [counts[i] for i in tag_ids[:5]] == [1] * 5
        assert all(counts[i] == 0 for i in tag_ids[5:])

        await taxonomy_client.delete(f"/api/v1/profiles/{profile['id']}", headers=headers)
        await session.rollback()

        assert await usage() == counts

    async def test_second_profile_in_another_role_does_not_become_active(
        self, taxonomy_client, taxonomy_data, tag_ids, session, user_a
    ):
        _, headers = user_a
        t = taxonomy_data
        first = await _create(taxonomy_client, headers, t, tag_ids)
        for tag_id in tag_ids:
            await session.execute(
                text("INSERT INTO tag_scopes (tag_id, category_id, role_id) VALUES (:t, :c, :r)"),
                {"t": tag_id, "c": t.tech_category_id, "r": t.design_role_id},
            )
        await session.commit()

        second = await _create(
            taxonomy_client, headers, t, tag_ids, role_id=t.design_role_id, extra_attributes={}
        )

        assert second["is_active"] is False
        profiles = await _my_profiles(taxonomy_client, headers)
        assert [(p["id"], p["is_active"]) for p in profiles] == [(first["id"], True), (second["id"], False)]

    async def test_repeat_for_the_same_role_returns_409_with_the_existing_profile(
        self, taxonomy_client, taxonomy_data, tag_ids, user_a
    ):
        _, headers = user_a
        first = await _create(taxonomy_client, headers, taxonomy_data, tag_ids)

        response = await taxonomy_client.post(BASE, json=_payload(taxonomy_data, tag_ids), headers=headers)

        assert response.status_code == 409
        detail = response.json()["detail"]
        assert detail["profile"]["id"] == first["id"]
        assert detail["message"]

    async def test_parallel_creates_produce_one_profile(
        self, taxonomy_client, taxonomy_data, tag_ids, session, user_a
    ):
        _, headers = user_a
        payload = _payload(taxonomy_data, tag_ids)

        responses = await asyncio.gather(
            *[taxonomy_client.post(BASE, json=payload, headers=headers) for _ in range(5)]
        )

        assert sorted(r.status_code for r in responses) == [201, 409, 409, 409, 409]
        assert (await session.execute(text("SELECT count(*) FROM profiles"))).scalar_one() == 1
        assert (await session.execute(text("SELECT count(*) FROM profile_tags"))).scalar_one() == 5

    async def test_unknown_category_and_role_of_another_category_return_404(
        self, taxonomy_client, taxonomy_data, tag_ids, user_a
    ):
        _, headers = user_a
        t = taxonomy_data

        unknown_category = await taxonomy_client.post(
            BASE, json=_payload(t, tag_ids, category_id=999999), headers=headers
        )
        foreign_role = await taxonomy_client.post(
            BASE, json=_payload(t, tag_ids, role_id=t.study_mate_role_id), headers=headers
        )

        assert unknown_category.status_code == 404
        assert foreign_role.status_code == 404

    async def test_rejected_tag_returns_409(self, taxonomy_client, taxonomy_data, tag_ids, session, user_a):
        _, headers = user_a
        t = taxonomy_data
        rejected = await add_tag(
            session, "spam", status=TagStatus.REJECTED, scopes=[(t.tech_category_id, t.engineering_role_id)]
        )

        response = await taxonomy_client.post(
            BASE, json=_payload(t, tag_ids, tag_ids=[*tag_ids[:4], rejected.id]), headers=headers
        )

        assert response.status_code == 409

    async def test_pending_tag_of_another_user_is_allowed(
        self, taxonomy_client, taxonomy_data, tag_ids, session, user_a, user_b
    ):
        _, headers = user_a
        other, _ = user_b
        t = taxonomy_data
        pending = await add_tag(
            session,
            "fresh",
            status=TagStatus.PENDING,
            created_by=other.id,
            scopes=[(t.tech_category_id, t.engineering_role_id)],
        )

        profile = await _create(taxonomy_client, headers, t, tag_ids, tag_ids=[*tag_ids[:4], pending.id])

        assert pending.id in [tag["id"] for tag in profile["tags"]]

    @pytest.mark.parametrize(
        "overrides",
        [
            {"country_code": "ZZ"},
            {"country_code": "Germany"},
            {"timezone": "Asia/Tokyo"},
            {"timezone": "Not/AZone"},
            {"bio": "short"},
            {"bio": "x" * 2001},
            {"bio": "a" * 199 + "\x00"},
            {"goals_description": " " * 300},
            {"extra_attributes": {}},
            {"extra_attributes": {"grade": "wizard"}},
            {"extra_attributes": {"grade": "junior", "unknown": "x"}},
            {"extra_attributes": {"grade": None}},
        ],
    )
    async def test_invalid_content_returns_400(self, taxonomy_client, taxonomy_data, tag_ids, user_a, overrides):
        _, headers = user_a

        response = await taxonomy_client.post(BASE, json=_payload(taxonomy_data, tag_ids, **overrides), headers=headers)

        assert response.status_code == 400

    async def test_wrong_number_of_tags_and_duplicates_return_400(
        self, taxonomy_client, taxonomy_data, tag_ids, user_a
    ):
        _, headers = user_a

        too_few = await taxonomy_client.post(
            BASE, json=_payload(taxonomy_data, tag_ids, tag_ids=tag_ids[:4]), headers=headers
        )
        duplicates = await taxonomy_client.post(
            BASE, json=_payload(taxonomy_data, tag_ids, tag_ids=[tag_ids[0]] * 5), headers=headers
        )
        unknown = await taxonomy_client.post(
            BASE, json=_payload(taxonomy_data, tag_ids, tag_ids=[*tag_ids[:4], 987654]), headers=headers
        )

        assert too_few.status_code == 400
        assert duplicates.status_code == 400
        assert unknown.status_code == 400

    @pytest.mark.parametrize(
        "overrides",
        [
            {"category_id": 0},
            {"role_id": MAX_INT64 + 1},
            {"bio": 12345},
            {"bio": "x" * 4001},
            {"country_code": None},
            {"tag_ids": list(range(1, 52))},
            {"tag_ids": [0, 1, 2, 3, 4]},
            {"tag_ids": [MAX_INT64 + 1]},
            {"tag_ids": "1,2,3"},
            {"extra_attributes": {f"k{i}": "v" for i in range(33)}},
            {"extra_attributes": {"k" * 65: "v"}},
            {"extra_attributes": {"grade": "v" * 129}},
            {"extra_attributes": {"grade": 5}},
            {"extra_attributes": ["grade"]},
            {"unexpected": "field"},
        ],
    )
    async def test_malformed_body_returns_422(self, taxonomy_client, taxonomy_data, tag_ids, user_a, overrides):
        _, headers = user_a

        response = await taxonomy_client.post(BASE, json=_payload(taxonomy_data, tag_ids, **overrides), headers=headers)

        assert response.status_code == 422

    async def test_missing_required_fields_return_422(self, taxonomy_client, taxonomy_data, tag_ids, user_a):
        _, headers = user_a
        payload = _payload(taxonomy_data, tag_ids)
        del payload["bio"]

        response = await taxonomy_client.post(BASE, json=payload, headers=headers)

        assert response.status_code == 422


class TestReadProfiles:
    async def test_me_returns_only_own_profiles(self, taxonomy_client, taxonomy_data, tag_ids, user_a, user_b):
        _, headers_a = user_a
        _, headers_b = user_b
        mine = await _create(taxonomy_client, headers_a, taxonomy_data, tag_ids)
        await _create(taxonomy_client, headers_b, taxonomy_data, tag_ids)

        profiles = await _my_profiles(taxonomy_client, headers_a)

        assert [p["id"] for p in profiles] == [mine["id"]]

    async def test_me_is_empty_for_a_new_user(self, taxonomy_client, user_a):
        _, headers = user_a

        assert await _my_profiles(taxonomy_client, headers) == []

    async def test_get_own_profile(self, taxonomy_client, taxonomy_data, tag_ids, user_a):
        _, headers = user_a
        created = await _create(taxonomy_client, headers, taxonomy_data, tag_ids)

        response = await taxonomy_client.get(f"{BASE}/{created['id']}", headers=headers)

        assert response.status_code == 200
        assert response.json() == created

    async def test_someone_elses_profile_returns_404_not_403(
        self, taxonomy_client, taxonomy_data, tag_ids, user_a, user_b
    ):
        _, headers_a = user_a
        _, headers_b = user_b
        created = await _create(taxonomy_client, headers_a, taxonomy_data, tag_ids)

        response = await taxonomy_client.get(f"{BASE}/{created['id']}", headers=headers_b)

        assert response.status_code == 404

    @pytest.mark.parametrize("profile_id", [0, -1, MAX_INT64 + 1, "abc"])
    async def test_profile_id_out_of_range_returns_422(self, taxonomy_client, user_a, profile_id):
        _, headers = user_a

        response = await taxonomy_client.get(f"{BASE}/{profile_id}", headers=headers)

        assert response.status_code == 422

    async def test_unknown_profile_returns_404(self, taxonomy_client, user_a):
        _, headers = user_a

        response = await taxonomy_client.get(f"{BASE}/999999", headers=headers)

        assert response.status_code == 404


class TestUpdateProfile:
    async def test_replaces_content_and_tags(self, taxonomy_client, taxonomy_data, tag_ids, user_a):
        _, headers = user_a
        created = await _create(taxonomy_client, headers, taxonomy_data, tag_ids)

        response = await taxonomy_client.put(
            f"{BASE}/{created['id']}",
            json=_update_payload(
                taxonomy_data,
                tag_ids,
                bio="n" * 250,
                tag_ids=tag_ids[1:],
                extra_attributes={"grade": "middle"},
            ),
            headers=headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["bio"] == "n" * 250
        assert [t["id"] for t in body["tags"]] == tag_ids[1:]
        assert body["extra_attributes"] == {"grade": "middle"}
        assert body["status"] == "active"
        assert (await _my_profiles(taxonomy_client, headers))[0]["bio"] == "n" * 250

    async def test_category_or_role_in_the_body_returns_422(self, taxonomy_client, taxonomy_data, tag_ids, user_a):
        _, headers = user_a
        created = await _create(taxonomy_client, headers, taxonomy_data, tag_ids)

        response = await taxonomy_client.put(
            f"{BASE}/{created['id']}", json=_payload(taxonomy_data, tag_ids), headers=headers
        )

        assert response.status_code == 422

    async def test_erasing_a_required_attribute_returns_400(self, taxonomy_client, taxonomy_data, tag_ids, user_a):
        _, headers = user_a
        created = await _create(taxonomy_client, headers, taxonomy_data, tag_ids)

        response = await taxonomy_client.put(
            f"{BASE}/{created['id']}",
            json=_update_payload(taxonomy_data, tag_ids, extra_attributes={}),
            headers=headers,
        )

        assert response.status_code == 400

    async def test_someone_elses_profile_returns_404_and_is_unchanged(
        self, taxonomy_client, taxonomy_data, tag_ids, user_a, user_b
    ):
        _, headers_a = user_a
        _, headers_b = user_b
        created = await _create(taxonomy_client, headers_a, taxonomy_data, tag_ids)

        response = await taxonomy_client.put(
            f"{BASE}/{created['id']}",
            json=_update_payload(taxonomy_data, tag_ids, bio="h" * 250),
            headers=headers_b,
        )

        assert response.status_code == 404
        assert (await _my_profiles(taxonomy_client, headers_a))[0]["bio"] == created["bio"]

    async def test_hidden_profile_cannot_be_edited(self, taxonomy_client, taxonomy_data, tag_ids, session, user_a):
        _, headers = user_a
        created = await _create(taxonomy_client, headers, taxonomy_data, tag_ids)
        await session.execute(text("UPDATE profiles SET status = 'hidden_by_admin' WHERE id = :id"), {"id": created["id"]})
        await session.commit()

        response = await taxonomy_client.put(
            f"{BASE}/{created['id']}", json=_update_payload(taxonomy_data, tag_ids), headers=headers
        )

        assert response.status_code == 409

    async def test_parallel_puts_do_not_fail(self, taxonomy_client, taxonomy_data, tag_ids, user_a):
        _, headers = user_a
        created = await _create(taxonomy_client, headers, taxonomy_data, tag_ids)
        payload = _update_payload(taxonomy_data, tag_ids)

        responses = await asyncio.gather(
            *[taxonomy_client.put(f"{BASE}/{created['id']}", json=payload, headers=headers) for _ in range(5)]
        )

        assert [r.status_code for r in responses] == [200] * 5


class TestActiveProfileLifecycle:
    async def test_pause_the_only_profile_then_resume(self, taxonomy_client, taxonomy_data, tag_ids, user_a):
        _, headers = user_a
        created = await _create(taxonomy_client, headers, taxonomy_data, tag_ids)

        paused = await taxonomy_client.post(f"{BASE}/{created['id']}/pause", headers=headers)

        assert paused.status_code == 200
        assert paused.json()["status"] == "paused"
        assert paused.json()["is_active"] is False
        assert (await _my_profiles(taxonomy_client, headers))[0]["is_active"] is False

        resumed = await taxonomy_client.post(f"{BASE}/{created['id']}/resume", headers=headers)

        assert resumed.json()["status"] == "active"
        assert resumed.json()["is_active"] is True

    async def test_pause_the_active_profile_moves_the_pointer(
        self, taxonomy_client, taxonomy_data, tag_ids, session, user_a
    ):
        _, headers = user_a
        t = taxonomy_data
        first = await _create(taxonomy_client, headers, t, tag_ids)
        for tag_id in tag_ids:
            await session.execute(
                text("INSERT INTO tag_scopes (tag_id, category_id, role_id) VALUES (:t, :c, :r)"),
                {"t": tag_id, "c": t.tech_category_id, "r": t.design_role_id},
            )
        await session.commit()
        second = await _create(taxonomy_client, headers, t, tag_ids, role_id=t.design_role_id, extra_attributes={})

        await taxonomy_client.post(f"{BASE}/{first['id']}/pause", headers=headers)

        profiles = await _my_profiles(taxonomy_client, headers)
        assert [(p["id"], p["is_active"]) for p in profiles] == [(first["id"], False), (second["id"], True)]

    async def test_activate_switches_the_active_profile_and_rejects_a_paused_one(
        self, taxonomy_client, taxonomy_data, tag_ids, session, user_a
    ):
        _, headers = user_a
        t = taxonomy_data
        first = await _create(taxonomy_client, headers, t, tag_ids)
        for tag_id in tag_ids:
            await session.execute(
                text("INSERT INTO tag_scopes (tag_id, category_id, role_id) VALUES (:t, :c, :r)"),
                {"t": tag_id, "c": t.tech_category_id, "r": t.design_role_id},
            )
        await session.commit()
        second = await _create(taxonomy_client, headers, t, tag_ids, role_id=t.design_role_id, extra_attributes={})

        activated = await taxonomy_client.post(f"{BASE}/{second['id']}/activate", headers=headers)

        assert activated.status_code == 200
        assert activated.json()["is_active"] is True
        await taxonomy_client.post(f"{BASE}/{first['id']}/pause", headers=headers)
        paused_activation = await taxonomy_client.post(f"{BASE}/{first['id']}/activate", headers=headers)
        assert paused_activation.status_code == 409

    async def test_delete_removes_the_profile_and_clears_the_pointer(
        self, taxonomy_client, taxonomy_data, tag_ids, session, user_a
    ):
        user, headers = user_a
        created = await _create(taxonomy_client, headers, taxonomy_data, tag_ids)

        response = await taxonomy_client.delete(f"{BASE}/{created['id']}", headers=headers)

        assert response.status_code == 204
        assert await _my_profiles(taxonomy_client, headers) == []
        active = (
            await session.execute(text("SELECT active_profile_id FROM users WHERE id = :id"), {"id": user.id})
        ).scalar_one()
        assert active is None
        assert (await session.execute(text("SELECT count(*) FROM tags"))).scalar_one() == len(tag_ids)

    @pytest.mark.parametrize(
        "method, suffix",
        [("POST", "/activate"), ("POST", "/pause"), ("POST", "/resume"), ("DELETE", "")],
    )
    async def test_someone_elses_profile_returns_404_and_stays(
        self, taxonomy_client, taxonomy_data, tag_ids, session, user_a, user_b, method, suffix
    ):
        _, headers_a = user_a
        _, headers_b = user_b
        created = await _create(taxonomy_client, headers_a, taxonomy_data, tag_ids)

        response = await taxonomy_client.request(method, f"{BASE}/{created['id']}{suffix}", headers=headers_b)

        assert response.status_code == 404
        assert (await _my_profiles(taxonomy_client, headers_a))[0]["status"] == "active"

    @pytest.mark.parametrize("action", ["activate", "pause", "resume"])
    async def test_hidden_profile_returns_409(
        self, taxonomy_client, taxonomy_data, tag_ids, session, user_a, action
    ):
        _, headers = user_a
        created = await _create(taxonomy_client, headers, taxonomy_data, tag_ids)
        await session.execute(text("UPDATE profiles SET status = 'hidden_by_admin' WHERE id = :id"), {"id": created["id"]})
        await session.commit()

        response = await taxonomy_client.post(f"{BASE}/{created['id']}/{action}", headers=headers)

        assert response.status_code == 409


class TestAuthResponseCarriesProfiles:
    async def test_login_returns_profiles_and_active_profile_id(self, taxonomy_client, taxonomy_data, tag_ids):
        raw = build_init_data(BOT_TOKEN, 940100, int(time.time()), bad_hash=False)
        login = (await taxonomy_client.post("/api/v1/auth/telegram", json={"init_data": raw})).json()
        headers = {"Authorization": f"Bearer {login['access_token']}"}
        assert login["profiles"] == []
        assert login["user"]["active_profile_id"] is None
        created = await _create(taxonomy_client, headers, taxonomy_data, tag_ids)

        raw = build_init_data(BOT_TOKEN, 940100, int(time.time()), bad_hash=False)
        relogin = (await taxonomy_client.post("/api/v1/auth/telegram", json={"init_data": raw})).json()

        assert [p["id"] for p in relogin["profiles"]] == [created["id"]]
        assert relogin["profiles"][0]["is_active"] is True
        assert relogin["user"]["active_profile_id"] == created["id"]
