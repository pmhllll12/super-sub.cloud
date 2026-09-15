"""검출(`detect`) 작업 인터랙터. 미결 `ho` 44번 — 안 (가).

사람(화면)이 직접 부르는 자리다(`ClaimJobUseCase`/`FinishJobUseCase`는 워커
전용). 소유권 검사는 `ReadReportInteractor`와 같은 판단 — 없는 것과 남의
것을 구별해 주지 않는다(둘 다 404 `VIDEO_NOT_FOUND`).
"""

from __future__ import annotations

from app.analysis.application.dtos.job_dto import (
    DetectionStatusQuery,
    DetectionStatusResult,
    RequestDetectionCommand,
)
from app.analysis.application.ports.input.job_use_cases import (
    GetDetectionStatusUseCase,
    RequestDetectionUseCase,
)
from app.analysis.application.ports.output.job_port import JobPort
from app.analysis.application.ports.output.video_port import VideoPort
from app.analysis.domain.rules.job_rules import QUEUED
from app.core.errors import ApiError


def _check_owns(video_port: VideoPort, video_id, user_id) -> None:
    video = video_port.get(video_id)
    if video is None or video.user_id != user_id:
        raise ApiError(404, "VIDEO_NOT_FOUND", "영상을 찾을 수 없습니다.")


class RequestDetectionInteractor(RequestDetectionUseCase):
    def __init__(self, repository: JobPort, video_repository: VideoPort) -> None:
        self._repository = repository
        self._video_repository = video_repository

    def __call__(self, command: RequestDetectionCommand) -> DetectionStatusResult:
        _check_owns(self._video_repository, command.video_id, command.user_id)
        job_id = self._repository.create_detect_job(
            command.video_id, command.at_ms
        )
        return DetectionStatusResult(
            job_id=job_id,
            status=QUEUED,
            failure_reason=None,
            detection_result=None,
        )


class GetDetectionStatusInteractor(GetDetectionStatusUseCase):
    def __init__(self, repository: JobPort, video_repository: VideoPort) -> None:
        self._repository = repository
        self._video_repository = video_repository

    def __call__(self, query: DetectionStatusQuery) -> DetectionStatusResult:
        _check_owns(self._video_repository, query.video_id, query.user_id)
        detection = self._repository.get_latest_detection(query.video_id)
        if detection is None:
            raise ApiError(
                404, "DETECTION_NOT_FOUND", "검출 요청 이력이 없습니다."
            )
        return DetectionStatusResult(
            job_id=detection.job_id,
            status=detection.status,
            failure_reason=detection.failure_reason,
            detection_result=detection.detection_result,
        )
