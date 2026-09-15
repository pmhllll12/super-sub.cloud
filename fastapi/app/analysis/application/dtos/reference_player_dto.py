"""선수 목록·관절 결과 조회 DTO. `paik` 29번."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

# 관절(skeleton) 봉투는 그대로 통과시킨다(에이전트가 낸 것을 다시 뽑거나
# 줄이지 않는다 — `ho` 30번 「하지 말 것」과 같은 이유) — 그래서 여기서는
# 필드를 하나하나 다시 모델링하지 않고 원시 dict로 다룬다. HTTP 경계에서만
# `SkeletonResponse`(스키마)로 형태를 검증한다.
SkeletonResult = dict[str, Any]

_NO_SKELETON: SkeletonResult = {
    "known": False,
    "why": "이 리포트는 관절 데이터가 없습니다.",
}


def no_skeleton() -> SkeletonResult:
    """리포트는 있지만 `skeleton` 키가 없을 때(옛 스키마, `schema_version`
    1.4 이전) — 없는 것을 있는 척하지 않고 명시적으로 "모른다"고 답한다.
    """
    return dict(_NO_SKELETON)


@dataclass(frozen=True)
class ListReferencePlayersQuery:
    pass


@dataclass(frozen=True)
class ReferencePlayerResult:
    id: str
    name: str


@dataclass(frozen=True)
class GetReferencePlayerSkeletonQuery:
    player_id: str


@dataclass(frozen=True)
class GetVideoSkeletonQuery:
    video_id: UUID
    user_id: UUID
