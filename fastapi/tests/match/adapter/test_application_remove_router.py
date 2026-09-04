"""`DELETE /matches/{id}/applications/{id}` — 무르기·거절. 계약 3-5절.

스텁을 끼워 DB 없이 돈다.

## 이 검사가 보는 것

미결 `jin` 16번에서 **A-1**(거절 = 행 삭제)로 정한 결과다. 핵심은 마지막
`TestUnblocksCancel` — **이것이 실제로 `DELETE /matches/{id}` 의 409 를 푸는가.**
거절을 시각 컬럼으로 담았으면 행이 남아 안 풀린다(그래서 A-2 를 버렸다).

무르기와 거절은 **같은 경로**다. 하는 일이 같아서다 — 누가 부르느냐만 다르다.
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
    """경기 하나 + 주장·구성원·용병 둘. 용병 하나가 이미 지원해 둔 상태."""
    team_id, owner, member = uuid4(), uuid4(), uuid4()
    applicant, stranger = uuid4(), uuid4()
    register_team(team_id, "football")
    register_role(team_id, owner, "owner")
    register_role(team_id, member, "member")
    register_user(member, "구성원")
    register_user(applicant, "지원자")
    register_user(stranger, "무관한 사람")

    created = client.post(
        f"{V1}/teams/{team_id}/matches",
        json={
            "played_at": _at(7),
            "place": "강남 풋살장 2구장",
            "needs": [{"position_code": "GK", "head_count": 1}],
        },
        headers=_headers(owner),
    )
    assert created.status_code == 201, created.text
    match_id = created.json()["id"]

    applied = client.post(
        f"{V1}/matches/{match_id}/applications",
        json={},
        headers=_headers(applicant),
    )
    assert applied.status_code == 201, applied.text

    return {
        "id": match_id,
        "team_id": team_id,
        "owner": owner,
        "member": member,
        "applicant": applicant,
        "stranger": stranger,
        "application_id": applied.json()["id"],
    }


def _remove(client, match, actor, application_id=None):
    return client.delete(
        f"{V1}/matches/{match['id']}/applications/"
        f"{application_id or match['application_id']}",
        headers=_headers(actor),
    )


def _count_applications(client, match):
    res = client.get(
        f"{V1}/matches/{match['id']}/applications", headers=_headers(match["owner"])
    )
    assert res.status_code == 200, res.text
    return len(res.json())


class TestAuth:
    def test_인증이_필요하다(self, client, match):
        res = client.delete(
            f"{V1}/matches/{match['id']}/applications/{match['application_id']}"
        )
        assert res.status_code == 401

    def test_무관한_사람은_없앨_수_없다(self, client, match):
        res = _remove(client, match, match["stranger"])
        assert res.status_code == 403
        assert error_code(res) == "FORBIDDEN"
        assert _count_applications(client, match) == 1

    def test_같은_팀_구성원이라도_주장이_아니면_못_한다(self, client, match):
        """거절은 팀의 결정이라 주장만 한다 — 수락과 같은 기준이다."""
        res = _remove(client, match, match["member"])
        assert res.status_code == 403
        assert _count_applications(client, match) == 1


class TestRemove:
    def test_지원자는_스스로_무를_수_있다(self, client, match):
        assert _remove(client, match, match["applicant"]).status_code == 204
        assert _count_applications(client, match) == 0

    def test_주장은_거절할_수_있다(self, client, match):
        assert _remove(client, match, match["owner"]).status_code == 204
        assert _count_applications(client, match) == 0

    def test_확정된_건도_없앨_수_있다(self, client, match):
        """🔴 확정된 것을 못 없애면 취소가 다시 막힌다 — 그 경우가 남으면
        16번이 반만 풀린 것이다."""
        accepted = client.post(
            f"{V1}/matches/{match['id']}/applications/"
            f"{match['application_id']}/accept",
            headers=_headers(match["owner"]),
        )
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["confirmed"] is True

        assert _remove(client, match, match["owner"]).status_code == 204
        assert _count_applications(client, match) == 0

    def test_두_번_없애면_404_다(self, client, match):
        assert _remove(client, match, match["owner"]).status_code == 204
        res = _remove(client, match, match["owner"])
        assert res.status_code == 404
        assert error_code(res) == "APPLICATION_NOT_FOUND"


class TestNotFound:
    def test_없는_지원_건은_404_다(self, client, match):
        res = _remove(client, match, match["owner"], application_id=uuid4())
        assert res.status_code == 404
        assert error_code(res) == "APPLICATION_NOT_FOUND"

    def test_없는_경기는_404_다(self, client, match):
        res = client.delete(
            f"{V1}/matches/{uuid4()}/applications/{match['application_id']}",
            headers=_headers(match["owner"]),
        )
        assert res.status_code == 404
        assert error_code(res) == "MATCH_NOT_FOUND"

    def test_다른_경기의_지원_건이면_404_다(self, client, match):
        """경로의 경기와 지원 건의 경기가 달라도 지워지면 안 된다."""
        other = client.post(
            f"{V1}/teams/{match['team_id']}/matches",
            json={
                "played_at": _at(9),
                "place": "다른 구장",
                "needs": [{"position_code": "GK", "head_count": 1}],
            },
            headers=_headers(match["owner"]),
        )
        assert other.status_code == 201, other.text

        res = client.delete(
            f"{V1}/matches/{other.json()['id']}/applications/"
            f"{match['application_id']}",
            headers=_headers(match["owner"]),
        )
        assert res.status_code == 404
        assert error_code(res) == "APPLICATION_NOT_FOUND"
        # 원래 경기의 지원은 그대로다.
        assert _count_applications(client, match) == 1


class TestPastMatch:
    def test_지난_경기의_지원은_못_없앤다(self, client, match):
        """🔴 확정된 행이 "누가 그 경기에 뛰었나"의 유일한 근거다 — 지우면
        평가(SFR-008)가 대상을 잃는다."""
        from dataclasses import replace
        from uuid import UUID

        from app.match.adapter.outbound.stub.match_stub_repository import _MATCHES

        mid = UUID(match["id"])
        _MATCHES[mid] = replace(
            _MATCHES[mid], played_at=datetime.now(timezone.utc) - timedelta(days=1)
        )

        res = _remove(client, match, match["owner"])
        assert res.status_code == 422
        assert error_code(res) == "PAST_MATCH"


class TestUnblocksCancel:
    """🔴 미결 16번이 실제로 풀렸는지 — 이 검사가 그 항목의 존재 이유다."""

    def test_거절하면_경기를_취소할_수_있다(self, client, match):
        blocked = client.delete(
            f"{V1}/matches/{match['id']}", headers=_headers(match["owner"])
        )
        assert blocked.status_code == 409
        assert error_code(blocked) == "MATCH_HAS_APPLICATIONS"

        assert _remove(client, match, match["owner"]).status_code == 204

        assert (
            client.delete(
                f"{V1}/matches/{match['id']}", headers=_headers(match["owner"])
            ).status_code
            == 204
        )

    def test_지원자가_스스로_물러도_취소가_풀린다(self, client, match):
        assert _remove(client, match, match["applicant"]).status_code == 204
        assert (
            client.delete(
                f"{V1}/matches/{match['id']}", headers=_headers(match["owner"])
            ).status_code
            == 204
        )
