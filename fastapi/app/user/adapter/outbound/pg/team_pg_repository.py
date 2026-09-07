"""`TeamPort` 의 PostgreSQL 구현.

`team`·`team_member`·`user`·`sport` 는 **전부 `user` 컨텍스트의 테이블**이라
ORM 을 그대로 쓴다.

🔴 **`player_card` 만 예외다.** 저쪽은 `card` 컨텍스트라 임포트하지 않고
`table()`/`column()` 으로 읽는다(2026-09-04 추가 — 미결 `paik` 2번).
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import column, select, table, update
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.user.adapter.outbound.orm.sport_orm import SportOrm
from app.user.adapter.outbound.orm.team_member_orm import TeamMemberOrm
from app.user.adapter.outbound.orm.team_orm import TeamOrm
from app.user.adapter.outbound.orm.user_orm import UserOrm
from app.user.application.ports.output.team_port import TeamPort
from app.user.domain.entities.team_entity import TeamEntity, TeamMemberEntity
from app.user.domain.value_objects.team_role_vo import TeamRole


# 소유하지 않는 테이블에서 **읽기만** 한다. 위 docstring 참조.
_card = table("player_card", column("id"), column("user_id"), column("public_slug"))


class TeamPgRepository(TeamPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def sport_exists(self, sport_code: str) -> bool:
        stmt = select(SportOrm.code).where(SportOrm.code == sport_code)
        return self._session.execute(stmt).first() is not None

    def user_exists(self, user_id: UUID) -> bool:
        stmt = select(UserOrm.id).where(UserOrm.id == user_id)
        return self._session.execute(stmt).first() is not None

    def find_team(self, team_id: UUID) -> TeamEntity | None:
        row = self._session.get(TeamOrm, team_id)
        if row is None:
            return None
        return TeamEntity(
            id=row.id, name=row.name, region=row.region, sport_code=row.sport_code
        )

    def active_members(self, team_id: UUID) -> list[TeamMemberEntity]:
        """`left_at IS NULL` 만. 오래 소속된 사람이 앞에 온다.

        🔴 **카드는 `outerjoin` 이다.** 안쪽 조인으로 걸면 카드를 안 만든 구성원이
        목록에서 통째로 사라진다 — 팀에는 여전히 있는 사람이다
        (미결 `paik` 2번의 「하지 말 것」).

        `player_card` 는 `card` 컨텍스트의 테이블이라 ORM 을 임포트하지 않고
        `table()`/`column()` 으로 읽는다(`user_pg_repository.has_card` 와 같은 방식).
        ⚠️ 대가: 저쪽 컬럼 이름이 바뀌면 파이썬이 안 잡아 준다 —
        `tests/user/adapter/test_team_db.py` 가 방어선이다.
        """
        stmt = (
            select(TeamMemberOrm, UserOrm.nickname, _card.c.id, _card.c.public_slug)
            .join(UserOrm, UserOrm.id == TeamMemberOrm.user_id)
            .outerjoin(_card, _card.c.user_id == TeamMemberOrm.user_id)
            .where(
                TeamMemberOrm.team_id == team_id,
                TeamMemberOrm.left_at.is_(None),
            )
            .order_by(TeamMemberOrm.joined_at.asc())
        )
        return [
            TeamMemberEntity(
                user_id=member.user_id,
                nickname=nickname,
                role=TeamRole(member.role),
                joined_at=member.joined_at,
                player_card_id=card_id,
                card_public_slug=slug,
            )
            for member, nickname, card_id, slug in self._session.execute(stmt).all()
        ]

    def create_team(self, team: TeamEntity, owner_id: UUID) -> None:
        """팀과 `owner` 소속을 **한 트랜잭션에서** 만든다.

        🔴 `flush` 를 빼면 안 된다. 두 모델 사이에 relationship 이 없어 SQLAlchemy 가
        INSERT 순서를 모르고, `team_member` 가 먼저 나가면 외래키 위반이 난다
        (`user_pg_repository.create` 에서 실제로 겪었다).
        """
        self._session.add(
            TeamOrm(
                id=team.id,
                name=team.name,
                region=team.region,
                sport_code=team.sport_code,
            )
        )
        self._session.flush()
        self._session.add(
            TeamMemberOrm(
                id=uuid4(),
                team_id=team.id,
                user_id=owner_id,
                role=str(TeamRole.OWNER),
                joined_at=datetime.now(timezone.utc),
                left_at=None,
            )
        )
        self._session.commit()

    def add_member(self, team_id: UUID, user_id: UUID) -> None:
        """`member` 로 넣는다.

        🔴 **팀 행을 먼저 잠근다.** 유일 제약이 `(team_id, user_id, joined_at)` 이라
        같은 사람이 **다른 시각으로 두 번** 들어오는 것은 DB 가 막지 못한다. 동시
        요청 두 건이 유스케이스의 중복 검사를 나란히 통과할 수 있어서, 팀 단위로
        직렬화하고 잠근 뒤에 다시 확인한다.

        부분 유일 색인(`WHERE left_at IS NULL`)으로 막는 방법도 있지만 부록 D 에 없는
        제약이라 늘리지 않았다.
        """
        self._session.execute(
            select(TeamOrm.id).where(TeamOrm.id == team_id).with_for_update()
        )
        already = self._session.execute(
            select(TeamMemberOrm.id).where(
                TeamMemberOrm.team_id == team_id,
                TeamMemberOrm.user_id == user_id,
                TeamMemberOrm.left_at.is_(None),
            )
        ).first()
        if already is not None:
            self._session.rollback()
            raise ApiError(409, "ALREADY_MEMBER", "이미 이 팀의 구성원입니다.")

        self._session.add(
            TeamMemberOrm(
                id=uuid4(),
                team_id=team_id,
                user_id=user_id,
                role=str(TeamRole.MEMBER),
                joined_at=datetime.now(timezone.utc),
                left_at=None,
            )
        )
        self._session.commit()

    def mark_left(self, team_id: UUID, user_id: UUID) -> None:
        """`left_at` 을 채운다. **행을 지우지 않는다** — 이력이 참조한다(부록 D.6)."""
        self._session.execute(
            update(TeamMemberOrm)
            .where(
                TeamMemberOrm.team_id == team_id,
                TeamMemberOrm.user_id == user_id,
                TeamMemberOrm.left_at.is_(None),
            )
            .values(left_at=datetime.now(timezone.utc))
        )
        self._session.commit()
