"""`MatchPort` 의 PostgreSQL 구현.

🔴 **`user` 컨텍스트를 임포트하지 않는다.**

경기는 팀(주최)·소속(권한)·포지션(필요 인원)을 알아야 하는데 셋 다 `user` 컨텍스트의
테이블이다. 모듈을 가져오면 경계가 무너지므로(`tests/test_architecture.py`)
**필요한 컬럼만** `table()`/`column()` 으로 읽는다 — 카드가 `user.nickname` 을 읽는
것과 같은 방식이다.

⚠️ 대가: 저쪽 컬럼 이름이 바뀌면 **파이썬이 잡아 주지 않는다.**
`tests/match/adapter/test_match_db.py` 가 유일한 방어선이다 — 지우지 말 것.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import column, select, table
from sqlalchemy.orm import Session

from app.match.adapter.outbound.orm.match_orm import MatchOrm
from app.match.adapter.outbound.orm.match_position_need_orm import (
    MatchPositionNeedOrm,
)
from app.match.application.ports.output.match_port import MatchPort
from app.match.domain.entities.match_entity import MatchEntity, PositionNeedEntity

# 소유하지 않는 테이블에서 **읽기만** 한다. 위 docstring 참조.
_team = table("team", column("id"), column("sport_code"))
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


class MatchPgRepository(MatchPort):
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

    def find_positions(
        self, team_id: UUID, codes: list[str]
    ) -> dict[str, PositionNeedEntity]:
        """팀 종목으로 좁혀서 찾는다. 코드만으로 찾으면 남의 종목이 걸린다."""
        if not codes:
            return {}
        stmt = (
            select(_position.c.id, _position.c.code, _position.c.label)
            .join(_team, _team.c.sport_code == _position.c.sport_code)
            .where(_team.c.id == team_id, _position.c.code.in_(codes))
        )
        return {
            row.code: PositionNeedEntity(
                position_id=row.id, code=row.code, label=row.label, head_count=0
            )
            for row in self._session.execute(stmt)
        }

    def create_match(self, match: MatchEntity) -> None:
        """🔴 `flush` 를 빼면 안 된다.

        두 모델 사이에 relationship 이 없어 SQLAlchemy 가 INSERT 순서를 모르고,
        `match_position_need` 가 먼저 나가면 외래키 위반이 난다.
        """
        self._session.add(
            MatchOrm(
                id=match.id,
                team_id=match.team_id,
                played_at=match.played_at,
                place=match.place,
            )
        )
        self._session.flush()
        for need in match.needs:
            self._session.add(
                MatchPositionNeedOrm(
                    id=uuid4(),
                    match_id=match.id,
                    position_id=need.position_id,
                    head_count=need.head_count,
                )
            )
        self._session.commit()

    def find_match(self, match_id: UUID) -> MatchEntity | None:
        row = self._session.get(MatchOrm, match_id)
        if row is None:
            return None
        return MatchEntity(
            id=row.id,
            team_id=row.team_id,
            played_at=row.played_at,
            place=row.place,
            needs=self._needs(match_id),
        )

    def _needs(self, match_id: UUID) -> list[PositionNeedEntity]:
        stmt = (
            select(
                MatchPositionNeedOrm.position_id,
                MatchPositionNeedOrm.head_count,
                _position.c.code,
                _position.c.label,
            )
            .join(_position, _position.c.id == MatchPositionNeedOrm.position_id)
            .where(MatchPositionNeedOrm.match_id == match_id)
            .order_by(_position.c.code.asc())
        )
        return [
            PositionNeedEntity(
                position_id=row.position_id,
                code=row.code,
                label=row.label,
                head_count=row.head_count,
            )
            for row in self._session.execute(stmt)
        ]
