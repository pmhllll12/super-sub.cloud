"""영상 입력 포트."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.analysis.application.dtos.video_dto import (
    AdminDeleteVideoCommand,
    AdminVideoListResult,
    AdminVideosQuery,
    DeleteVideoCommand,
    FeaturedVideoResult,
    GetFeaturedVideoCommand,
    GetPlaybackUrlCommand,
    KeepVideoCommand,
    MyVideosQuery,
    PlaybackUrlResult,
    PublicVideoResult,
    PublicVideosQuery,
    RegisterVideoCommand,
    UpdateVideoCommand,
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


class UpdateVideoUseCase(ABC):
    @abstractmethod
    def __call__(self, command: UpdateVideoCommand) -> VideoResult:
        """클립을 부분 수정한다(공개 여부·제목·설명). 남의/없는 클립이면 404."""


class ListPublicVideosUseCase(ABC):
    @abstractmethod
    def __call__(self, query: PublicVideosQuery) -> list[PublicVideoResult]:
        """공개된 클립 목록. 홈의 영상 모음이 쓴다."""


class GetPlaybackUrlUseCase(ABC):
    @abstractmethod
    def __call__(self, command: GetPlaybackUrlCommand) -> PlaybackUrlResult:
        """재생용 사전 서명 URL. 공개 클립이거나 자기 클립일 때만, 아니면 404."""


class GetFeaturedVideoUseCase(ABC):
    @abstractmethod
    def __call__(self, command: GetFeaturedVideoCommand) -> FeaturedVideoResult:
        """어떤 사람의 대표 영상. 로그인하면 누구나. 대표가 없으면 404 `NO_FEATURED_VIDEO`."""


class DeleteVideoUseCase(ABC):
    @abstractmethod
    def __call__(self, command: DeleteVideoCommand) -> None:
        """영상을 DB·S3 에서 지운다. 남의/없는 클립이면 404."""


class KeepVideoUseCase(ABC):
    @abstractmethod
    def __call__(self, command: KeepVideoCommand) -> VideoResult:
        """"프로필에 저장" — `kept` 를 켜고 임시 원본을 리포트 자리로 옮긴다.
        남의/없는 클립이면 404. 응답은 `GET /videos` 한 줄과 같다.
        """


class ListAdminVideosUseCase(ABC):
    @abstractmethod
    def __call__(self, query: AdminVideosQuery) -> AdminVideoListResult:
        """관리자가 한 사람(`?user=<uid|email>`)의 영상을 전부 본다. 없는
        사람이면 `404 USER_NOT_FOUND`.
        """


class AdminDeleteVideoUseCase(ABC):
    @abstractmethod
    def __call__(self, command: AdminDeleteVideoCommand) -> None:
        """관리자가 아무 영상이나 지운다(소유 검사 없음). 없는 클립이면 404."""
