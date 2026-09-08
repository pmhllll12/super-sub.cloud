"""영상 출력 포트.

🔴 **`sport` 는 `user` 컨텍스트의 테이블이다.** 포트에 `sport_exists` 가 있어도
`analysis` 가 `user` 를 임포트하는 것은 아니다 — 구현이 `table()`/`column()`
원시 쿼리로 필요한 컬럼만 읽는다(경기가 `team` 을 읽는 것과 같은 방식).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from abc import ABC, abstractmethod

from app.analysis.application.dtos.video_dto import UNSET
from app.analysis.domain.entities.video_entity import VideoEntity


class VideoPort(ABC):
    @abstractmethod
    def sport_exists(self, sport_code: str) -> bool: ...

    @abstractmethod
    def register(self, video: VideoEntity) -> None:
        """`video` 와 `video_validation` 을, 통과했으면 `analysis_job` 까지
        **같은 트랜잭션에서** 만든다.

        🔴 셋이 갈리면 안 된다. 검사 결과 없는 영상이 남으면 "검사를 안 한 것"과
        구별되지 않고(SFR-001), 통과했는데 작업이 없으면 분석이 영영 시작되지
        않는데 화면에는 통과로 보인다.

        만들 작업의 id 는 `video.analysis_job_id` 가 들고 온다 — 반려면 None 이다.
        """

    @abstractmethod
    def list_by_user(self, user_id: UUID) -> list[VideoEntity]:
        """그 사람의 영상. **최근 것이 앞에 온다.**

        검사 결과와 **가장 최근** 분석 작업의 상태를 함께 채운다 — `/videos`
        화면 한 줄이 그 셋을 같이 보여주기 때문이다.
        """

    @abstractmethod
    def get(self, video_id: UUID) -> VideoEntity | None:
        """영상 1건. 업로더 구분 없이 — 소유 판단은 부르는 쪽이 한다."""

    @abstractmethod
    def update_video(
        self,
        video_id: UUID,
        user_id: UUID,
        *,
        is_public: bool | Any = UNSET,
        title: str | None | Any = UNSET,
        description: str | None | Any = UNSET,
    ) -> VideoEntity | None:
        """클립을 부분 수정하고 갱신된 영상을 돌려준다.

        `UNSET` 인 필드는 건드리지 않는다. **`user_id` 로 소유를 확인한다** —
        남의 클립이거나 없는 클립이면 `None`.
        """

    @abstractmethod
    def delete(self, video_id: UUID, user_id: UUID) -> VideoEntity | None:
        """영상 행을 지우고 지운 영상을 돌려준다(S3 정리에 `storage_key` 가 필요).

        `video_validation`·`analysis_job`(·그 하위)은 외래키 `ON DELETE CASCADE`
        로 따라 지워진다(SEC-006). **`user_id` 로 소유를 확인한다** — 남의/없는
        클립이면 `None`.
        """

    @abstractmethod
    def list_public(self, limit: int) -> list[VideoEntity]:
        """공개된 클립. **최근 것이 앞에 온다.** 업로더 구분 없이 훑는다.

        홈의 영상 모음이 쓴다. 반려 사유·분석 상태는 채우지 않는다 — 목록이
        보여주지 않는다.
        """
