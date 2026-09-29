"""포스터 뜨기가 **DB 커넥션을 쥔 채로 기다리지 않는다**.

🔴 **왜 있나** (2026-09-25, `paik`). 앱 홈에서 영상 줄이 통째로 안 나와서 재
봤더니, `GET /videos/public` 이 **정확히 30.00초** 무응답이었다 — 그때
SQLAlchemy 의 기본 `pool_timeout` 이 30초였다. 같은 순간 `/regions` 는 0.4초에
답했고, 같은 경로가 0.4초 ~ 30초로 널뛰었다. **죽은 것이 아니라 줄을 서
있었다.**

줄을 세운 것은 포스터였다: 요청당 세션 하나라 커넥션이 요청 내내 잡혀 있는데,
`ffmpeg` 이 원격 주소를 읽는 데 **최대 20초**를 쓴다. 홈이 카드 다섯 장을 한
번에 부르고 웹·앱이 겹치면 풀이 금세 비고, 그러면 **상관없는 요청들이**
커넥션을 기다린다.

고친 방식은 「느린 일 앞에서 커넥션을 돌려준다」(`VideoPort.release`)이고,
이 파일이 그 한 줄을 지킨다. ⛔ 지우지 말 것.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.analysis.application.dtos.video_dto import GetVideoPosterCommand
from app.analysis.application.use_cases.video_interactors import (
    GetVideoPosterInteractor,
)
from app.core.errors import ApiError


class _Repo:
    """필요한 것만 흉내낸다 — `release()` 가 **언제** 불렸는지만 본다."""

    def __init__(self, video: object | None) -> None:
        self._video = video
        self.released = False

    def get(self, video_id: UUID) -> object | None:  # noqa: ARG002
        return self._video

    def release(self) -> None:
        self.released = True


class _Video:
    def __init__(self, user_id: UUID, *, is_public: bool) -> None:
        self.user_id = user_id
        self.is_public = is_public
        self.storage_key = "videos/x.mp4"


class _Storage:
    def create_download_url(self, key: str) -> tuple[str, int]:  # noqa: ARG002
        return ("https://example.invalid/x.mp4", 60)


class _Poster:
    """🔴 **뜨는 그 순간에** 커넥션이 이미 돌아갔는지 본다."""

    def __init__(self, repo: _Repo) -> None:
        self._repo = repo
        self.released_when_captured: bool | None = None

    def capture(self, media_url: str) -> bytes | None:  # noqa: ARG002
        self.released_when_captured = self._repo.released
        return b"\xff\xd8jpeg"


class _Cache:
    def __init__(self) -> None:
        self._data: dict[UUID, bytes] = {}

    def get(self, video_id: UUID) -> bytes | None:
        return self._data.get(video_id)

    def put(self, video_id: UUID, jpeg: bytes) -> None:
        self._data[video_id] = jpeg


def test_느린_ffmpeg_앞에서_커넥션을_돌려준다() -> None:
    me = uuid4()
    repo = _Repo(_Video(me, is_public=False))
    poster = _Poster(repo)
    interactor = GetVideoPosterInteractor(repo, _Storage(), poster, _Cache())

    interactor(GetVideoPosterCommand(video_id=uuid4(), user_id=me))

    assert poster.released_when_captured is True, (
        "ffmpeg 이 도는 동안 DB 커넥션을 쥐고 있으면 풀이 비고, "
        "상관없는 요청들이 pool_timeout 만큼 멈춘다"
    )


def test_캐시에_있으면_뜨지도_돌려주지도_않는다() -> None:
    """🔴 **값싼 길에는 아무 일도 안 한다** — 캐시 적중이 이 설계의 전부다."""
    me = uuid4()
    video_id = uuid4()
    repo = _Repo(_Video(me, is_public=False))
    poster = _Poster(repo)
    cache = _Cache()
    cache.put(video_id, b"\xff\xd8cached")

    result = GetVideoPosterInteractor(repo, _Storage(), poster, cache)(
        GetVideoPosterCommand(video_id=video_id, user_id=me)
    )

    assert result.cached is True
    assert poster.released_when_captured is None, "캐시에 있는데 떴다"


def test_권한이_없으면_돌려주기_전에_막는다() -> None:
    """🔴 **권한이 캐시보다 먼저다** — 뒤에 두면 한 번 떠 둔 비공개 클립의
    장면이 아무에게나 나간다."""
    repo = _Repo(_Video(uuid4(), is_public=False))
    poster = _Poster(repo)

    with pytest.raises(ApiError) as caught:
        GetVideoPosterInteractor(repo, _Storage(), poster, _Cache())(
            GetVideoPosterCommand(video_id=uuid4(), user_id=uuid4())
        )

    assert caught.value.code == "VIDEO_NOT_FOUND"
    assert poster.released_when_captured is None
