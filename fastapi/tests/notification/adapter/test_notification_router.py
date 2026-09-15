"""notification/adapter/inbound/api/v1/notification_router.py — 계약 문서 3-12절."""

from __future__ import annotations

import uuid

from tests.conftest import V1


class TestListNotifications:
    def test_인증_없으면_401(self, client):
        res = client.get(f"{V1}/me/notifications")
        assert res.status_code == 401

    def test_스텁_고정_알림이_보인다(self, client, auth):
        res = client.get(f"{V1}/me/notifications", headers=auth)
        assert res.status_code == 200, res.text
        body = res.json()
        assert len(body) == 1
        assert body[0]["type"] == "contact_request"
        assert body[0]["read_at"] is None

    def test_unread_only_로_걸러도_그대로_보인다(self, client, auth):
        res = client.get(
            f"{V1}/me/notifications", params={"unread_only": True}, headers=auth
        )
        assert res.status_code == 200
        assert len(res.json()) == 1


class TestMarkRead:
    def test_성공하면_read_at이_찬다(self, client, auth):
        notification_id = "6e1a2b3c-4d5e-4f60-8a71-2b3c4d5e6f70"
        res = client.patch(
            f"{V1}/me/notifications/{notification_id}/read", headers=auth
        )
        assert res.status_code == 200, res.text
        assert res.json()["read_at"] is not None

    def test_없는_알림이면_404(self, client, auth):
        res = client.patch(
            f"{V1}/me/notifications/{uuid.uuid4()}/read", headers=auth
        )
        assert res.status_code == 404
