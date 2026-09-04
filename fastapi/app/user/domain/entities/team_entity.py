"""`team` 과 그 구성원. 부록 D 도메인 ①."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.user.domain.value_objects.team_role_vo import TeamRole


@dataclass(frozen=True)
class TeamEntity:
    """팀 1개.

    **종목은 팀이 정한다**(5장 SFR-010) — 경기에 종목 컬럼을 따로 두지 않고
    `match -> team -> sport_code` 로 결정된다(부록 D.4).
    """

    id: UUID
    name: str
    region: str
    sport_code: str


@dataclass(frozen=True)
class TeamMemberEntity:
    """지금 소속된 구성원 1명.

    나간 사람은 여기 담지 않는다 — `team_member` 는 `left_at` 으로 소프트 삭제라
    거르는 것은 도메인 규칙의 몫이다(`membership_rules.active_memberships` 와 같은 결).
    """

    user_id: UUID
    nickname: str
    role: TeamRole
    joined_at: datetime
    # 그 사람의 선수 카드. **없을 수 있다** — 카드를 안 만든 구성원도 팀에는
    # 있는 사람이라 목록에서 빼지 않는다(미결 `paik` 2번의 「하지 말 것」).
    #
    # 🔴 둘을 함께 싣는 이유: 스쿼드 등재(`POST /teams/{id}/squad/members`)는
    # 내부 id 를 받고, 카드로 가는 링크는 `public_slug` 를 쓴다. 하나만 주면
    # 화면이 나머지를 얻을 경로가 없다 — 남의 카드를 슬러그로 찾을 수도,
    # 내부 id 로 열 수도 없기 때문이다.
    player_card_id: UUID | None = None
    card_public_slug: str | None = None
