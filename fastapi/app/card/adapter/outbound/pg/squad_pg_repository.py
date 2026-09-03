"""`SquadPort` 의 PostgreSQL 구현.

🔴 **`user` 컨텍스트를 임포트하지 않는다.**

스쿼드는 팀(주최)·소속(권한)·포지션(등재)·닉네임(표시)을 알아야 하는데 넷 다
`user` 컨텍스트의 테이블이다. 모듈을 가져오면 경계가 무너지므로
(`tests/test_architecture.py`) **필요한 컬럼만** `table()`/`column()` 으로 읽는다 —
같은 컨텍스트의 `card_pg_repository` 가 `user.nickname` 을 읽는 방식과 같다.

⚠️ 대가: 저쪽 컬럼 이름이 바뀌면 **파이썬이 잡아 주지 않는다.**
`tests/card/adapter/test_squad_db.py` 가 유일한 방어선이다 — 지우지 말 것.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import column, delete, select, table
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.card.adapter.outbound.orm.player_card_orm import PlayerCardOrm
from app.card.adapter.outbound.orm.squad_member_orm import SquadMemberOrm
from app.card.adapter.outbound.orm.squad_orm import SquadOrm
from app.card.application.ports.output.squad_port import SquadPort
from app.card.domain.entities.squad_entity import SquadEntity, SquadMemberEntity
from app.card.domain.value_objects.public_slug_vo import PublicSlug

# 소유하지 않는 테이블에서 **읽기만** 한다. 위 docstring 참조.
_team = table("team", column("id"))
_team_member = table(
    "team_member",
    column("team_id"),
    column("user_id"),
    column("role"),
    column("left_at"),
)
_position = table(
    "position", column("id"), column("sport_code"), column("code"), column("label")
)
_team_sport = table("team", column("id"), column("sport_code"))
_user = table("user", column("id"), column("nickname"))

# PostgreSQL 의 unique_violation. 같은 상수가 `card_pg_repository` 에도 있지만
# **가져오지 않는다** — 표준 SQLSTATE 라 값이 같고, 굳이 잇는 것보다 낫다.
_UNIQUE_VIOLATION = "23505"

# 슬러그가 겹쳤을 때 다시 뽑는 횟수. 카드와 같은 이유다 — 96비트 난수라 한 번도
# 걸리지 않는 것이 정상이고, 이 상수는 "겹치면 영영 못 만든다"를 막는다.
_CREATE_ATTEMPTS = 3


def _is_unique_violation(exc: IntegrityError) -> bool:
    return getattr(getattr(exc, "orig", None), "sqlstate", None) == _UNIQUE_VIOLATION


class SquadPgRepository(SquadPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def team_exists(self, team_id: UUID) -> bool:
        stmt = select(_team.c.id).where(_team.c.id == team_id)
        return self._session.execute(stmt).first() is not None

    def team_role_of(self, team_id: UUID, user_id: UUID) -> str | None:
        """**나간 소속은 세지 않는다.** 재가입 이력이 여러 행으로 남기 때문이다."""
        stmt = select(_team_member.c.role).where(
            _team_member.c.team_id == team_id,
            _team_member.c.user_id == user_id,
            _team_member.c.left_at.is_(None),
        )
        row = self._session.execute(stmt).first()
        return None if row is None else row[0]

    def find_by_team(self, team_id: UUID) -> SquadEntity | None:
        squad = self._session.execute(
            select(SquadOrm).where(SquadOrm.team_id == team_id)
        ).scalar_one_or_none()
        return None if squad is None else self._with_members(squad)

    def find_by_slug(self, public_slug: str) -> SquadEntity | None:
        squad = self._session.execute(
            select(SquadOrm).where(SquadOrm.public_slug == public_slug)
        ).scalar_one_or_none()
        return None if squad is None else self._with_members(squad)

    def create_for_team(self, team_id: UUID) -> tuple[SquadEntity, bool]:
        existing = self.find_by_team(team_id)
        if existing is not None:
            return existing, False

        # 슬러그가 겹치면 다시 뽑는다. 규칙은 도메인에 있고(`PublicSlug.generate`)
        # 재시도는 유일 제약을 아는 여기서만 할 수 있다 — 카드와 같은 구조다.
        for _ in range(_CREATE_ATTEMPTS):
            squad = SquadOrm(
                id=uuid4(),
                team_id=team_id,
                public_slug=str(PublicSlug.generate()),
            )
            self._session.add(squad)
            try:
                self._session.commit()
            except IntegrityError as exc:
                self._session.rollback()
                if not _is_unique_violation(exc):
                    raise
                continue
            return self._with_members(squad), True

        raise RuntimeError("슬러그를 여러 번 뽑았는데 전부 겹쳤다")

    def find_position(self, team_id: UUID, code: str) -> tuple[UUID, str] | None:
        """팀 종목으로 좁혀서 찾는다. 코드만으로 찾으면 남의 종목이 걸린다."""
        stmt = (
            select(_position.c.id, _position.c.label)
            .select_from(
                _position.join(
                    _team_sport,
                    _position.c.sport_code == _team_sport.c.sport_code,
                )
            )
            .where(_team_sport.c.id == team_id, _position.c.code == code)
        )
        row = self._session.execute(stmt).first()
        return None if row is None else (row[0], row[1])

    def card_owner(self, player_card_id: UUID) -> UUID | None:
        stmt = select(PlayerCardOrm.user_id).where(PlayerCardOrm.id == player_card_id)
        return self._session.execute(stmt).scalar_one_or_none()

    def enlist(
        self, squad_id: UUID, player_card_id: UUID, position_id: UUID
    ) -> SquadMemberEntity:
        member = SquadMemberOrm(
            id=uuid4(),
            squad_id=squad_id,
            player_card_id=player_card_id,
            position_id=position_id,
        )
        self._session.add(member)
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            if _is_unique_violation(exc):
                # 인터랙터가 409 로 바꾼다. 여기서 ApiError 를 내면 어댑터가
                # HTTP 를 알게 된다.
                raise ValueError("이미 등재된 카드다") from exc
            raise
        return self._member_entity(member.id, player_card_id, position_id)

    def find_member(self, member_id: UUID) -> tuple[UUID, UUID] | None:
        stmt = select(SquadMemberOrm.squad_id, SquadMemberOrm.player_card_id).where(
            SquadMemberOrm.id == member_id
        )
        row = self._session.execute(stmt).first()
        return None if row is None else (row[0], row[1])

    def discharge(self, member_id: UUID) -> None:
        self._session.execute(
            delete(SquadMemberOrm).where(SquadMemberOrm.id == member_id)
        )
        self._session.commit()

    # -- 조립 -----------------------------------------------------------------

    def _with_members(self, squad: SquadOrm) -> SquadEntity:
        """등재를 표시용 값까지 채워서 붙인다.

        닉네임과 카드 슬러그는 **저장되지 않는 값**이라 매번 조인해서 읽는다.
        `player_card -> user` 로 한 단계 더 가는 이유는 스쿼드가 사람이 아니라
        **카드**를 담기 때문이다.
        """
        rows = (
            self._session.execute(
                select(
                    SquadMemberOrm.id,
                    SquadMemberOrm.player_card_id,
                    PlayerCardOrm.public_slug,
                    _user.c.nickname,
                    _position.c.id,
                    _position.c.code,
                    _position.c.label,
                )
                .select_from(SquadMemberOrm)
                .join(PlayerCardOrm, PlayerCardOrm.id == SquadMemberOrm.player_card_id)
                .join(_user, _user.c.id == PlayerCardOrm.user_id)
                .join(_position, _position.c.id == SquadMemberOrm.position_id)
                .where(SquadMemberOrm.squad_id == squad.id)
                .order_by(_position.c.code, _user.c.nickname)
            )
            .tuples()
            .all()
        )
        return SquadEntity(
            id=squad.id,
            team_id=squad.team_id,
            public_slug=PublicSlug(squad.public_slug),
            members=[
                SquadMemberEntity(
                    id=r[0],
                    player_card_id=r[1],
                    card_public_slug=r[2],
                    nickname=r[3],
                    position_id=r[4],
                    position_code=r[5],
                    position_label=r[6],
                )
                for r in rows
            ],
        )

    def _member_entity(
        self, member_id: UUID, player_card_id: UUID, position_id: UUID
    ) -> SquadMemberEntity:
        row = self._session.execute(
            select(
                PlayerCardOrm.public_slug,
                _user.c.nickname,
                _position.c.code,
                _position.c.label,
            )
            .select_from(PlayerCardOrm)
            .join(_user, _user.c.id == PlayerCardOrm.user_id)
            .join(_position, _position.c.id == position_id)
            .where(PlayerCardOrm.id == player_card_id)
        ).one()
        return SquadMemberEntity(
            id=member_id,
            player_card_id=player_card_id,
            card_public_slug=row[0],
            nickname=row[1],
            position_id=position_id,
            position_code=row[2],
            position_label=row[3],
        )
