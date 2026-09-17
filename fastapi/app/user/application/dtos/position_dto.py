"""포지션 목록 조회 DTO."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ListPositionsQuery:
    """`sport_code` 가 있으면 그 종목만, 없으면 전 종목."""

    sport_code: str | None = None


@dataclass(frozen=True)
class PositionResult:
    sport_code: str
    code: str
    label: str
