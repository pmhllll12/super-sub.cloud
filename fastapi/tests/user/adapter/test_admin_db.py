"""회원 관리(admin)를 실제 PostgreSQL 로 확인한다. 계약 문서 3-2절.

**왜 DB 로 해야 하나.** 이 세 엔드포인트에는 파이썬이 잡아 주지 않는 자리가 둘 있다.

1. `has_card` 가 `card` 컨텍스트의 테이블을 `table()`/`column()` **원시 쿼리**로
   읽는다. 컨텍스트 경계를 지키려고 일부러 그렇게 한 것이지만, 그래서 `player_card`
   나 그 `user_id` 컬럼 이름이 바뀌어도 임포트가 깨지지 않는다 — 스텁으로 도는
   계약 테스트는 초록인 채로 운영에서 500 이 난다. 이 파일이 유일한 방어선이다.
   (`tests/card/adapter/test_card_db.py` 가 `user.nickname` 을 지키는 것과 같은 구조.)
2. `list_users` 의 검색·정렬·페이지네이션은 SQL 이 하는 일이다. 스텁 저장소에는
   사용자가 데모 하나뿐이라 페이지가 나뉘는 상황 자체를 만들 수 없다.

강제 탈퇴의 **성공 경로**도 여기 있다. 같은 이유로 스텁에서는 "남을 지운다"를
표현할 수 없다 (`tests/user/adapter/test_admin_router.py` 의 `TestForceDelete` 참고).
삭제 연쇄 자체는 `DELETE /me` 와 **같은** `repository.delete()` 를 타므로
`test_delete_me_db.py` 가 이미 넓게 검사한다 — 여기서는 관리자 경로로도 실제로
지워지는지만 확인한다.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.card.adapter.outbound.orm.player_card_orm import PlayerCardOrm
from app.core.config import settings
from tests.conftest import V1, error_code

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"


def _count(session, sql: str, params: dict) -> int:
    session.rollback()  # 다른 트랜잭션이 커밋한 결과를 읽는다
    return session.execute(text(sql), params).scalar_one()


def _signup(db_client, email: str, nickname: str) -> uuid.UUID:
    res = db_client.post(
        f"{V1}/auth/signup",
        json={"email": email, "password": PASSWORD, "nickname": nickname},
    )
    assert res.status_code == 201, res.text
    return uuid.UUID(res.json()["id"])


def _login(db_client, email: str) -> dict[str, str]:
    res = db_client.post(f"{V1}/auth/login", json={"email": email, "password": PASSWORD})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def pair(db_client, db_session):
    """관리자 하나와 대상 하나.

    둘의 이메일·닉네임에 **같은 표식**을 심어 두고 검색은 그 표식으로만 한다.
    DB 에 다른 계정이 몇 개 있든 결과가 흔들리지 않게 하기 위해서다.
    """
    marker = uuid.uuid4().hex[:10]
    admin_email = f"admin-{marker}@super-sub.example"
    target_email = f"target-{marker}@super-sub.example"
    # 대상 닉네임에 **역슬래시를 실제로 심는다.** 이스케이프 문자 자신이 검색어에
    # 들어오는 경우는 그것을 가진 데이터가 있어야만 검사할 수 있다
    # (`test_역슬래시가_섞여도_그_대상을_찾는다`).
    target_nickname = f"대상{marker}\\백"

    admin_id = _signup(db_client, admin_email, f"관리자{marker}")
    target_id = _signup(db_client, target_email, target_nickname)

    # 대상에게 카드를 준다 — `has_card` 가 읽는 원시 쿼리의 검사 대상이다.
    db_session.add(
        PlayerCardOrm(
            id=uuid.uuid4(),
            user_id=target_id,
            public_slug=f"slug-{uuid.uuid4().hex[:10]}",
            og_image_key="cards/x.png",
        )
    )
    # 정렬은 `created_at desc` 다. 가입이 같은 순간에 몰리면 순서가 흔들리므로
    # 대상 쪽을 하루 과거로 밀어 두 행의 앞뒤를 확정한다.
    db_session.execute(
        text('update "user" set created_at = :t where id = :u'),
        {"t": datetime.now(timezone.utc) - timedelta(days=1), "u": str(target_id)},
    )
    db_session.commit()

    original_admins = settings.admin_emails
    settings.admin_emails = admin_email
    try:
        yield {
            "marker": marker,
            "admin_id": admin_id,
            "admin_email": admin_email,
            "target_id": target_id,
            "target_email": target_email,
            "target_nickname": target_nickname,
            "headers": _login(db_client, admin_email),
            "target_headers": _login(db_client, target_email),
        }
    finally:
        settings.admin_emails = original_admins
        db_session.rollback()
        db_session.execute(
            text('delete from "user" where id in (:a, :t)'),
            {"a": str(admin_id), "t": str(target_id)},
        )
        db_session.commit()


class TestAdminGate:
    def test_화이트리스트에_없으면_FORBIDDEN(self, db_client, pair):
        """게이트가 이메일을 **실제 DB 에서** 읽는다 — 그 경로를 여기서 확인한다."""
        settings.admin_emails = ""
        res = db_client.get(f"{V1}/admin/users", headers=pair["headers"])
        assert res.status_code == 403
        assert error_code(res) == "FORBIDDEN"


class TestListUsers:
    def test_이메일과_닉네임_모두로_찾는다(self, db_client, pair):
        by_email = db_client.get(
            f"{V1}/admin/users",
            headers=pair["headers"],
            params={"q": f"target-{pair['marker']}"},
        )
        assert by_email.status_code == 200
        assert [u["email"] for u in by_email.json()["items"]] == [pair["target_email"]]

        by_nickname = db_client.get(
            f"{V1}/admin/users", headers=pair["headers"], params={"q": f"관리자{pair['marker']}"}
        )
        assert by_nickname.status_code == 200
        assert [u["email"] for u in by_nickname.json()["items"]] == [pair["admin_email"]]

    def test_최근_가입_순이다(self, db_client, pair):
        res = db_client.get(
            f"{V1}/admin/users", headers=pair["headers"], params={"q": pair["marker"]}
        )
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 2
        # 대상은 하루 과거로 밀어 뒀다.
        assert [u["email"] for u in body["items"]] == [
            pair["admin_email"],
            pair["target_email"],
        ]

    def test_페이지가_나뉘어도_total_은_전체다(self, db_client, pair):
        first = db_client.get(
            f"{V1}/admin/users",
            headers=pair["headers"],
            params={"q": pair["marker"], "page": 1, "size": 1},
        )
        second = db_client.get(
            f"{V1}/admin/users",
            headers=pair["headers"],
            params={"q": pair["marker"], "page": 2, "size": 1},
        )
        assert first.status_code == second.status_code == 200
        assert first.json()["total"] == second.json()["total"] == 2
        assert len(first.json()["items"]) == len(second.json()["items"]) == 1
        assert first.json()["items"][0]["email"] == pair["admin_email"]
        assert second.json()["items"][0]["email"] == pair["target_email"]

    @pytest.mark.parametrize(
        "suffix",
        [
            "%",  # 이스케이프 안 하면 "표식으로 시작하는 전부"가 걸린다
            "_",  # 이스케이프 안 하면 임의의 한 글자와 맞는다
        ],
    )
    def test_LIKE_메타문자는_리터럴로_다룬다(self, db_client, pair, suffix):
        """검색어는 패턴이 아니라 글자다.

        표식 뒤에 메타문자를 붙이면 **리터럴로는 아무와도 안 맞는다.** 이스케이프가
        빠지면 이것들이 패턴으로 해석되어 앞의 두 계정이 그대로 걸린다.
        """
        res = db_client.get(
            f"{V1}/admin/users",
            headers=pair["headers"],
            params={"q": f"{pair['marker']}{suffix}"},
        )
        assert res.status_code == 200
        assert res.json()["total"] == 0

    def test_역슬래시가_섞여도_그_대상을_찾는다(self, db_client, pair):
        """이스케이프 문자 자신이 검색어에 들어온 경우.

        🔴 **"안 걸린다"로는 이것을 검사할 수 없다.** 역슬래시를 가진 데이터가 없으면
        이스케이프가 있든 없든 0건이라 통과해 버린다 — 그래서 대상 닉네임에 역슬래시를
        심어 두고 **걸리는 쪽**으로 확인한다. `_escape_like` 가 역슬래시를 먼저 바꾸지
        않으면 이 검색어는 다른 패턴이 되어 정작 대상을 놓친다.
        """
        res = db_client.get(
            f"{V1}/admin/users",
            headers=pair["headers"],
            params={"q": pair["target_nickname"]},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 1
        assert body["items"][0]["email"] == pair["target_email"]


class TestUserDetail:
    def test_has_card_는_실제_카드_테이블을_읽는다(self, db_client, pair):
        """`player_card` 를 원시 쿼리로 읽는 자리다 — 컬럼이 바뀌면 여기서만 걸린다."""
        target = db_client.get(f"{V1}/admin/users/{pair['target_id']}", headers=pair["headers"])
        assert target.status_code == 200
        assert target.json()["has_card"] is True

        admin = db_client.get(f"{V1}/admin/users/{pair['admin_id']}", headers=pair["headers"])
        assert admin.status_code == 200
        assert admin.json()["has_card"] is False


class TestForceDelete:
    def test_지우면_계정과_카드가_함께_사라진다(self, db_client, db_session, pair):
        res = db_client.delete(
            f"{V1}/admin/users/{pair['target_id']}", headers=pair["headers"]
        )
        assert res.status_code == 204

        target_id = str(pair["target_id"])
        assert _count(db_session, 'select count(*) from "user" where id = :u', {"u": target_id}) == 0
        assert (
            _count(
                db_session,
                "select count(*) from player_card where user_id = :u",
                {"u": target_id},
            )
            == 0
        )

    def test_지운_회원의_토큰은_막힌다(self, db_client, pair):
        db_client.delete(f"{V1}/admin/users/{pair['target_id']}", headers=pair["headers"])

        after = db_client.get(f"{V1}/me", headers=pair["target_headers"])
        assert after.status_code == 401
        assert error_code(after) == "INVALID_TOKEN"

    def test_자기_자신은_지울_수_없다(self, db_client, db_session, pair):
        res = db_client.delete(
            f"{V1}/admin/users/{pair['admin_id']}", headers=pair["headers"]
        )
        assert res.status_code == 409
        assert error_code(res) == "CANNOT_DELETE_SELF"
        assert (
            _count(
                db_session,
                'select count(*) from "user" where id = :u',
                {"u": str(pair["admin_id"])},
            )
            == 1
        )

    def test_누가_지웠는지_로그에_남는다(self, db_client, pair, caplog):
        """되돌릴 수 없는 동작이라 실행자가 남아야 한다 (5장 SEC-010).

        `supersub.auth` 로만 거른다 — 안 거르면 httpx 등 남의 로거가 섞인다.
        """
        with caplog.at_level(logging.INFO, logger="supersub.auth"):
            db_client.delete(
                f"{V1}/admin/users/{pair['target_id']}", headers=pair["headers"]
            )

        lines = [
            r.getMessage()
            for r in caplog.records
            if r.name == "supersub.auth" and "admin_force_delete" in r.getMessage()
        ]
        assert len(lines) == 1, caplog.text
        assert f"admin_id={pair['admin_id']}" in lines[0]
        assert f"user_id={pair['target_id']}" in lines[0]
