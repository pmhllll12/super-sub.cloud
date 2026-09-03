"""match/adapter/inbound/api/v1/match_router.py — 계약 문서 3-4절.

스텁을 끼워 DB 없이 돈다. 실제 조인·외래키는 `test_match_db.py` 가 본다.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.security import issue_access_token
from app.match.adapter.outbound.stub.match_stub_repository import (
    register_role,
    register_team,
    reset_matches,
)
from tests.conftest import V1, error_code


def _headers(user_id):
    return {"Authorization": f"Bearer {issue_access_token(user_id)}"}


def _future(days=7):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


@pytest.fixture(autouse=True)
def _clean():
    reset_matches()
    yield
    reset_matches()


@pytest.fixture
def football():
    """축구 팀 하나와 주장·구성원."""
    team_id, owner, member = uuid4(), uuid4(), uuid4()
    register_team(team_id, "football")
    register_role(team_id, owner, "owner")
    register_role(team_id, member, "member")
    return {"id": team_id, "owner": owner, "member": member}


def _body(**kw):
    body = {
        "played_at": _future(),
        "place": "강남 풋살장 2구장",
        "needs": [{"position_code": "GK", "head_count": 1}],
    }
    body.update(kw)
    return body


class TestCreateMatch:
    def test_인증이_필요하다(self, client, football):
        res = client.post(f"{V1}/teams/{football['id']}/matches", json=_body())
        assert res.status_code == 401

    def test_주장은_등록할_수_있다(self, client, football):
        res = client.post(
            f"{V1}/teams/{football['id']}/matches",
            json=_body(needs=[{"position_code": "GK", "head_count": 1},
                              {"position_code": "FW", "head_count": 2}]),
            headers=_headers(football["owner"]),
        )
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["team_id"] == str(football["id"])
        assert {(n["position_code"], n["position_label"], n["head_count"])
                for n in body["needs"]} == {("GK", "골키퍼", 1), ("FW", "공격수", 2)}

    def test_종목이_응답에_없다(self, client, football):
        """부록 D.4 — 종목은 주최 팀이 정한다. 경기에 두면 두 번째 진실이 생긴다."""
        res = client.post(
            f"{V1}/teams/{football['id']}/matches",
            json=_body(),
            headers=_headers(football["owner"]),
        )
        assert "sport_code" not in res.json()

    def test_일반_구성원은_못_한다(self, client, football):
        res = client.post(
            f"{V1}/teams/{football['id']}/matches",
            json=_body(),
            headers=_headers(football["member"]),
        )
        assert res.status_code == 403
        assert error_code(res) == "FORBIDDEN"

    def test_소속이_아니면_못_한다(self, client, football):
        res = client.post(
            f"{V1}/teams/{football['id']}/matches",
            json=_body(),
            headers=_headers(uuid4()),
        )
        assert res.status_code == 403

    def test_없는_팀이면_404(self, client, football):
        res = client.post(
            f"{V1}/teams/{uuid4()}/matches",
            json=_body(),
            headers=_headers(football["owner"]),
        )
        assert res.status_code == 404
        assert error_code(res) == "TEAM_NOT_FOUND"

    def test_지난_시각이면_422(self, client, football):
        res = client.post(
            f"{V1}/teams/{football['id']}/matches",
            json=_body(played_at=_future(-1)),
            headers=_headers(football["owner"]),
        )
        assert res.status_code == 422
        assert error_code(res) == "PAST_MATCH"

    def test_이_종목에_없는_포지션이면_422(self, client, football):
        """축구 팀에 농구 포지션을 적었다."""
        res = client.post(
            f"{V1}/teams/{football['id']}/matches",
            json=_body(needs=[{"position_code": "G", "head_count": 1}]),
            headers=_headers(football["owner"]),
        )
        assert res.status_code == 422
        assert error_code(res) == "UNKNOWN_POSITION"

    def test_같은_포지션을_두_번_적으면_422(self, client, football):
        res = client.post(
            f"{V1}/teams/{football['id']}/matches",
            json=_body(needs=[{"position_code": "GK", "head_count": 1},
                              {"position_code": "GK", "head_count": 2}]),
            headers=_headers(football["owner"]),
        )
        assert res.status_code == 422
        assert error_code(res) == "DUPLICATE_POSITION"

    def test_인원이_0이면_422(self, client, football):
        res = client.post(
            f"{V1}/teams/{football['id']}/matches",
            json=_body(needs=[{"position_code": "GK", "head_count": 0}]),
            headers=_headers(football["owner"]),
        )
        assert res.status_code == 422

    def test_필요_포지션이_없으면_422(self, client, football):
        """모집 글인데 무엇을 모집하는지 없으면 뜻이 없다."""
        res = client.post(
            f"{V1}/teams/{football['id']}/matches",
            json=_body(needs=[]),
            headers=_headers(football["owner"]),
        )
        assert res.status_code == 422


class TestReadMatch:
    def test_등록한_경기를_다시_읽는다(self, client, football):
        created = client.post(
            f"{V1}/teams/{football['id']}/matches",
            json=_body(),
            headers=_headers(football["owner"]),
        ).json()

        res = client.get(f"{V1}/matches/{created['id']}", headers=_headers(uuid4()))
        assert res.status_code == 200
        assert res.json()["place"] == "강남 풋살장 2구장"

    def test_없는_경기는_404(self, client):
        res = client.get(f"{V1}/matches/{uuid4()}", headers=_headers(uuid4()))
        assert res.status_code == 404
        assert error_code(res) == "MATCH_NOT_FOUND"


class TestListTeamMatches:
    """`GET /teams/{id}/matches` — 다가오는 경기만, 이른 것부터."""

    def _create(self, client, football, days, place):
        return client.post(
            f"{V1}/teams/{football['id']}/matches",
            json={
                "played_at": _future(days),
                "place": place,
                "needs": [{"position_code": "GK", "head_count": 1}],
            },
            headers=_headers(football["owner"]),
        )

    def test_인증이_필요하다(self, client, football):
        assert client.get(f"{V1}/teams/{football['id']}/matches").status_code == 401

    def test_이른_경기가_앞에_온다(self, client, football):
        self._create(client, football, 9, "늦은 경기")
        self._create(client, football, 3, "이른 경기")

        res = client.get(
            f"{V1}/teams/{football['id']}/matches", headers=_headers(uuid4())
        )
        assert res.status_code == 200, res.text
        assert [m["place"] for m in res.json()] == ["이른 경기", "늦은 경기"]

    def test_필요_포지션이_함께_온다(self, client, football):
        """목록만 보고 무엇을 모집하는지 알 수 있어야 한다."""
        self._create(client, football, 5, "강남")
        body = client.get(
            f"{V1}/teams/{football['id']}/matches", headers=_headers(uuid4())
        ).json()
        assert body[0]["needs"][0]["position_label"] == "골키퍼"

    def test_경기가_없으면_빈_배열(self, client, football):
        res = client.get(
            f"{V1}/teams/{football['id']}/matches", headers=_headers(uuid4())
        )
        assert res.json() == []

    def test_없는_팀은_404(self, client):
        """🔴 빈 배열이 아니다 — 오타 난 id 를 "경기가 없구나"로 읽으면 안 된다."""
        res = client.get(f"{V1}/teams/{uuid4()}/matches", headers=_headers(uuid4()))
        assert res.status_code == 404
        assert error_code(res) == "TEAM_NOT_FOUND"

    def test_소속이_아니어도_본다(self, client, football):
        """모집 글이다 — 지원할 사람이 봐야 한다."""
        self._create(client, football, 4, "강남")
        res = client.get(
            f"{V1}/teams/{football['id']}/matches", headers=_headers(uuid4())
        )
        assert len(res.json()) == 1
