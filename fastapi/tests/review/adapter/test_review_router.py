"""평가·신뢰 경로. 계약 3-9절. SFR-008.

스텁을 끼워 DB 없이 돈다. 유일 제약이 **실제로 DB 에 있는지**는
`test_review_db.py` 가 본다.

## 이 검사가 보는 것

부록 D 가 스키마로 박아 둔 것과, 2026-09-04 에 정어진이 정한 것 셋을 지킨다.

1. **평가에 점수가 없다** — 고른 선택지만 남는다(3.4)
2. **경기 후 14일** 안에만 평가할 수 있다
3. **불참은 주최 팀 주장만** 기록한다
4. `report`·`no_show` 는 `review` 와 무관하다 — 평가를 안 해도 신고할 수 있다
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.core.security import issue_access_token
from app.review.adapter.outbound.stub.review_stub_repository import (
    no_shows,
    register_confirmed,
    register_match,
    register_role,
    register_user,
    reports,
    reviews_of,
)
from tests.conftest import V1, error_code

OPTIONS = f"{V1}/review-options"
REPORTS = f"{V1}/reports"


def _headers(user_id):
    return {"Authorization": f"Bearer {issue_access_token(user_id)}"}


def _reviews(match_id):
    return f"{V1}/matches/{match_id}/reviews"


def _no_shows(match_id):
    return f"{V1}/matches/{match_id}/no-shows"


@pytest.fixture
def played(client):
    """어제 끝난 경기 하나. 주장·용병 둘이 확정돼 있다."""
    match_id, owner, mercenary, outsider = uuid4(), uuid4(), uuid4(), uuid4()
    register_match(match_id, datetime.now(timezone.utc) - timedelta(days=1))
    register_role(match_id, owner, "owner")
    register_confirmed(match_id, owner)
    register_confirmed(match_id, mercenary)
    register_user(outsider)
    return {
        "id": match_id,
        "owner": owner,
        "mercenary": mercenary,
        "outsider": outsider,
    }


class TestOptions:
    def test_인증이_필요하다(self, client):
        assert client.get(OPTIONS).status_code == 401

    def test_노출_순서대로_온다(self, client, played):
        """🔴 카테고리 알파벳순이면 '주의'가 맨 앞에 온다 — 그러면 안 된다."""
        res = client.get(OPTIONS, headers=_headers(played["owner"]))
        assert res.status_code == 200

        cats = [o["category"] for o in res.json()]
        assert cats[0] == "manner", "매너가 먼저여야 한다"
        assert cats[-1] == "caution", "주의가 마지막이어야 한다"
        # 카테고리가 섞이지 않고 묶여 나온다.
        assert cats == sorted(cats, key=lambda c: cats.index(c))

    def test_선택지에_점수가_없다(self, client, played):
        """평가는 선택형이다(3.4). 점수 필드가 생기면 설계가 무너진다."""
        res = client.get(OPTIONS, headers=_headers(played["owner"]))
        for option in res.json():
            assert set(option) == {"code", "category", "label"}


class TestSubmitReview:
    def _submit(self, client, played, actor, reviewee, codes=("manner_time",)):
        return client.post(
            _reviews(played["id"]),
            json={"reviewee_id": str(reviewee), "option_codes": list(codes)},
            headers=_headers(actor),
        )

    def test_확정된_참가자끼리_평가한다(self, client, played):
        res = self._submit(client, played, played["owner"], played["mercenary"])
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["selected_codes"] == ["manner_time"]
        assert "score" not in body and "rating" not in body   # 점수가 없다

        assert len(reviews_of(played["id"])) == 1

    def test_같은_상대를_두_번_평가할_수_없다(self, client, played):
        assert self._submit(
            client, played, played["owner"], played["mercenary"]
        ).status_code == 201

        res = self._submit(client, played, played["owner"], played["mercenary"])
        assert res.status_code == 409
        assert error_code(res) == "ALREADY_REVIEWED"

    def test_자기_자신은_평가할_수_없다(self, client, played):
        res = self._submit(client, played, played["owner"], played["owner"])
        assert res.status_code == 422
        assert error_code(res) == "SELF_REVIEW"

    def test_참가자가_아니면_403_이다(self, client, played):
        res = self._submit(client, played, played["outsider"], played["mercenary"])
        assert res.status_code == 403
        assert error_code(res) == "FORBIDDEN"

    def test_대상이_참가자가_아니면_422_다(self, client, played):
        res = self._submit(client, played, played["owner"], played["outsider"])
        assert res.status_code == 422
        assert error_code(res) == "NOT_A_PARTICIPANT"

    def test_없는_선택지는_422_다(self, client, played):
        res = self._submit(
            client, played, played["owner"], played["mercenary"], codes=("nope",)
        )
        assert res.status_code == 422
        assert error_code(res) == "UNKNOWN_OPTION"

    def test_없는_경기는_404_다(self, client, played):
        res = client.post(
            _reviews(uuid4()),
            json={"reviewee_id": str(played["mercenary"]), "option_codes": ["manner_time"]},
            headers=_headers(played["owner"]),
        )
        assert res.status_code == 404
        assert error_code(res) == "MATCH_NOT_FOUND"


class TestReviewWindow:
    """🔴 경기 후 **14일**. 정어진이 2026-09-04 에 정했다."""

    def _submit(self, client, match_id, actor, reviewee):
        return client.post(
            f"{V1}/matches/{match_id}/reviews",
            json={"reviewee_id": str(reviewee), "option_codes": ["manner_time"]},
            headers=_headers(actor),
        )

    def _match_at(self, days_ago):
        match_id, owner, mercenary = uuid4(), uuid4(), uuid4()
        register_match(
            match_id, datetime.now(timezone.utc) - timedelta(days=days_ago)
        )
        register_confirmed(match_id, owner)
        register_confirmed(match_id, mercenary)
        return match_id, owner, mercenary

    def test_아직_안_끝난_경기는_422_다(self, client, played):
        match_id, owner, mercenary = self._match_at(-1)   # 내일 경기
        res = self._submit(client, match_id, owner, mercenary)
        assert res.status_code == 422
        assert error_code(res) == "MATCH_NOT_PLAYED"

    def test_13일_지난_경기는_평가된다(self, client, played):
        match_id, owner, mercenary = self._match_at(13)
        assert self._submit(client, match_id, owner, mercenary).status_code == 201

    def test_15일_지난_경기는_닫힌다(self, client, played):
        match_id, owner, mercenary = self._match_at(15)
        res = self._submit(client, match_id, owner, mercenary)
        assert res.status_code == 422
        assert error_code(res) == "REVIEW_WINDOW_CLOSED"

    def test_안_끝난_것과_늦은_것을_가른다(self, client, played):
        """화면이 '아직입니다'와 '늦었습니다'를 다르게 안내해야 한다."""
        early, o1, m1 = self._match_at(-1)
        late, o2, m2 = self._match_at(30)
        assert error_code(self._submit(client, early, o1, m1)) == "MATCH_NOT_PLAYED"
        assert error_code(self._submit(client, late, o2, m2)) == "REVIEW_WINDOW_CLOSED"


class TestNoShow:
    """🔴 주최 팀 주장만. 제재 기록이라 만들 수 있는 사람을 좁혔다."""

    def _record(self, client, played, actor, target):
        return client.post(
            _no_shows(played["id"]),
            json={"user_id": str(target)},
            headers=_headers(actor),
        )

    def test_주장은_기록할_수_있다(self, client, played):
        res = self._record(client, played, played["owner"], played["mercenary"])
        assert res.status_code == 201, res.text
        assert len(no_shows()) == 1

    def test_참가자라도_주장이_아니면_못_한다(self, client, played):
        res = self._record(client, played, played["mercenary"], played["owner"])
        assert res.status_code == 403
        assert error_code(res) == "FORBIDDEN"
        assert no_shows() == []

    def test_경기당_1인_1건이다(self, client, played):
        assert self._record(
            client, played, played["owner"], played["mercenary"]
        ).status_code == 201
        res = self._record(client, played, played["owner"], played["mercenary"])
        assert res.status_code == 409
        assert error_code(res) == "ALREADY_RECORDED"

    def test_확정자가_아니면_422_다(self, client, played):
        res = self._record(client, played, played["owner"], played["outsider"])
        assert res.status_code == 422
        assert error_code(res) == "NOT_A_PARTICIPANT"


class TestReport:
    def test_신고를_접수한다(self, client, played):
        res = client.post(
            REPORTS,
            json={"target_user_id": str(played["mercenary"]), "reason": "폭언"},
            headers=_headers(played["owner"]),
        )
        assert res.status_code == 201, res.text
        assert set(res.json()) == {"id", "target_user_id", "created_at"}
        assert len(reports()) == 1

    def test_신고_내용을_되돌려주지_않는다(self, client, played):
        res = client.post(
            REPORTS,
            json={"target_user_id": str(played["mercenary"]), "reason": "폭언"},
            headers=_headers(played["owner"]),
        )
        assert "reason" not in res.json()

    def test_평가를_안_해도_신고할_수_있다(self, client, played):
        """🔴 제재는 평가와 분리돼 있다(3.5). 여기가 그 경계다."""
        assert reviews_of(played["id"]) == []
        res = client.post(
            REPORTS,
            json={"target_user_id": str(played["mercenary"]), "reason": "불성실"},
            headers=_headers(played["outsider"]),   # 참가자도 아니다
        )
        assert res.status_code == 201

    def test_자기_자신은_신고할_수_없다(self, client, played):
        res = client.post(
            REPORTS,
            json={"target_user_id": str(played["owner"]), "reason": "x"},
            headers=_headers(played["owner"]),
        )
        assert res.status_code == 422
        assert error_code(res) == "SELF_REPORT"

    def test_인증이_필요하다(self, client):
        res = client.post(
            REPORTS, json={"target_user_id": str(uuid4()), "reason": "x"}
        )
        assert res.status_code == 401
