"""엔티티 → DTO 변환. **여기까지가 도메인의 마지막 지점이다.**"""

from __future__ import annotations

from app.card.application.dtos.squad_dto import SquadMemberResult, SquadResult
from app.card.domain.entities.squad_entity import SquadEntity


def to_squad_result(squad: SquadEntity) -> SquadResult:
    return SquadResult(
        id=squad.id,
        team_id=squad.team_id,
        public_slug=str(squad.public_slug),
        members=[
            SquadMemberResult(
                id=m.id,
                player_card_id=m.player_card_id,
                card_public_slug=m.card_public_slug,
                nickname=m.nickname,
                position_code=m.position_code,
                position_label=m.position_label,
            )
            for m in squad.members
        ],
    )
