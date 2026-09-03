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

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import column, func, select, table, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.match.adapter.outbound.orm.match_application_orm import (
    MatchApplicationOrm,
)
from app.match.adapter.outbound.orm.match_orm import MatchOrm
from app.match.adapter.outbound.orm.match_position_need_orm import (
    MatchPositionNeedOrm,
)
from app.match.application.ports.output.match_port import MatchPort
from app.match.domain.entities.application_entity import ApplicationEntity
from app.match.domain.entities.match_entity import (
    MatchEntity,
    MatchListingEntity,
    PositionNeedEntity,
)
from app.match.domain.rules.application_rules import SIDE_TEAM, SIDE_USER

# 소유하지 않는 테이블에서 **읽기만** 한다. 위 docstring 참조.
_team = table(
    "team", column("id"), column("sport_code"), column("name"), column("region")
)
_sport = table("sport", column("code"))
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
_user = table("user", column("id"), column("nickname"))

# PostgreSQL 의 unique_violation. 컨텍스트끼리 임포트하지 않으므로 상수를 여기에도 둔다.
_UNIQUE_VIOLATION = "23505"


def _is_unique_violation(exc: IntegrityError) -> bool:
    return getattr(getattr(exc, "orig", None), "sqlstate", None) == _UNIQUE_VIOLATION


# LIKE 패턴에서 특별한 뜻을 갖는 문자. 검색어에 들어오면 리터럴로 바꿔야 한다.
# `user` 쪽 저장소에 같은 함수가 있지만 **가져오지 않는다** — 컨텍스트끼리
# 임포트하지 않기 때문이다(`tests/test_architecture.py`).
_LIKE_ESCAPE = "\\"


def _escape_like(value: str) -> str:
    """LIKE 메타문자를 리터럴로 만든다.

    🔴 역슬래시를 **먼저** 바꾼다. 나중에 바꾸면 `%` 를 감싸려고 붙인 이스케이프
    문자까지 다시 이스케이프되어 패턴이 깨진다.
    """
    return (
        value.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2)
        .replace("%", f"{_LIKE_ESCAPE}%")
        .replace("_", f"{_LIKE_ESCAPE}_")
    )


class MatchPgRepository(MatchPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def team_exists(self, team_id: UUID) -> bool:
        stmt = select(_team.c.id).where(_team.c.id == team_id)
        return self._session.execute(stmt).first() is not None

    def sport_exists(self, sport_code: str) -> bool:
        stmt = select(_sport.c.code).where(_sport.c.code == sport_code)
        return self._session.execute(stmt).first() is not None

    def search_upcoming(
        self,
        *,
        sport_code: str | None,
        region: str | None,
        now: datetime,
        offset: int,
        limit: int,
    ) -> tuple[list[MatchListingEntity], int]:
        conditions = [MatchOrm.played_at > now]
        if sport_code:
            conditions.append(_team.c.sport_code == sport_code)
        if region:
            # 🔴 `%`·`_` 는 LIKE 메타문자다. 그대로 넘기면 검색어가 패턴이 되어
            #    `region="%"` 한 글자로 전체가 걸린다 — 리터럴로 이스케이프한다.
            #    (`user_pg_repository` 의 `q` 와 같은 판단이다.)
            conditions.append(
                _team.c.region.ilike(
                    f"%{_escape_like(region)}%", escape=_LIKE_ESCAPE
                )
            )

        joined = MatchOrm.__table__.join(_team, _team.c.id == MatchOrm.team_id)

        total = self._session.execute(
            select(func.count()).select_from(joined).where(*conditions)
        ).scalar_one()
        if total == 0:
            return [], 0

        rows = (
            self._session.execute(
                select(
                    MatchOrm.id,
                    MatchOrm.team_id,
                    MatchOrm.played_at,
                    MatchOrm.place,
                    _team.c.name,
                    _team.c.region,
                    _team.c.sport_code,
                )
                .select_from(joined)
                .where(*conditions)
                # 이른 것이 앞에 온다 — 임박한 모집이 급하다.
                .order_by(MatchOrm.played_at)
                .offset(offset)
                .limit(limit)
            )
            .tuples()
            .all()
        )
        if not rows:
            # 마지막 페이지를 넘겨 요청한 경우다. `total` 은 그대로 돌려준다.
            return [], total

        needs = self._needs_of([r[0] for r in rows])
        return [
            MatchListingEntity(
                match=MatchEntity(
                    id=r[0],
                    team_id=r[1],
                    played_at=r[2],
                    place=r[3],
                    needs=needs.get(r[0], []),
                ),
                team_name=r[4],
                region=r[5],
                sport_code=r[6],
            )
            for r in rows
        ], total

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

    def list_upcoming_matches(
        self, team_id: UUID, now: datetime
    ) -> list[MatchEntity]:
        """필요 포지션은 **한 번에** 읽는다.

        경기마다 따로 읽으면 목록 길이만큼 쿼리가 는다(N+1). 목록은 화면에서 자주
        열리는 자리라 여기서 미리 막아 둔다.
        """
        stmt = (
            select(MatchOrm)
            .where(MatchOrm.team_id == team_id, MatchOrm.played_at > now)
            .order_by(MatchOrm.played_at.asc())
        )
        rows = list(self._session.execute(stmt).scalars())
        needs = self._needs_of([row.id for row in rows])
        return [
            MatchEntity(
                id=row.id,
                team_id=row.team_id,
                played_at=row.played_at,
                place=row.place,
                needs=needs.get(row.id, []),
            )
            for row in rows
        ]

    def _needs_of(self, match_ids: list[UUID]) -> dict[UUID, list[PositionNeedEntity]]:
        if not match_ids:
            return {}
        stmt = (
            select(
                MatchPositionNeedOrm.match_id,
                MatchPositionNeedOrm.position_id,
                MatchPositionNeedOrm.head_count,
                _position.c.code,
                _position.c.label,
            )
            .join(_position, _position.c.id == MatchPositionNeedOrm.position_id)
            .where(MatchPositionNeedOrm.match_id.in_(match_ids))
            .order_by(_position.c.code.asc())
        )
        found: dict[UUID, list[PositionNeedEntity]] = {}
        for row in self._session.execute(stmt):
            found.setdefault(row.match_id, []).append(
                PositionNeedEntity(
                    position_id=row.position_id,
                    code=row.code,
                    label=row.label,
                    head_count=row.head_count,
                )
            )
        return found

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

    # ------------------------------------------------------------------
    # 지원·제안 (`match_application`)
    # ------------------------------------------------------------------

    def user_exists(self, user_id: UUID) -> bool:
        stmt = select(_user.c.id).where(_user.c.id == user_id)
        return self._session.execute(stmt).first() is not None

    def find_application(
        self, match_id: UUID, user_id: UUID
    ) -> ApplicationEntity | None:
        return self._load_application(
            (MatchApplicationOrm.match_id == match_id)
            & (MatchApplicationOrm.user_id == user_id)
        )

    def find_application_by_id(
        self, application_id: UUID
    ) -> ApplicationEntity | None:
        return self._load_application(MatchApplicationOrm.id == application_id)

    def list_applications(self, match_id: UUID) -> list[ApplicationEntity]:
        """먼저 시작된 건이 앞에 온다.

        `created_at` 이 없으므로(부록 D 의 ERD 에 없다) **먼저 찬 시각**으로 센다 —
        지원이면 `user_accepted_at`, 제안이면 `team_accepted_at` 이 그 값이다.
        """
        started = func.least(
            func.coalesce(
                MatchApplicationOrm.user_accepted_at,
                MatchApplicationOrm.team_accepted_at,
            ),
            func.coalesce(
                MatchApplicationOrm.team_accepted_at,
                MatchApplicationOrm.user_accepted_at,
            ),
        )
        stmt = (
            select(MatchApplicationOrm, _user.c.nickname)
            .join(_user, _user.c.id == MatchApplicationOrm.user_id)
            .where(MatchApplicationOrm.match_id == match_id)
            .order_by(started.asc())
        )
        return [
            self._to_application(row, nickname)
            for row, nickname in self._session.execute(stmt).all()
        ]

    def create_application(
        self, match_id: UUID, user_id: UUID, side: str
    ) -> ApplicationEntity:
        """시작한 쪽 시각만 채운다. 나머지는 상대가 수락할 때 찬다."""
        now = datetime.now(timezone.utc)
        row = MatchApplicationOrm(
            id=uuid4(),
            match_id=match_id,
            user_id=user_id,
            user_accepted_at=now if side == SIDE_USER else None,
            team_accepted_at=now if side == SIDE_TEAM else None,
        )
        self._session.add(row)
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            # 유스케이스가 먼저 걸러도 동시 요청 두 건은 통과한다.
            # `uq_match_application` 이 마지막 방어선이다.
            if _is_unique_violation(exc):
                raise ApiError(
                    409, "ALREADY_APPLIED", "이미 지원·제안된 건이 있습니다."
                ) from exc
            raise

        loaded = self.find_application_by_id(row.id)
        if loaded is None:
            raise RuntimeError("지원 건을 만들었는데 다시 읽히지 않는다")
        return loaded

    def accept_application(self, application_id: UUID, side: str) -> ApplicationEntity:
        column_name = (
            MatchApplicationOrm.user_accepted_at
            if side == SIDE_USER
            else MatchApplicationOrm.team_accepted_at
        )
        self._session.execute(
            update(MatchApplicationOrm)
            .where(
                MatchApplicationOrm.id == application_id,
                # 🔴 비어 있을 때만 채운다. 이미 찬 값을 덮으면 수락 시각이 뒤로
                # 밀려 "언제 확정됐나"가 틀어진다.
                column_name.is_(None),
            )
            .values({column_name: datetime.now(timezone.utc)})
        )
        self._session.commit()

        loaded = self.find_application_by_id(application_id)
        if loaded is None:
            raise RuntimeError("수락한 지원 건이 사라졌다")
        return loaded

    def _load_application(self, where) -> ApplicationEntity | None:
        stmt = (
            select(MatchApplicationOrm, _user.c.nickname)
            .join(_user, _user.c.id == MatchApplicationOrm.user_id)
            .where(where)
        )
        row = self._session.execute(stmt).first()
        if row is None:
            return None
        return self._to_application(row[0], row[1])

    def _to_application(self, row, nickname: str) -> ApplicationEntity:
        return ApplicationEntity(
            id=row.id,
            match_id=row.match_id,
            user_id=row.user_id,
            nickname=nickname,
            team_accepted_at=row.team_accepted_at,
            user_accepted_at=row.user_accepted_at,
        )
