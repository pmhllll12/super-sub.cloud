"""엔티티 → DTO 변환. **여기까지가 도메인의 마지막 지점이다.**"""

from __future__ import annotations

from app.analysis.application.dtos.video_dto import VideoResult
from app.analysis.domain.entities.video_entity import VideoEntity


def to_video_result(video: VideoEntity) -> VideoResult:
    """검사 결과가 없는 영상은 **통과로 치지 않는다.**

    `passed` 를 기본 참으로 두면 검사에 실패해 결과가 안 남은 영상이 화면에서
    정상으로 보인다. 등록은 검사와 같은 트랜잭션이라 정상 경로에서는 항상
    결과가 있지만, 없을 때 조용히 통과가 되는 쪽이 더 나쁘다.
    """
    validation = video.validation
    return VideoResult(
        id=video.id,
        sport_code=video.sport_code,
        storage_key=video.storage_key,
        duration_ms=video.duration_ms,
        side=video.side,
        created_at=video.created_at,
        passed=bool(validation and validation.passed),
        reject_reason=validation.reject_reason if validation else None,
        analysis_job_id=video.analysis_job_id,
        analysis_status=video.analysis_status,
    )
