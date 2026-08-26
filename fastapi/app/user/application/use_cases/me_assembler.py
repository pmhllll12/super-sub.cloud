"""엔티티 → `MeResult` 조립.

조회(`MeInteractor`)와 수정(`UpdateMeInteractor`)이 **같은 응답 형태**를 돌려주므로
조립을 한 곳에 둔다. 나눠 두면 한쪽만 고쳐서 두 응답이 갈라진다 —
`card` 컨텍스트의 `card_assembler.py` 와 같은 이유다.

**나간 팀을 거르는 것은 여기가 아니라 도메인 규칙의 몫이다**
(`domain/rules/membership_rules.py`). 여기서는 이미 걸러진 것을 받는다.
"""

from __future__ import annotations

from app.user.application.dtos.me_dto import MembershipResult, MeResult
from app.user.domain.entities.membership_entity import MembershipEntity
from app.user.domain.entities.user_entity import UserEntity


def build_me_result(
    user: UserEntity, memberships: list[MembershipEntity]
) -> MeResult:
    return MeResult(
        id=user.id,
        email=str(user.email),
        nickname=str(user.nickname),
        created_at=user.created_at,
        teams=[
            MembershipResult(
                team_id=m.team_id,
                name=m.name,
                region=m.region,
                sport_code=m.sport_code,
                role=m.role,
                joined_at=m.joined_at,
            )
            for m in memberships
        ],
    )
