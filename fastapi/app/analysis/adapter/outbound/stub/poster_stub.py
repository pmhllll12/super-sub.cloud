"""시험용 포스터 — `ffmpeg` 도 바깥 망도 안 쓴다."""

from __future__ import annotations

from uuid import UUID

from app.analysis.application.ports.output.poster_cache_port import PosterCachePort
from app.analysis.application.ports.output.poster_port import PosterPort

#: 1×1 JPEG. 내용은 아무 뜻이 없다 — 계약 시험이 보는 것은 **바이트가 왔는가**와
#: 응답의 `Content-Type` 이지 그림 자체가 아니다.
TINY_JPEG = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300"
    "0806060706050806070707090908" + "0a" * 52 + "ffd9"
)


class StubPoster(PosterPort):
    def __init__(self, *, jpeg: bytes | None = TINY_JPEG) -> None:
        self._jpeg = jpeg
        #: 몇 번 실제로 떴는가 — **캐시가 도는지**를 시험이 이걸로 잰다.
        self.calls = 0

    def capture(self, media_url: str) -> bytes | None:
        self.calls += 1
        return self._jpeg


class MemoryPosterCache(PosterCachePort):
    """시험용 캐시 — 디스크를 안 쓴다.

    🔴 **`FsPosterCache` 를 시험에 쓰지 않는 까닭**: 그쪽은 임시 폴더에 남아서
    **시험끼리 결과가 새어 나간다**(앞 시험이 떠 둔 것을 뒤 시험이 캐시 적중으로
    읽는다). 캐시가 도는지를 재는 시험이라 그러면 판별력이 없어진다.
    """

    def __init__(self) -> None:
        self._items: dict[UUID, bytes] = {}

    def get(self, video_id: UUID) -> bytes | None:
        return self._items.get(video_id)

    def put(self, video_id: UUID, jpeg: bytes) -> None:
        self._items[video_id] = jpeg
