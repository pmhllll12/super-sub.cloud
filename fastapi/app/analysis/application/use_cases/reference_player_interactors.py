"""선수 목록·관절 결과 인터랙터. `paik` 29번.

`skeleton`을 DB에 복제하지 않는다(정어진 판단) — 리포트 전체가 이미 S3에
있으니, 요청이 올 때마다 그 키로 읽어서 `skeleton`만 꺼낸다.
`StoragePort.read_object`(미결 `jin` 27번이 이미 같은 방식으로 씀)를 그대로
쓴다.
"""

from __future__ import annotations

import json

from app.analysis.application.dtos.reference_player_dto import (
    GetReferencePlayerSkeletonQuery,
    GetVideoSkeletonQuery,
    ListReferencePlayersQuery,
    ReferencePlayerResult,
    SkeletonResult,
    no_skeleton,
)
from app.analysis.application.ports.input.reference_player_use_cases import (
    GetReferencePlayerSkeletonUseCase,
    GetVideoSkeletonUseCase,
    ListReferencePlayersUseCase,
)
from app.analysis.application.ports.output.job_port import JobPort
from app.analysis.application.ports.output.reference_player_port import (
    ReferencePlayerPort,
)
from app.analysis.application.ports.output.storage_port import StoragePort
from app.analysis.application.ports.output.video_port import VideoPort
from app.core.errors import ApiError


def _skeleton_from_report(raw: bytes | None) -> SkeletonResult:
    """리포트 바이트에서 `skeleton`만 뽑는다. 없거나 못 읽으면 「모른다」로
    답한다 — 리포트 자체가 없는 것(호출부가 404로 가른다)과는 다른 상태다.
    """
    if raw is None:
        return no_skeleton()
    try:
        report = json.loads(raw)
    except ValueError:
        return no_skeleton()
    skeleton = report.get("skeleton")
    if not isinstance(skeleton, dict):
        return no_skeleton()
    return skeleton


class ListReferencePlayersInteractor(ListReferencePlayersUseCase):
    def __init__(self, repository: ReferencePlayerPort) -> None:
        self._repository = repository

    def __call__(
        self, query: ListReferencePlayersQuery
    ) -> list[ReferencePlayerResult]:
        return [
            ReferencePlayerResult(id=p.id, name=p.name)
            for p in sorted(self._repository.list_players(), key=lambda p: p.name)
        ]


class GetReferencePlayerSkeletonInteractor(GetReferencePlayerSkeletonUseCase):
    def __init__(
        self, repository: ReferencePlayerPort, storage: StoragePort
    ) -> None:
        self._repository = repository
        self._storage = storage

    def __call__(self, query: GetReferencePlayerSkeletonQuery) -> SkeletonResult:
        player = self._repository.find_player(query.player_id)
        if player is None:
            raise ApiError(404, "PLAYER_NOT_FOUND", "선수를 찾을 수 없습니다.")
        raw = self._storage.read_object(player.report_key)
        return _skeleton_from_report(raw)


class GetVideoSkeletonInteractor(GetVideoSkeletonUseCase):
    def __init__(
        self,
        video_repository: VideoPort,
        job_repository: JobPort,
        storage: StoragePort,
    ) -> None:
        self._video_repository = video_repository
        self._job_repository = job_repository
        self._storage = storage

    def __call__(self, query: GetVideoSkeletonQuery) -> SkeletonResult:
        # `ReadReportInteractor`와 같은 판단 — 영상이 없거나 남의 것이면
        # 404 VIDEO_NOT_FOUND(존재 여부를 구별해 주지 않는다), 분석이
        # `failed`면 ANALYSIS_FAILED(다시 기다려도 안 생긴다), 그 외 아직
        # 성공한 분석이 없으면 REPORT_NOT_READY.
        video = self._video_repository.get(query.video_id)
        if video is None or video.user_id != query.user_id:
            raise ApiError(404, "VIDEO_NOT_FOUND", "영상을 찾을 수 없습니다.")
        if video.analysis_status == "failed":
            raise ApiError(
                404,
                "ANALYSIS_FAILED",
                video.analysis_failure_reason or "분석에 실패했습니다.",
            )
        report_key = self._job_repository.get_latest_report_key(query.video_id)
        if report_key is None:
            raise ApiError(
                404, "REPORT_NOT_READY", "아직 리포트가 준비되지 않았습니다."
            )
        raw = self._storage.read_object(report_key)
        return _skeleton_from_report(raw)
