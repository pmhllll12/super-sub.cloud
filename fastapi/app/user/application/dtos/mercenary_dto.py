"""용병 매칭 프로필·검색 유스케이스가 주고받는 DTO.

🔴 도메인 엔티티(`PositionRef`·`AvailableSlot`)를 여기서 재사용하지 않는다 —
인바운드(라우터)가 커맨드를 만들려면 이 DTO의 타입을 알아야 하는데, 도메인
타입을 그대로 쓰면 라우터가 도메인을 직접 임포트하게 되어 계층 검사
(`test_인바운드는_도메인_엔티티와_규칙을_모른다`)에 걸린다. `app/match`의
`PositionNeedInput`과 같은 관례 — 모양이 같아도 DTO는 따로 둔다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class PositionRefDto:
    sport_code: str
    code: str


@dataclass(frozen=True)
class AvailableSlotDto:
    day: str
    start: str
    end: str


@dataclass(frozen=True)
class GetMercenaryProfileQuery:
    user_id: UUID


@dataclass(frozen=True)
class UpdateMercenaryProfileCommand:
    """전부 선택 필드다 — 보낸 것만 바꾼다(PATCH 의미).

    `None`은 "이 필드는 건드리지 않는다"는 뜻이라 "지운다"와 다르다. 값을
    지우고 싶으면 스키마 쪽에서 빈 리스트("")·빈 문자열 등 그 타입의 "없음"
    표현을 명시적으로 보내야 한다 — 자세한 규칙은 인터랙터 주석 참고.
    """

    user_id: UUID
    preferred_positions: list[PositionRefDto] | None = None
    available_slots: list[AvailableSlotDto] | None = None
    location: str | None = None
    skill_summary: str | None = None
    is_searchable: bool | None = None


@dataclass(frozen=True)
class MercenaryProfileResult:
    user_id: UUID
    preferred_positions: list[PositionRefDto] = field(default_factory=list)
    available_slots: list[AvailableSlotDto] = field(default_factory=list)
    location: str | None = None
    skill_summary: str | None = None
    is_searchable: bool = False


@dataclass(frozen=True)
class SearchCandidatesQuery:
    sport_code: str
    position_code: str
    # 자연어 그대로("주말 저녁 가능한 골키퍼, 공중볼 강한 사람") — 인터랙터가
    # 임베딩으로 바꾼다. www 챗봇처럼 이미 계산된 벡터를 클라이언트가 들고
    # 오지 않는다 — 클라이언트가 임의 벡터를 제출하면 검색 랭킹을 조작할 수
    # 있어서다(신뢰 경계는 서버 안쪽에 둔다).
    query_text: str
    limit: int = 10


@dataclass(frozen=True)
class CandidateResult:
    user_id: UUID
    nickname: str
    location: str | None
    skill_summary: str | None
    similarity: float
