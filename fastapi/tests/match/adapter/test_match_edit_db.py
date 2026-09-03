"""경기 수정·취소가 **실제 PostgreSQL 에서** 도는지 확인한다.

계약 테스트(`test_match_edit_router.py`)는 스텁을 끼우므로 행 교체와 외래키를
보지 못한다. 여기서 보는 것은 셋이다.

1. `needs` 교체가 **옛 행을 실제로 지운다** — 남으면 인원이 두 배가 된다
2. 취소가 `match` 와 `match_position_need` 를 함께 지운다
3. 🔴 **지원이 붙은 경기는 못 지운다** — 앱이 409 로 막고, 그 뒤에도 행이 남아 있다

3번이 이 도메인의 설계 근거다. 부록 D 의 `match` 에 상태 컬럼이 없어 취소를 행
삭제로 정했고, `match_application` 의 삭제 규칙이 RESTRICT 라 그 경계가 생겼다.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from tests.conftest import V1

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"


def _at(days):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _signup(db_client, nickname):
    email = f"edit-{uuid.uuid4().hex[:12]}@super-sub.example"
    res = db_client.post(
        f"{V1}/auth/signup",
        json={"email": email, "password": PASSWORD, "nickname": nickname},
    )
    assert res.status_code == 201, res.text
    login = db_client.post(
        f"{V1}/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert login.status_code == 200, login.text
    return {
        "id": uuid.UUID(res.json()["id"]),
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


@pytest.fixture
def world(db_client, db_session):
    """축구 팀 하나와 주장, 팀 밖 용병 하나, 그리고 경기 하나."""
    owner = _signup(db_client, "주장")
    mercenary = _signup(db_client, "용병")

    created = db_client.post(
        f"{V1}/teams",
        json={
            "name": f"수정팀-{uuid.uuid4().hex[:6]}",
            "region": "서울",
            "sport_code": "football",
        },
        headers=owner["headers"],
    )
    assert created.status_code == 201, created.text
    team_id = uuid.UUID(created.json()["id"])

    match = db_client.post(
        f"{V1}/teams/{team_id}/matches",
        json={
            "played_at": _at(7),
            "place": "원래 구장",
            "needs": [{"position_code": "GK", "head_count": 1}],
        },
        headers=owner["headers"],
    )
    assert match.status_code == 201, match.text

    yield {
        "team_id": team_id,
        "owner": owner,
        "mercenary": mercenary,
        "match_id": uuid.UUID(match.json()["id"]),
    }

    db_session.execute(
        text("delete from match_application where match_id in "
             "(select id from match where team_id = :t)"),
        {"t": team_id},
    )
    db_session.execute(
        text("delete from match_position_need where match_id in "
             "(select id from match where team_id = :t)"),
        {"t": team_id},
    )
    db_session.execute(text("delete from match where team_id = :t"), {"t": team_id})
    db_session.execute(
        text("delete from team_member where team_id = :t"), {"t": team_id}
    )
    db_session.execute(text("delete from team where id = :t"), {"t": team_id})
    db_session.commit()


def _needs_rows(db_session, match_id):
    return db_session.execute(
        text(
            "select p.code, n.head_count from match_position_need n"
            " join position p on p.id = n.position_id"
            " where n.match_id = :id order by p.code"
        ),
        {"id": match_id},
    ).all()


class TestUpdate:
    def test_필요_포지션_교체가_옛_행을_지운다(self, db_client, db_session, world):
        """🔴 안 지우면 인원이 두 배가 된다 — 화면에는 합쳐서 보인다."""
        assert _needs_rows(db_session, world["match_id"]) == [("GK", 1)]

        res = db_client.patch(
            f"{V1}/matches/{world['match_id']}",
            json={
                "needs": [
                    {"position_code": "DF", "head_count": 2},
                    {"position_code": "FW", "head_count": 1},
                ]
            },
            headers=world["owner"]["headers"],
        )
        assert res.status_code == 200, res.text

        assert _needs_rows(db_session, world["match_id"]) == [("DF", 2), ("FW", 1)]

    def test_시각과_장소만_바꾸면_포지션은_그대로다(
        self, db_client, db_session, world
    ):
        res = db_client.patch(
            f"{V1}/matches/{world['match_id']}",
            json={"place": "옮긴 구장"},
            headers=world["owner"]["headers"],
        )
        assert res.status_code == 200, res.text
        assert res.json()["place"] == "옮긴 구장"
        assert _needs_rows(db_session, world["match_id"]) == [("GK", 1)]

    def test_다른_종목의_포지션은_거부되고_아무것도_안_바뀐다(
        self, db_client, db_session, world
    ):
        """검증이 저장보다 먼저다 — 반쯤 지워진 상태가 남으면 안 된다."""
        res = db_client.patch(
            f"{V1}/matches/{world['match_id']}",
            json={"place": "바뀌면 안 됨", "needs": [{"position_code": "P", "head_count": 1}]},
            headers=world["owner"]["headers"],
        )
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "UNKNOWN_POSITION"

        assert _needs_rows(db_session, world["match_id"]) == [("GK", 1)]
        place = db_session.execute(
            text("select place from match where id = :id"), {"id": world["match_id"]}
        ).scalar_one()
        assert place == "원래 구장"


class TestCancel:
    def test_취소가_경기와_필요_포지션을_함께_지운다(
        self, db_client, db_session, world
    ):
        res = db_client.delete(
            f"{V1}/matches/{world['match_id']}", headers=world["owner"]["headers"]
        )
        assert res.status_code == 204, res.text

        left = db_session.execute(
            text(
                "select (select count(*) from match where id = :id),"
                " (select count(*) from match_position_need where match_id = :id)"
            ),
            {"id": world["match_id"]},
        ).one()
        assert left == (0, 0)

    def test_지원이_붙으면_막히고_경기가_남는다(self, db_client, db_session, world):
        """🔴 `match_application` 의 삭제 규칙이 RESTRICT 라 생긴 경계다.

        앱이 409 로 먼저 막는다 — 안 막으면 DB 가 외래키로 막아 **500** 이 된다.
        """
        applied = db_client.post(
            f"{V1}/matches/{world['match_id']}/applications",
            json={},
            headers=world["mercenary"]["headers"],
        )
        assert applied.status_code == 201, applied.text

        res = db_client.delete(
            f"{V1}/matches/{world['match_id']}", headers=world["owner"]["headers"]
        )
        assert res.status_code == 409
        assert res.json()["error"]["code"] == "MATCH_HAS_APPLICATIONS"

        still = db_session.execute(
            text("select count(*) from match where id = :id"),
            {"id": world["match_id"]},
        ).scalar_one()
        assert still == 1, "막혔는데 경기가 사라졌다"

    def test_외래키가_실제로_막는지_확인한다(self, db_client, db_session, world):
        """앱의 409 가 없었다면 어떻게 되는지 — **DB 가 막는 것이 근거다.**

        앱 검사가 언젠가 느슨해져도 이 제약이 남아 있어야 한다.
        """
        from sqlalchemy.exc import IntegrityError

        applied = db_client.post(
            f"{V1}/matches/{world['match_id']}/applications",
            json={},
            headers=world["mercenary"]["headers"],
        )
        assert applied.status_code == 201, applied.text

        db_session.execute(
            text("delete from match_position_need where match_id = :id"),
            {"id": world["match_id"]},
        )
        with pytest.raises(IntegrityError):
            db_session.execute(
                text("delete from match where id = :id"), {"id": world["match_id"]}
            )
            db_session.flush()
        db_session.rollback()
