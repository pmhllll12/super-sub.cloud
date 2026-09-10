"""용병 매칭용 프로필. `user` 테이블 위에 얹은 별도 개념이다.

`UserEntity`에 필드를 더 얹지 않는 이유: 로그인·토큰 검증 등 `user`가 관여하는
모든 경로가 임베딩(768 floats)까지 매번 읽고 다니게 된다. 이 프로필을 실제로
쓰는 경로(내 프로필 수정·후보 검색)만 이 엔티티를 다룬다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class AvailableSlot:
    day: str  # "MON".."SUN"
    start: str  # "HH:MM"
    end: str  # "HH:MM"


@dataclass(frozen=True)
class PositionRef:
    """포지션 약칭은 종목 간 겹친다(`position` 테이블 주석 — 축구 FW ≠ 농구 FW).

    그래서 `sport_code`를 같이 들고 다닌다. 저장소(PG 구현)가 이 쌍을
    `"<sport_code>:<code>"` 문자열로 인코딩해 `ARRAY(String)` 컬럼에 담는다 —
    이 인코딩은 어댑터 안의 사정이고 도메인은 쌍으로만 다룬다.
    """

    sport_code: str
    code: str


@dataclass(frozen=True)
class MercenaryProfileEntity:
    user_id: UUID
    preferred_positions: list[PositionRef] = field(default_factory=list)
    available_slots: list[AvailableSlot] = field(default_factory=list)
    location: str | None = None
    skill_summary: str | None = None
    is_searchable: bool = False
    # 검색 결과에는 안 실어 보낸다(응답 크기·모델 결합도 때문) — 저장·재계산에만 쓴다.
    skill_embedding: list[float] | None = None
