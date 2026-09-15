"""지인 신청·수락을 **실제 PostgreSQL** 에 대고 확인한다. 미결 `jin` 35번.

스텁이 답할 수 없는 것들이다:

- 🔴 신청이 상대에게 `notification`(다른 컨텍스트 테이블, 원시 SQL로 씀)을
  실제로 남기는가 — 신청·알림이 같은 트랜잭션인가
- 유일 제약 `uq_user_contact_pair`가 같은 방향 중복 신청을 막는가
- `find_contact`가 **방향 무관**으로 기존 관계를 찾는가(B→A 중복 신청 방지)
- 수락하면 양쪽 다 `list_accepted_contacts`에서 서로를 보는가, `note`는 신청자
  쪽에만 실리는가
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from tests.conftest import V1, error_code

pytestmark = pytest.mark.db

PASSWORD = "supersub2026"


def _account(db_client, nickname):
    nickname = f"{nickname}{uuid.uuid4().hex[:6]}"
    email = f"contact-{uuid.uuid4().hex[:12]}@super-sub.example"
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
def pair(db_client, db_session):
    """지인 신청을 주고받을 두 사람. 끝나면 계정·지인 관계·알림을 전부 지운다."""
    a = _account(db_client, "가")
    b = _account(db_client, "나")

    yield {"a": a, "b": b}

    ids = [str(a["id"]), str(b["id"])]
    db_session.execute(
        text("delete from notification where recipient_user_id = any(:u)"),
        {"u": ids},
    )
    db_session.execute(
        text(
            "delete from user_contact where requester_user_id = any(:u)"
            " or target_user_id = any(:u)"
        ),
        {"u": ids},
    )
    db_session.execute(text('delete from "user" where id = any(:u)'), {"u": ids})
    db_session.commit()


class TestRequestInDb:
    def test_신청과_알림이_같이_생긴다(self, db_client, db_session, pair):
        res = db_client.post(
            f"{V1}/me/contacts",
            json={"target_user_id": str(pair["b"]["id"]), "note": "같은 동네"},
            headers=pair["a"]["headers"],
        )
        assert res.status_code == 201, res.text
        contact_id = uuid.UUID(res.json()["id"])

        row = db_session.execute(
            text(
                "select requester_user_id, target_user_id, note, accepted_at"
                " from user_contact where id = :i"
            ),
            {"i": contact_id},
        ).one()
        assert str(row.requester_user_id) == str(pair["a"]["id"])
        assert row.note == "같은 동네"
        assert row.accepted_at is None

        notif = db_session.execute(
            text(
                "select type, actor_user_id, subject_type, subject_id"
                " from notification where recipient_user_id = :r"
            ),
            {"r": pair["b"]["id"]},
        ).one()
        assert notif.type == "contact_request"
        assert str(notif.actor_user_id) == str(pair["a"]["id"])
        assert notif.subject_type == "user_contact"
        assert str(notif.subject_id) == str(contact_id)

    def test_같은_방향_중복_신청은_409(self, db_client, pair):
        db_client.post(
            f"{V1}/me/contacts",
            json={"target_user_id": str(pair["b"]["id"])},
            headers=pair["a"]["headers"],
        )
        res = db_client.post(
            f"{V1}/me/contacts",
            json={"target_user_id": str(pair["b"]["id"])},
            headers=pair["a"]["headers"],
        )
        assert res.status_code == 409
        assert error_code(res) == "ALREADY_REQUESTED"

    def test_반대_방향_신청도_409(self, db_client, pair):
        """A→B 신청이 있으면 B→A 신청도 막는다 — `find_contact`는 방향 무관이다."""
        db_client.post(
            f"{V1}/me/contacts",
            json={"target_user_id": str(pair["b"]["id"])},
            headers=pair["a"]["headers"],
        )
        res = db_client.post(
            f"{V1}/me/contacts",
            json={"target_user_id": str(pair["a"]["id"])},
            headers=pair["b"]["headers"],
        )
        assert res.status_code == 409
        assert error_code(res) == "ALREADY_REQUESTED"


class TestAcceptInDb:
    def test_수락하면_양쪽_다_서로를_본다(self, db_client, pair):
        req = db_client.post(
            f"{V1}/me/contacts",
            json={"target_user_id": str(pair["b"]["id"]), "note": "같은 동네"},
            headers=pair["a"]["headers"],
        )
        contact_id = req.json()["id"]

        accept = db_client.post(
            f"{V1}/me/contacts/{contact_id}/accept", headers=pair["b"]["headers"]
        )
        assert accept.status_code == 200, accept.text
        assert accept.json()["accepted_at"] is not None

        a_list = db_client.get(f"{V1}/me/contacts", headers=pair["a"]["headers"]).json()
        b_list = db_client.get(f"{V1}/me/contacts", headers=pair["b"]["headers"]).json()

        assert [i["user_id"] for i in a_list["items"]] == [str(pair["b"]["id"])]
        assert [i["user_id"] for i in b_list["items"]] == [str(pair["a"]["id"])]

        # note는 신청자(a)쪽에서만 보인다 — b가 보는 목록에는 없다.
        assert a_list["items"][0]["note"] == "같은 동네"
        assert b_list["items"][0]["note"] is None

    def test_대상이_아니면_403(self, db_client, pair):
        req = db_client.post(
            f"{V1}/me/contacts",
            json={"target_user_id": str(pair["b"]["id"])},
            headers=pair["a"]["headers"],
        )
        contact_id = req.json()["id"]

        # 신청자 본인은 자기 신청을 수락할 수 없다.
        res = db_client.post(
            f"{V1}/me/contacts/{contact_id}/accept", headers=pair["a"]["headers"]
        )
        assert res.status_code == 403
        assert error_code(res) == "FORBIDDEN"

    def test_이미_수락됐으면_409(self, db_client, pair):
        req = db_client.post(
            f"{V1}/me/contacts",
            json={"target_user_id": str(pair["b"]["id"])},
            headers=pair["a"]["headers"],
        )
        contact_id = req.json()["id"]
        db_client.post(
            f"{V1}/me/contacts/{contact_id}/accept", headers=pair["b"]["headers"]
        )
        res = db_client.post(
            f"{V1}/me/contacts/{contact_id}/accept", headers=pair["b"]["headers"]
        )
        assert res.status_code == 409
        assert error_code(res) == "ALREADY_ACCEPTED"


class TestListRequestsInDb:
    def test_대상에게만_대기중_신청이_보인다(self, db_client, pair):
        db_client.post(
            f"{V1}/me/contacts",
            json={"target_user_id": str(pair["b"]["id"])},
            headers=pair["a"]["headers"],
        )
        incoming = db_client.get(
            f"{V1}/me/contacts/requests", headers=pair["b"]["headers"]
        ).json()
        assert [r["requester_user_id"] for r in incoming] == [str(pair["a"]["id"])]

        outgoing = db_client.get(
            f"{V1}/me/contacts/requests", headers=pair["a"]["headers"]
        ).json()
        assert outgoing == []
