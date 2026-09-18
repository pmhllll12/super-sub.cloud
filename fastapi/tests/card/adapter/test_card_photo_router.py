"""`POST /me/card/photo-upload-url` — 카드 사진 올릴 자리 (2026-09-18).

사용자 요청: 카드 사진을 바꾸면 **실제로 저장돼야** 한다. 여태 화면이
`FileReader` 로 읽어 브라우저 메모리에만 두었고 새로고침하면 사라졌다 —
계약에 담을 자리가 없었기 때문이다.

🔴 **바이트는 S3 로, 앱 서버를 지나지 않는다**(PER-002). 영상과 같은 방식이다.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.card.adapter.outbound.stub.card_photo_stub_storage import CardPhotoStubStorage
from app.card.adapter.outbound.stub.card_stub_repository import reset_created_cards
from app.card.dependencies.photo_storage_provider import (
    get_card_photo_storage,
    get_card_photo_storage_optional,
)
from app.main import app
from tests.conftest import V1, error_code

CARD = f"{V1}/me/card"
UPLOAD = f"{V1}/me/card/photo-upload-url"


@pytest.fixture(autouse=True)
def _clean():
    reset_created_cards()
    yield
    reset_created_cards()


@pytest.fixture(autouse=True)
def photos(client):
    """S3 없이 돌게 저장소를 갈아끼운다.

    🔴 **`tests/conftest.py` 를 안 고친다** — 공유 파일이라 건드리지 말라고
    `fastapi/CLAUDE.md` 가 적어 두었다. 여기서 `client` 를 받아 그 뒤에
    끼우면 된다(정리는 `client` 의 `finally` 가 한다).

    영상 쪽 `get_storage` 와 같은 이유다 — 버킷이 없어 나는 503 은 계약이
    아니라 **환경 문제**라 계약 시험이 그것을 재면 안 된다.
    """
    stub = CardPhotoStubStorage()
    app.dependency_overrides[get_card_photo_storage] = lambda: stub
    app.dependency_overrides[get_card_photo_storage_optional] = lambda: stub
    return stub


class TestPhotoUploadUrl:
    def test_인증이_필요하다(self, client):
        assert client.post(UPLOAD, json={"content_type": "image/jpeg"}).status_code == 401

    def test_올릴_주소와_키를_준다(self, client, auth):
        client.post(CARD, headers=auth)  # 카드가 있어야 한다
        res = client.post(UPLOAD, json={"content_type": "image/jpeg"}, headers=auth)
        assert res.status_code == 200, res.text

        body = res.json()
        assert body["upload_url"]
        assert body["storage_key"].startswith("cards/photos/")
        assert body["storage_key"].endswith(".jpg")
        assert body["expires_in"] > 0

    def test_카드가_없으면_404(self):
        """사진은 카드에 붙는 것이라 카드가 먼저다 — 키에 카드 id 가 들어간다.

        🔴 **라우터로는 못 잰다** — 계약 시험의 스텁 저장소는 데모 사용자에게
        카드를 이미 쥐여 주고 있어서 「카드 없음」 상태를 만들 수 없다. 그래서
        인터랙터를 직접 부른다.
        """
        from app.card.application.dtos.card_dto import CardPhotoUploadCommand
        from app.card.application.use_cases.card_photo_interactor import (
            CardPhotoUploadInteractor,
        )
        from app.core.errors import ApiError

        class _NoCard:
            def find_by_owner(self, user_id):
                return None

        interactor = CardPhotoUploadInteractor(_NoCard(), CardPhotoStubStorage())
        with pytest.raises(ApiError) as caught:
            interactor(
                CardPhotoUploadCommand(user_id=uuid4(), content_type="image/jpeg")
            )
        assert caught.value.status_code == 404
        assert caught.value.code == "CARD_NOT_FOUND"

    @pytest.mark.parametrize(
        "content_type", ["text/html", "application/pdf", "image/svg+xml", "video/mp4"]
    )
    def test_이미지가_아니면_422(self, client, auth, content_type):
        """🔴 **열어 두면 우리 버킷에 `.html` 을 올려 같은 도메인에서 연다.**

        사전 서명 PUT 은 내용을 검사하지 않는다 — 막는 곳이 여기뿐이다.
        `image/svg+xml` 도 막는다: SVG 는 스크립트를 담을 수 있다.
        """
        client.post(CARD, headers=auth)
        res = client.post(UPLOAD, json={"content_type": content_type}, headers=auth)
        assert res.status_code == 422
        assert error_code(res) == "UNSUPPORTED_PHOTO_TYPE"

    def test_부를_때마다_키가_다르다(self, client, auth):
        """🔴 같으면 **옛 사진을 조용히 덮는다** — 되돌릴 수 없다."""
        client.post(CARD, headers=auth)
        one = client.post(UPLOAD, json={"content_type": "image/jpeg"}, headers=auth)
        two = client.post(UPLOAD, json={"content_type": "image/jpeg"}, headers=auth)
        assert one.json()["storage_key"] != two.json()["storage_key"]


class TestPhotoKeyOwnership:
    """🔴 **남의 키를 내 카드에 못 붙인다.**

    키는 비밀이 아니다 — 응답에 실려 나간다. 사전 서명도 키만 알면 만들어지므로,
    저장 시점에 접두사를 대조하는 것이 유일한 방어선이다(영상의 `owns_key` 와
    같은 자리).
    """

    def _style(self, photo_key: str) -> dict:
        return {
            "bg": "#91ea92",
            "logo": "#0b0b0b",
            "text_color": "#0b0b0b",
            "text_x": 50,
            "text_y": 34,
            "brush": 0,
            "brush_color": "#0b0b0b",
            "brush_scale": 1,
            "brush_x": 0,
            "brush_y": 0,
            "photo_key": photo_key,
        }

    def test_내가_받은_키는_저장된다(self, client, auth):
        client.post(CARD, headers=auth)
        key = client.post(
            UPLOAD, json={"content_type": "image/jpeg"}, headers=auth
        ).json()["storage_key"]

        res = client.patch(CARD, json={"style": self._style(key)}, headers=auth)
        assert res.status_code == 200, res.text
        assert res.json()["style"]["photo_key"] == key

    def test_남의_자리의_키는_422(self, client, auth):
        client.post(CARD, headers=auth)
        stolen = "cards/photos/00000000-0000-0000-0000-000000000009/abc-1234.jpg"

        res = client.patch(CARD, json={"style": self._style(stolen)}, headers=auth)
        assert res.status_code == 422
        assert error_code(res) == "PHOTO_KEY_NOT_OWNED"

    def test_경로를_거슬러_올라가면_422(self, client, auth):
        me = client.post(CARD, headers=auth).json()["user"]["id"]
        res = client.patch(
            CARD,
            json={"style": self._style(f"cards/photos/{me}/../../etc/x.jpg")},
            headers=auth,
        )
        assert res.status_code == 422
        assert error_code(res) == "PHOTO_KEY_NOT_OWNED"
