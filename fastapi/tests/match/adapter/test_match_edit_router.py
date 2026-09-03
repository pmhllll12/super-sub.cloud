"""`PATCH /matches/{id}` · `DELETE /matches/{id}` — 경기 수정·취소. 계약 3-4절.

스텁을 끼워 DB 없이 돈다. 실제 필요 포지션 교체와 외래키는 `test_match_edit_db.py`.

## 이 검사가 보는 것

**취소는 행 삭제다.** 부록 D 의 `match` 에 상태 컬럼이 없어서 그렇게 정했고,
그래서 **지원이 붙으면 취소할 수 없다** — 그 경계가 여기서 지켜지는지 본다.
"""

from __future__ import annotations

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


def _at(days):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


@pytest.fixture(autouse=True)
def _clean():
    reset_matches()
    yield
    reset_matches()


@pytest.fixture
def match(client):
    """축구 팀 하나와 주장·구성원·외부인, 그리고 등록된 경기 하나."""
    team_id, owner, member, outsider = uuid4(), uuid4(), uuid4(), uuid4()
    register_team(team_id, "football")
    register_role(team_id, owner, "owner")
    register_role(team_id, member, "member")
    register_user(member, "구성원")
    # 지원은 **팀 밖 사람만** 할 수 있다(`TEAM_MEMBER_CANNOT_APPLY`).
    register_user(outsider, "용병")

    res = client.post(
        f"{V1}/teams/{team_id}/matches",
        json={
            "played_at": _at(7),
            "place": "강남 풋살장 2구장",
            "needs": [{"position_code": "GK", "head_count": 1}],
        },
        headers=_headers(owner),
    )
    assert res.status_code == 201, res.text
    return {
        "id": res.json()["id"],
        "team_id": team_id,
        "owner": owner,
        "member": member,
        "outsider": outsider,
    }


def _patch(client, match, actor, **body):
    return client.patch(
        f"{V1}/matches/{match['id']}", json=body, headers=_headers(actor)
    )


def _cancel(client, match, actor):
    return client.delete(f"{V1}/matches/{match['id']}", headers=_headers(actor))


class TestUpdateAuth:
    def test_인증이_필요하다(self, client, match):
        assert client.patch(f"{V1}/matches/{match['id']}", json={}).status_code == 401

    def test_주장만_고칠_수_있다(self, client, match):
        res = _patch(client, match, match["member"], place="옮긴 구장")
        assert res.status_code == 403
        assert error_code(res) == "FORBIDDEN"

    def test_소속이_아니면_못_고친다(self, client, match):
        assert _patch(client, match, match["outsider"], place="x").status_code == 403

    def test_없는_경기는_404_다(self, client, match):
        res = client.patch(
            f"{V1}/matches/{uuid4()}", json={"place": "x"}, headers=_headers(match["owner"])
        )
        assert res.status_code == 404
        assert error_code(res) == "MATCH_NOT_FOUND"


class TestUpdate:
    def test_보낸_것만_바뀐다(self, client, match):
        res = _patch(client, match, match["owner"], place="옮긴 구장")
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["place"] == "옮긴 구장"
        # 안 보낸 것은 그대로다.
        assert body["needs"][0]["position_code"] == "GK"

    def test_빈_본문은_아무것도_안_바꾼다(self, client, match):
        before = client.get(
            f"{V1}/matches/{match['id']}", headers=_headers(match["owner"])
        ).json()
        after = _patch(client, match, match["owner"]).json()
        assert after == before

    def test_필요_포지션은_통째로_갈린다(self, client, match):
        res = _patch(
            client,
            match,
            match["owner"],
            needs=[
                {"position_code": "DF", "head_count": 2},
                {"position_code": "FW", "head_count": 1},
            ],
        )
        assert res.status_code == 200, res.text
        codes = {n["position_code"] for n in res.json()["needs"]}
        assert codes == {"DF", "FW"}, "GK 가 남아 있으면 통째로 갈린 것이 아니다"

    def test_시각을_옮길_수_있다(self, client, match):
        moved = _at(10)
        res = _patch(client, match, match["owner"], played_at=moved)
        assert res.status_code == 200, res.text
        assert res.json()["played_at"].startswith(moved[:13])


class TestUpdateRules:
    def test_과거로는_옮길_수_없다(self, client, match):
        res = _patch(client, match, match["owner"], played_at=_at(-1))
        assert res.status_code == 422
        assert error_code(res) == "PAST_MATCH"

    def test_지난_경기는_못_고친다(self, client, match):
        """끝난 일을 고치는 것은 기록을 바꾸는 것이지 모집을 고치는 것이 아니다."""
        from app.match.adapter.outbound.stub.match_stub_repository import _MATCHES
        from dataclasses import replace
        import uuid as _uuid

        mid = _uuid.UUID(match["id"])
        _MATCHES[mid] = replace(
            _MATCHES[mid], played_at=datetime.now(timezone.utc) - timedelta(days=1)
        )

        res = _patch(client, match, match["owner"], place="x")
        assert res.status_code == 422
        assert error_code(res) == "PAST_MATCH"

    def test_같은_포지션을_두_번_적을_수_없다(self, client, match):
        res = _patch(
            client,
            match,
            match["owner"],
            needs=[
                {"position_code": "GK", "head_count": 1},
                {"position_code": "GK", "head_count": 2},
            ],
        )
        assert res.status_code == 422
        assert error_code(res) == "DUPLICATE_POSITION"

    def test_다른_종목의_포지션은_거부한다(self, client, match):
        """등록과 **같은 검증**을 쓴다 — 갈리면 한쪽으로만 이상한 값이 들어간다."""
        res = _patch(
            client, match, match["owner"], needs=[{"position_code": "P", "head_count": 1}]
        )
        assert res.status_code == 422
        assert error_code(res) == "UNKNOWN_POSITION"

    def test_빈_포지션_목록은_거부한다(self, client, match):
        res = _patch(client, match, match["owner"], needs=[])
        assert res.status_code == 422
        assert error_code(res) == "VALIDATION_ERROR"


class TestCancel:
    def test_인증이_필요하다(self, client, match):
        assert client.delete(f"{V1}/matches/{match['id']}").status_code == 401

    def test_주장은_취소할_수_있다(self, client, match):
        assert _cancel(client, match, match["owner"]).status_code == 204

        gone = client.get(
            f"{V1}/matches/{match['id']}", headers=_headers(match["owner"])
        )
        assert gone.status_code == 404

    def test_구성원은_취소할_수_없다(self, client, match):
        assert _cancel(client, match, match["member"]).status_code == 403

    def test_없는_경기는_404_다(self, client, match):
        res = client.delete(
            f"{V1}/matches/{uuid4()}", headers=_headers(match["owner"])
        )
        assert res.status_code == 404
        assert error_code(res) == "MATCH_NOT_FOUND"

    def test_지원이_붙으면_취소할_수_없다(self, client, match):
        """🔴 취소가 행 삭제라서 생기는 경계다. 지원자에게 알릴 방법도 없다."""
        applied = client.post(
            f"{V1}/matches/{match['id']}/applications",
            json={},
            headers=_headers(match["outsider"]),
        )
        assert applied.status_code == 201, applied.text

        res = _cancel(client, match, match["owner"])
        assert res.status_code == 409
        assert error_code(res) == "MATCH_HAS_APPLICATIONS"

        # 막혔으면 경기는 그대로 있어야 한다.
        assert (
            client.get(
                f"{V1}/matches/{match['id']}", headers=_headers(match["owner"])
            ).status_code
            == 200
        )

    def test_지난_경기는_취소할_수_없다(self, client, match):
        """이미 열린 경기를 "취소"하는 것은 뜻이 없다."""
        from app.match.adapter.outbound.stub.match_stub_repository import _MATCHES
        from dataclasses import replace
        import uuid as _uuid

        mid = _uuid.UUID(match["id"])
        _MATCHES[mid] = replace(
            _MATCHES[mid], played_at=datetime.now(timezone.utc) - timedelta(days=1)
        )

        res = _cancel(client, match, match["owner"])
        assert res.status_code == 422
        assert error_code(res) == "PAST_MATCH"
