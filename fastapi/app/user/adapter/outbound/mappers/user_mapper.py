"""ORM 행 ↔ 도메인 엔티티.

**변환을 리포지토리 안에 섞지 않는다.** 섞으면 쿼리와 매핑이 같이 자라서 어느 쪽이
틀렸는지 판별이 어려워진다. 여기 있는 것은 순수 함수라 DB 없이 테스트할 수 있다.

반대 방향(엔티티 → ORM)은 가입 한 곳에서만 필요해서 리포지토리가 직접 만든다.
쓰는 곳이 둘 이상이 되면 그때 여기로 올린다.
"""

from __future__ import annotations

from app.user.adapter.outbound.orm.team_member_orm import TeamMemberOrm
from app.user.adapter.outbound.orm.team_orm import TeamOrm
from app.user.adapter.outbound.orm.user_orm import UserOrm
from app.user.domain.entities.membership_entity import MembershipEntity
from app.user.domain.entities.user_entity import UserEntity
from app.user.domain.value_objects.email_vo import Email
from app.user.domain.value_objects.nickname_vo import Nickname


def to_user_entity(row: UserOrm) -> UserEntity:
    # Email.of 를 거치는 이유: DB 에 과거 데이터가 대문자로 들어 있어도
    # 도메인 안에서는 항상 정규화된 값만 돌게 한다.
    return UserEntity(
        id=row.id,
        email=Email.of(row.email),
        nickname=Nickname.of(row.nickname),
        created_at=row.created_at,
    )


def to_membership_entity(member: TeamMemberOrm, team: TeamOrm) -> MembershipEntity:
    """`team_member` 와 `team` 을 합쳐 하나의 소속 구간으로 만든다.

    `left_at` 을 그대로 넘긴다 — 나간 소속을 거르는 것은 도메인 규칙의 몫이고,
    여기서 걸러 버리면 그 규칙을 테스트할 수 없게 된다.
    """
    return MembershipEntity(
        team_id=team.id,
        name=team.name,
        region=team.region,
        sport_code=team.sport_code,
        role=member.role,
        joined_at=member.joined_at,
        left_at=member.left_at,
    )
