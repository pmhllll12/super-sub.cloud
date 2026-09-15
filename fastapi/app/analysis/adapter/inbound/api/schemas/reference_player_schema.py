"""선수·관절(skeleton) HTTP 모델. 계약 문서. `paik` 29번."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ReferencePlayerResponse(BaseModel):
    """선수 한 명. **재생 주소는 없다** — 원본 영상이 S3에 없어서다. 화면은
    계속 정적 파일(`www/public/compare/`)로 재생한다.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str


class SkeletonResponse(BaseModel):
    """관절 시계열. `agent/report-contract.md`의 `skeleton` 절 그대로 —
    에이전트가 낸 값을 다시 뽑거나 줄이지 않는다.

    `known: false`면 `why`만 뜻이 있고 나머지는 비어 있다(리포트 자체가
    없는 404와는 다른, "리포트는 있지만 관절 데이터가 없다"는 200 상태다).

    🔴 `extra="allow"` — 에이전트 쪽 계약이 늘어도(minor 버전) 여기서 몰라서
    거부하지 않는다. 아는 필드만 타입을 검증한다.
    """

    model_config = ConfigDict(extra="allow")

    known: bool
    why: str | None = None
    fps: float | None = None
    frames: int | None = None
    frame_size: list[int] | None = None
    swing_leg: str | None = None
    direction: int | None = None
    keypoint_names: list[str] | None = None
    moments: dict[str, int] | None = None
    moments_seconds: dict[str, float] | None = None
    after_clipped: bool | None = None
    # 프레임당 COCO-17 × [x, y, confidence]. 못 잡은 프레임은 `null` —
    # 배열에서 빼지 않는다(인덱스가 곧 프레임 번호다).
    joints: list[list[list[float]] | None] | None = None
