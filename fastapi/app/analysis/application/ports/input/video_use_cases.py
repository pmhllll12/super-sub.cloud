"""영상 입력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.analysis.application.dtos.video_dto import (
    MyVideosQuery,
    RegisterVideoCommand,
    UploadUrlCommand,
    UploadUrlResult,
    VideoResult,
)


class CreateUploadUrlUseCase(ABC):
    @abstractmethod
    def __call__(self, command: UploadUrlCommand) -> UploadUrlResult:
        """올릴 자리를 내준다. **아직 `video` 행을 만들지 않는다.**"""


class RegisterVideoUseCase(ABC):
    @abstractmethod
    def __call__(self, command: RegisterVideoCommand) -> VideoResult:
        """올린 클립을 등록하고 규격을 검사한다. **반려도 성공 응답이다.**"""


class ListMyVideosUseCase(ABC):
    @abstractmethod
    def __call__(self, query: MyVideosQuery) -> list[VideoResult]:
        """내 영상 목록. 분석 상태와 반려 사유가 함께 온다."""
