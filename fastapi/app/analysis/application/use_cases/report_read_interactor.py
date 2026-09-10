"""리포트 조회 인터랙터. 미결 `jin` 27번 · `paik` 7번."""

from __future__ import annotations

from app.analysis.application.dtos.report_view_dto import ReadReportQuery, ReportView
from app.analysis.application.ports.input.report_read_use_case import (
    ReadReportUseCase,
)
from app.analysis.application.ports.output.report_read_port import ReportReadPort
from app.analysis.application.ports.output.video_port import VideoPort
from app.core.errors import ApiError


class ReadReportInteractor(ReadReportUseCase):
    def __init__(
        self, repository: ReportReadPort, video_repository: VideoPort
    ) -> None:
        self._repository = repository
        self._video_repository = video_repository

    def __call__(self, query: ReadReportQuery) -> ReportView:
        view = self._repository.find_for_video(query.video_id, query.user_id)
        if view is not None:
            return view

        # 없는 이유를 가른다 — 영상 자체가 없거나 남의 것이면 404 VIDEO_NOT_FOUND
        # (존재 여부를 구별해 주지 않는 다른 경로와 같은 판단), 영상은 있는데
        # 적재가 안 됐으면 REPORT_NOT_READY(분석은 됐는데 화면이 못 찾는 상태).
        video = self._video_repository.get(query.video_id)
        if video is None or video.user_id != query.user_id:
            raise ApiError(404, "VIDEO_NOT_FOUND", "영상을 찾을 수 없습니다.")
        raise ApiError(
            404, "REPORT_NOT_READY", "아직 리포트가 준비되지 않았습니다."
        )
