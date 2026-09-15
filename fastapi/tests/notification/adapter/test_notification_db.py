"""알림 조회·읽음 처리를 **실제 PostgreSQL** 에 대고 확인한다. 미결 `jin` 35번.

알림 생성은 이 컨텍스트의 책임이 아니라서(포트 docstring 참고) 원시 SQL로
직접 넣는다 — `test_review_db.py`가 남의 컨텍스트(user) 행을 원시 SQL로
준비하는 것과 같은 이유다.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from tests.conftest import V1

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"


def _account(db_client, nickname):
    nickname = f"{nickname}{uuid.uuid4().hex[:6]}"
    email = f"notif-{uuid.uuid4().hex[:12]}@super-sub.example"
    signup = db_client.post(
        f"{V1}/auth/signup",
        json={"email": email, "password": PASSWORD, "nickname": nickname},
    )
    assert signup.status_code == 201, signup.text
    login = db_client.post(
        f"{V1}/auth/login", json={"email": email, "password": PASSWORD}
    )
    return {
        "id": uuid.UUID(signup.json()["id"]),
        "headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }


@pytest.fixture
def recipient(db_client, db_session):
    """알림 두 건(읽음/안읽음)을 가진 사람. 끝나면 알림·계정을 지운다."""
    person = _account(db_client, "받는이")
    older_id, newer_id = uuid.uuid4(), uuid.uuid4()
    db_session.execute(
        text(
            "insert into notification"
            " (id, recipient_user_id, type, read_at, created_at)"
            " values (:i, :r, 'contact_request', now(), now() - interval '1 hour')"
        ),
        {"i": older_id, "r": person["id"]},
    )
    db_session.execute(
        text(
            "insert into notification"
            " (id, recipient_user_id, type, read_at, created_at)"
            " values (:i, :r, 'contact_accepted', null, now())"
        ),
        {"i": newer_id, "r": person["id"]},
    )
    db_session.commit()

    yield {**person, "older_id": older_id, "newer_id": newer_id}

    db_session.execute(
        text("delete from notification where recipient_user_id = :u"),
        {"u": person["id"]},
    )
    db_session.execute(text('delete from "user" where id = :u'), {"u": person["id"]})
    db_session.commit()


class TestListInDb:
    def test_최신순이다(self, db_client, recipient):
        res = db_client.get(f"{V1}/me/notifications", headers=recipient["headers"])
        assert res.status_code == 200, res.text
        ids = [n["id"] for n in res.json()]
        assert ids == [str(recipient["newer_id"]), str(recipient["older_id"])]

    def test_unread_only가_읽은_것을_뺀다(self, db_client, recipient):
        res = db_client.get(
            f"{V1}/me/notifications",
            params={"unread_only": True},
            headers=recipient["headers"],
        )
        ids = [n["id"] for n in res.json()]
        assert ids == [str(recipient["newer_id"])]


class TestMarkReadInDb:
    def test_읽으면_DB에_반영되고_멱등이다(self, db_client, db_session, recipient):
        res = db_client.patch(
            f"{V1}/me/notifications/{recipient['newer_id']}/read",
            headers=recipient["headers"],
        )
        assert res.status_code == 200, res.text
        read_at = db_session.execute(
            text("select read_at from notification where id = :i"),
            {"i": recipient["newer_id"]},
        ).scalar_one()
        assert read_at is not None

        # 두 번째 호출은 이미 읽은 시각을 덮지 않는다(멱등).
        again = db_client.patch(
            f"{V1}/me/notifications/{recipient['newer_id']}/read",
            headers=recipient["headers"],
        )
        assert again.status_code == 200
        assert again.json()["read_at"] == res.json()["read_at"]

    def test_남의_알림이면_404(self, db_client, recipient):
        other = _account(db_client, "남")
        res = db_client.patch(
            f"{V1}/me/notifications/{recipient['newer_id']}/read",
            headers=other["headers"],
        )
        assert res.status_code == 404
