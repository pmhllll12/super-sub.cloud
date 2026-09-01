"""user/adapter/inbound/api/v1/admin_router.py — 계약 문서 3-2절."""

from __future__ import annotations

from uuid import UUID

import pytest

from app.core.config import settings
from app.user.adapter.outbound.stub.user_stub_repository import (
    DEMO_EMAIL,
    DEMO_USER_ID,
)
from tests.conftest import V1, error_code


@pytest.fixture
def as_admin():
    """`auth` 로 로그인한 데모 계정을 관리자 화이트리스트에 잠깐 넣는다."""
    original = settings.admin_emails
    settings.admin_emails = DEMO_EMAIL
    try:
        yield
    finally:
        settings.admin_emails = original


class TestAdminGate:
    def test_헤더가_없으면_UNAUTHORIZED(self, client):
        res = client.get(f"{V1}/admin/users")
        assert res.status_code == 401
        assert error_code(res) == "UNAUTHORIZED"

    def test_관리자_목록에_없으면_FORBIDDEN(self, client, auth):
        # ADMIN_EMAILS 기본값은 비어 있다 — 로그인은 됐지만 관리자는 아니다.
        res = client.get(f"{V1}/admin/users", headers=auth)
        assert res.status_code == 403
        assert error_code(res) == "FORBIDDEN"


class TestListUsers:
    def test_관리자면_목록을_받는다(self, client, auth, as_admin):
        res = client.get(f"{V1}/admin/users", headers=auth)
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 1
        assert body["page"] == 1
        assert body["items"][0]["nickname"] == "홍길동"
        assert body["items"][0]["email"] == DEMO_EMAIL

    def test_검색어가_안_맞으면_빈_목록(self, client, auth, as_admin):
        res = client.get(f"{V1}/admin/users", headers=auth, params={"q": "없는사람"})
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 0
        assert body["items"] == []


class TestUserDetail:
    def test_상세는_나간_팀도_포함한다(self, client, auth, as_admin):
        res = client.get(f"{V1}/admin/users/{DEMO_USER_ID}", headers=auth)
        assert res.status_code == 200
        body = res.json()
        assert body["has_card"] is True
        assert {t["name"] for t in body["teams"]} == {"번개FC", "옛날FC"}
        left = next(t for t in body["teams"] if t["name"] == "옛날FC")
        assert left["left_at"] is not None

    def test_없는_회원이면_NOT_FOUND(self, client, auth, as_admin):
        other = UUID("00000000-0000-4000-8000-000000000000")
        res = client.get(f"{V1}/admin/users/{other}", headers=auth)
        assert res.status_code == 404
        assert error_code(res) == "USER_NOT_FOUND"


class TestForceDelete:
    """성공 경로(204)는 여기 없다 — 스텁 저장소에 사용자가 데모 하나뿐이라
    "남을 지운다"를 만들 수 없다. `tests/user/adapter/test_admin_db.py` 가 맡는다.
    """

    def test_자기_자신은_지울_수_없다(self, client, auth, as_admin):
        """지운 사람이 사라지면 감사 기록의 상대가 없어진다. 본인 탈퇴는 `DELETE /me` 다."""
        res = client.delete(f"{V1}/admin/users/{DEMO_USER_ID}", headers=auth)
        assert res.status_code == 409
        assert error_code(res) == "CANNOT_DELETE_SELF"

    def test_없는_회원이면_NOT_FOUND(self, client, auth, as_admin):
        other = UUID("00000000-0000-4000-8000-000000000000")
        res = client.delete(f"{V1}/admin/users/{other}", headers=auth)
        assert res.status_code == 404
        assert error_code(res) == "USER_NOT_FOUND"
