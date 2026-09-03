"""메모리 저장소와 가짜 객체 저장소. 계약 테스트가 DB·S3 없이 돌기 위한 것이다.

종목 목록은 마이그레이션(`20260901_sport_and_position`)이 넣는 값과 같다. 여기서
갈리면 스텁으로는 통과하고 실물에서 깨진다.
"""

from __future__ import annotations

from uuid import UUID

from app.analysis.application.ports.output.storage_port import StoragePort
from app.analysis.application.ports.output.video_port import VideoPort
from app.analysis.domain.entities.video_entity import VideoEntity

_SPORTS = ("football", "baseball", "basketball")

_VIDEOS: dict[UUID, VideoEntity] = {}
# 가짜 저장소에 "올라와 있는" 객체. 키 -> 크기(바이트).
_OBJECTS: dict[str, int] = {}


def reset_videos() -> None:
    _VIDEOS.clear()
    _OBJECTS.clear()


def put_object(storage_key: str, size_bytes: int) -> None:
    """검사가 "이 키에 이만한 파일이 올라와 있다"고 알려 준다.

    실제 업로드를 흉내 내는 자리다. 이것을 부르지 않으면 등록은
    `FILE_NOT_UPLOADED` 로 떨어진다 — 실물과 같은 동작이다.
    """
    _OBJECTS[storage_key] = size_bytes


class StubVideoRepository(VideoPort):
    def sport_exists(self, sport_code: str) -> bool:
        return sport_code in _SPORTS

    def register(self, video: VideoEntity) -> None:
        _VIDEOS[video.id] = video

    def list_by_user(self, user_id: UUID) -> list[VideoEntity]:
        mine = [v for v in _VIDEOS.values() if v.user_id == user_id]
        return sorted(mine, key=lambda v: v.created_at, reverse=True)


class FakeStorage(StoragePort):
    """URL 을 만들어 주지만 아무 데도 안 올라간다.

    ⚠️ **크기는 `put_object` 가 정한 값을 그대로 돌려준다.** 실물 S3 는 올라온
    바이트를 재므로, 여기서 통과했다고 실물에서 통과하는 것은 아니다 — 상한이
    실제로 걸리는지는 `tests/analysis/adapter/test_video_db.py` 가 본다.
    """

    TTL_SECONDS = 900

    def create_upload_url(self, storage_key: str, content_type: str) -> tuple[str, int]:
        return f"https://storage.invalid/{storage_key}", self.TTL_SECONDS

    def size_of(self, storage_key: str) -> int | None:
        return _OBJECTS.get(storage_key)
