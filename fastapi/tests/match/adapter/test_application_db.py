"""지원·제안을 **실제 PostgreSQL** 에 대고 확인한다.

스텁이 답할 수 없는 것들이다:

- 🔴 **수락이 이미 찬 시각을 덮지 않는가** (`WHERE ... IS NULL` 이 빠지면 조용히 밀린다)
- 유일 제약 `uq_match_application` 이 동시 지원의 마지막 방어선인가
- 닉네임이 `user` 테이블에서 읽히는가 (`match` 는 `user` 를 임포트하지 않는다)
- 지난 경기에는 지원이 막히는가 (등록 뒤에 시간이 흐른 경우)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from tests.conftest import V1, error_code

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"


def _account(db_client, nickname):
    email = f"apply-{uuid.uuid4().hex[:12]}@super-sub.example"
    signup = db_client.post(
        f"{V1}/auth/signup",
        json={"email": email, "password": PASSWORD, "nickname": nickname},
    )
    assert signup.status_code == 201, signup.text
    login = db_client.post(
        f"{V1}/auth/login", json={"email": email, "password": PASSWORD}
    )
    return {
        "email": email,
        "id": uuid.UUID(signup.json()["id"]),
        "nickname": nickname,
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


@pytest.fixture
def world(db_client, db_session):
    owner = _account(db_client, "주장")
    outsider = _account(db_client, "용병지원자")

    team = db_client.post(
        f"{V1}/teams",
        json={"name": "지원테스트팀", "region": "서울", "sport_code": "football"},
        headers=owner["headers"],
    )
    assert team.status_code == 201, team.text
    team_id = team.json()["id"]

    match = db_client.post(
        f"{V1}/teams/{team_id}/matches",
        json={
            "played_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "place": "강남 운동장",
            "needs": [{"position_code": "GK", "head_count": 1}],
        },
        headers=owner["headers"],
    )
    assert match.status_code == 201, match.text

    yield {
        "owner": owner,
        "outsider": outsider,
        "team_id": team_id,
        "match_id": match.json()["id"],
    }

    db_session.execute(
        text("delete from match_application where match_id = :m"),
        {"m": match.json()["id"]},
    )
    db_session.execute(
        text("delete from match_position_need where match_id = :m"),
        {"m": match.json()["id"]},
    )
    db_session.execute(text("delete from match where team_id = :t"), {"t": team_id})
    db_session.execute(text("delete from team_member where team_id = :t"), {"t": team_id})
    db_session.execute(text("delete from team where id = :t"), {"t": team_id})
    db_session.execute(
        text('delete from "user" where email = any(:e)'),
        {"e": [owner["email"], outsider["email"]]},
    )
    db_session.commit()


def _apply(db_client, world, actor, user_id=None):
    body = {} if user_id is None else {"user_id": str(user_id)}
    return db_client.post(
        f"{V1}/matches/{world['match_id']}/applications",
        json=body,
        headers=actor["headers"],
    )


def _row(db_session, application_id):
    return db_session.execute(
        text(
            "select user_id, team_accepted_at, user_accepted_at "
            "from match_application where id = :a"
        ),
        {"a": application_id},
    ).one()


class TestApplyInDb:
    def test_행이_남고_한쪽_시각만_찬다(self, db_client, db_session, world):
        res = _apply(db_client, world, world["outsider"])
        assert res.status_code == 201, res.text

        row = _row(db_session, res.json()["id"])
        assert str(row.user_id) == str(world["outsider"]["id"])
        assert row.user_accepted_at is not None
        assert row.team_accepted_at is None

    def test_닉네임이_user_테이블에서_온다(self, db_client, world):
        """`match` 는 `user` 를 임포트하지 않고 컬럼만 읽는다 — 여기가 방어선이다."""
        res = _apply(db_client, world, world["outsider"])
        assert res.json()["nickname"] == "용병지원자"

    def test_유일_제약이_두_번째_지원을_막는다(self, db_client, db_session, world):
        _apply(db_client, world, world["outsider"])
        again = _apply(db_client, world, world["outsider"])
        assert again.status_code == 409
        assert error_code(again) == "ALREADY_APPLIED"

        count = db_session.execute(
            text(
                "select count(*) from match_application "
                "where match_id = :m and user_id = :u"
            ),
            {"m": world["match_id"], "u": str(world["outsider"]["id"])},
        ).scalar_one()
        assert count == 1

    def test_지난_경기에는_지원할_수_없다(self, db_client, db_session, world):
        """등록은 미래만 되지만 **그 뒤로 시간이 흐른다.**"""
        db_session.execute(
            text("update match set played_at = now() - interval '1 day' where id = :m"),
            {"m": world["match_id"]},
        )
        db_session.commit()

        res = _apply(db_client, world, world["outsider"])
        assert res.status_code == 422
        assert error_code(res) == "PAST_MATCH"


class TestAcceptInDb:
    def _accept(self, db_client, world, application_id, actor):
        return db_client.post(
            f"{V1}/matches/{world['match_id']}/applications/{application_id}/accept",
            headers=actor["headers"],
        )

    def test_수락하면_반대쪽이_차고_확정된다(self, db_client, db_session, world):
        app = _apply(db_client, world, world["outsider"]).json()
        res = self._accept(db_client, world, app["id"], world["owner"])
        assert res.status_code == 200, res.text
        assert res.json()["confirmed"] is True

        row = _row(db_session, app["id"])
        assert row.team_accepted_at is not None and row.user_accepted_at is not None

    def test_이미_찬_시각을_덮지_않는다(self, db_client, db_session, world):
        """🔴 덮으면 "언제 확정됐나"가 뒤로 밀린다."""
        app = _apply(db_client, world, world["outsider"]).json()
        first = _row(db_session, app["id"]).user_accepted_at

        again = self._accept(db_client, world, app["id"], world["outsider"])
        assert again.status_code == 409
        assert _row(db_session, app["id"]).user_accepted_at == first
