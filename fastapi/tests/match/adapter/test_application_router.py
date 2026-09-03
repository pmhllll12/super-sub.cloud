"""지원·제안 계약. 계약 문서 3-5절.

확정은 **두 시각이 다 차는 것**이고, 응답의 `confirmed` 는 서버가 계산한다.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.security import issue_access_token
from app.match.adapter.outbound.stub.match_stub_repository import (
    register_role,
    register_team,
    register_user,
    reset_matches,
)
from tests.conftest import V1, error_code


def _headers(user_id):
    return {"Authorization": f"Bearer {issue_access_token(user_id)}"}


@pytest.fixture(autouse=True)
def _clean():
    reset_matches()
    yield
    reset_matches()


@pytest.fixture
def world(client):
    """축구 팀 하나 · 주장 · 팀 구성원 · 외부인 둘, 그리고 경기 하나."""
    team_id, owner, member = uuid4(), uuid4(), uuid4()
    outsider, other = uuid4(), uuid4()
    register_team(team_id, "football")
    register_role(team_id, owner, "owner")
    register_role(team_id, member, "member")
    for u in (owner, member, outsider, other):
        register_user(u)

    res = client.post(
        f"{V1}/teams/{team_id}/matches",
        json={
            "played_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "place": "강남 풋살장",
            "needs": [{"position_code": "GK", "head_count": 1}],
        },
        headers=_headers(owner),
    )
    assert res.status_code == 201, res.text
    return {
        "team_id": team_id,
        "owner": owner,
        "member": member,
        "outsider": outsider,
        "other": other,
        "match_id": res.json()["id"],
    }


def _apply(client, world, actor, user_id=None):
    body = {} if user_id is None else {"user_id": str(user_id)}
    return client.post(
        f"{V1}/matches/{world['match_id']}/applications",
        json=body,
        headers=_headers(actor),
    )


class TestApply:
    def test_인증이_필요하다(self, client, world):
        res = client.post(f"{V1}/matches/{world['match_id']}/applications", json={})
        assert res.status_code == 401

    def test_외부인은_지원한다(self, client, world):
        res = _apply(client, world, world["outsider"])
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["user_accepted_at"] is not None
        assert body["team_accepted_at"] is None
        assert body["confirmed"] is False

    def test_팀_소속은_지원할_수_없다(self, client, world):
        """용병 매칭이다 — 자기 팀 경기에 지원하는 것은 뜻이 없다."""
        res = _apply(client, world, world["member"])
        assert res.status_code == 409
        assert error_code(res) == "TEAM_MEMBER_CANNOT_APPLY"

    def test_두_번_지원하면_409(self, client, world):
        _apply(client, world, world["outsider"])
        res = _apply(client, world, world["outsider"])
        assert res.status_code == 409
        assert error_code(res) == "ALREADY_APPLIED"

    def test_주장은_제안한다(self, client, world):
        res = _apply(client, world, world["owner"], user_id=world["outsider"])
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["team_accepted_at"] is not None
        assert body["user_accepted_at"] is None

    def test_일반_구성원은_제안하지_못한다(self, client, world):
        res = _apply(client, world, world["member"], user_id=world["outsider"])
        assert res.status_code == 403
        assert error_code(res) == "FORBIDDEN"

    def test_팀_소속에게는_제안하지_않는다(self, client, world):
        res = _apply(client, world, world["owner"], user_id=world["member"])
        assert res.status_code == 409
        assert error_code(res) == "TEAM_MEMBER_CANNOT_APPLY"

    def test_없는_사용자에게_제안하면_404(self, client, world):
        res = _apply(client, world, world["owner"], user_id=uuid4())
        assert res.status_code == 404
        assert error_code(res) == "USER_NOT_FOUND"

    def test_없는_경기면_404(self, client, world):
        res = client.post(
            f"{V1}/matches/{uuid4()}/applications",
            json={},
            headers=_headers(world["outsider"]),
        )
        assert res.status_code == 404
        assert error_code(res) == "MATCH_NOT_FOUND"


class TestAccept:
    def _accept(self, client, world, application_id, actor):
        return client.post(
            f"{V1}/matches/{world['match_id']}/applications/{application_id}/accept",
            headers=_headers(actor),
        )

    def test_주장이_수락하면_확정된다(self, client, world):
        app = _apply(client, world, world["outsider"]).json()
        res = self._accept(client, world, app["id"], world["owner"])
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["team_accepted_at"] is not None
        assert body["confirmed"] is True

    def test_제안을_본인이_수락하면_확정된다(self, client, world):
        app = _apply(client, world, world["owner"], user_id=world["outsider"]).json()
        res = self._accept(client, world, app["id"], world["outsider"])
        assert res.json()["confirmed"] is True

    def test_자기_쪽을_또_수락하면_409(self, client, world):
        app = _apply(client, world, world["outsider"]).json()
        res = self._accept(client, world, app["id"], world["outsider"])
        assert res.status_code == 409
        assert error_code(res) == "ALREADY_ACCEPTED"

    def test_무관한_사람은_403(self, client, world):
        """🔴 404 가 아니라 403 이다 — 지원 건의 존재 여부를 흘리지 않는다."""
        app = _apply(client, world, world["outsider"]).json()
        res = self._accept(client, world, app["id"], world["other"])
        assert res.status_code == 403
        assert error_code(res) == "FORBIDDEN"

    def test_없는_지원_건은_404(self, client, world):
        res = self._accept(client, world, uuid4(), world["owner"])
        assert res.status_code == 404
        assert error_code(res) == "APPLICATION_NOT_FOUND"


class TestList:
    def test_주장은_전부_본다(self, client, world):
        _apply(client, world, world["outsider"])
        _apply(client, world, world["other"])
        res = client.get(
            f"{V1}/matches/{world['match_id']}/applications",
            headers=_headers(world["owner"]),
        )
        assert res.status_code == 200
        assert len(res.json()) == 2

    def test_지원자는_자기_건만_본다(self, client, world):
        """지원자 명단은 팀의 정보다."""
        _apply(client, world, world["outsider"])
        _apply(client, world, world["other"])
        res = client.get(
            f"{V1}/matches/{world['match_id']}/applications",
            headers=_headers(world["outsider"]),
        )
        assert [a["user_id"] for a in res.json()] == [str(world["outsider"])]
