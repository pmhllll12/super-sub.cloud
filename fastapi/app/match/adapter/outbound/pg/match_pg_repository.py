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

from sqlalchemy import column, delete, func, insert, or_, select, table, update
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
from app.match.adapter.outbound.orm.team_match_request_orm import (
    TeamMatchRequestOrm,
)
from app.match.application.ports.output.match_port import MatchPort
from app.match.domain.entities.application_entity import ApplicationEntity
from app.match.domain.entities.match_entity import (
    MatchEntity,
    MatchListingEntity,
    PositionNeedEntity,
    TeamMatchRequestEntity,
)
from app.match.domain.rules.application_rules import SIDE_TEAM, SIDE_USER
from app.match.domain.rules.team_match_request_rules import CANCELLED, ACCEPTED, REJECTED

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
# `squad` 는 `card` 컨텍스트다 — 대기 화면이 상대 팀 판을 그리려면 공개
# 슬러그가 필요한데, 그것 때문에 컨텍스트를 임포트하지는 않는다(`paik` 31번의
# `_team` 과 같은 방식).
_squad = table("squad", column("team_id"), column("public_slug"))

# `notification` 은 `notification` 컨텍스트의 테이블이다. 임포트하지 않고
# 원시 SQL 로 쓴다(`user_pg_repository.py`의 `_notification`과 같은 방식·이유).
_notification = table(
    "notification",
    column("id"),
    column("recipient_user_id"),
    column("type"),
    column("actor_user_id"),
    column("subject_type"),
    column("subject_id"),
    column("read_at"),
    column("created_at"),
)

# `app.notification.domain.rules.notification_rules`의 값과 같다(컨텍스트끼리
# 임포트하지 않으므로 값을 복제 — `user_pg_repository.py`와 같은 판단).
_NOTIFY_TEAM_MATCH_REQUESTED = "team_match_requested"
_NOTIFY_TEAM_MATCH_ACCEPTED = "team_match_accepted"
_NOTIFY_TEAM_MATCH_REJECTED = "team_match_rejected"
_NOTIFY_TEAM_MATCH_REQUEST_CANCELLED = "team_match_request_cancelled"
_NOTIFY_TEAM_MATCH_CANCELLED = "team_match_cancelled"
_SUBJECT_TEAM_MATCH_REQUEST = "team_match_request"
_SUBJECT_MATCH = "match"

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
        # 팀 대 팀으로 이미 확정된 경기(`paik` 17번)는 모집이 없다 — 용병
        # 탐색 목록에 안 낸다(낸다 해도 지원할 자리가 없어 죽은 결과다).
        conditions = [MatchOrm.played_at > now, MatchOrm.opponent_team_id.is_(None)]
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
                opponent_team_id=match.opponent_team_id,
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

    def update_match(
        self,
        match_id: UUID,
        *,
        played_at: datetime | None,
        place: str | None,
        needs: list[PositionNeedEntity] | None,
    ) -> None:
        """`None` 인 항목은 건드리지 않는다. **한 트랜잭션에서** 끝낸다."""
        changes = {}
        if played_at is not None:
            changes["played_at"] = played_at
        if place is not None:
            changes["place"] = place
        if changes:
            self._session.execute(
                update(MatchOrm).where(MatchOrm.id == match_id).values(**changes)
            )

        if needs is not None:
            # 🔴 지우고 새로 넣는다. 같은 트랜잭션이라 중간 상태가 밖에서 안 보인다 —
            #    갈리면 필요 포지션이 사라진 경기가 남는다.
            self._session.execute(
                delete(MatchPositionNeedOrm).where(
                    MatchPositionNeedOrm.match_id == match_id
                )
            )
            for need in needs:
                self._session.add(
                    MatchPositionNeedOrm(
                        id=uuid4(),
                        match_id=match_id,
                        position_id=need.position_id,
                        head_count=need.head_count,
                    )
                )
        self._session.commit()

    def count_applications(self, match_id: UUID) -> int:
        return self._session.execute(
            select(func.count())
            .select_from(MatchApplicationOrm)
            .where(MatchApplicationOrm.match_id == match_id)
        ).scalar_one()

    def delete_match(self, match_id: UUID, actor_id: UUID) -> None:
        """필요 포지션을 먼저 지운다 — 외래키가 그 순서를 요구한다.

        팀 대 팀 확정 경기(`opponent_team_id` 있음)면 **취소한 쪽이 아닌
        상대 팀** 주장(들)에게 알린다(`paik` 17번). `team_match_request.
        match_id`는 FK가 `SET NULL`이라 따로 안 건드려도 된다.
        """
        match = self._session.get(MatchOrm, match_id)
        if match is not None and match.opponent_team_id is not None:
            # 취소한 사람이 속한 쪽이 아니라 **반대쪽** 팀에 알린다.
            actor_side = (
                match.team_id
                if self.team_role_of(match.team_id, actor_id) is not None
                else match.opponent_team_id
            )
            other_team = (
                match.opponent_team_id
                if actor_side == match.team_id
                else match.team_id
            )
            self._notify(
                recipient_user_ids=self.owner_user_ids(other_team),
                notif_type=_NOTIFY_TEAM_MATCH_CANCELLED,
                actor_user_id=actor_id,
                subject_id=match_id,
                now=datetime.now(timezone.utc),
                subject_type=_SUBJECT_MATCH,
            )
        self._session.execute(
            delete(MatchPositionNeedOrm).where(
                MatchPositionNeedOrm.match_id == match_id
            )
        )
        self._session.execute(delete(MatchOrm).where(MatchOrm.id == match_id))
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
            opponent_team_id=row.opponent_team_id,
        )

    def list_upcoming_matches(
        self, team_id: UUID, now: datetime
    ) -> list[MatchEntity]:
        """필요 포지션은 **한 번에** 읽는다.

        경기마다 따로 읽으면 목록 길이만큼 쿼리가 는다(N+1). 목록은 화면에서 자주
        열리는 자리라 여기서 미리 막아 둔다.

        🔴 **주최했거나(`team_id`) 상대로 확정됐거나(`opponent_team_id`) 둘
        다** 본다(`paik` 17번) — 안 그러면 수락한 상대 팀 화면엔 그 경기가
        안 뜬다.
        """
        stmt = (
            select(MatchOrm)
            .where(
                or_(
                    MatchOrm.team_id == team_id,
                    MatchOrm.opponent_team_id == team_id,
                ),
                MatchOrm.played_at > now,
            )
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
                opponent_team_id=row.opponent_team_id,
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

    def delete_application(self, application_id: UUID) -> None:
        self._session.execute(
            delete(MatchApplicationOrm).where(
                MatchApplicationOrm.id == application_id
            )
        )
        self._session.commit()

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

    # ------------------------------------------------------------------
    # 팀 대 팀 경기 신청 (`team_match_request`). `paik` 17번.
    # ------------------------------------------------------------------

    def owner_user_ids(self, team_id: UUID) -> list[UUID]:
        stmt = select(_team_member.c.user_id).where(
            _team_member.c.team_id == team_id,
            _team_member.c.role == "owner",
            _team_member.c.left_at.is_(None),
        )
        return [row[0] for row in self._session.execute(stmt).all()]

    def _notify(
        self,
        *,
        recipient_user_ids: list[UUID],
        notif_type: str,
        actor_user_id: UUID | None,
        subject_id: UUID,
        now: datetime,
        subject_type: str = _SUBJECT_TEAM_MATCH_REQUEST,
    ) -> None:
        if not recipient_user_ids:
            return
        self._session.execute(
            insert(_notification),
            [
                {
                    "id": uuid4(),
                    "recipient_user_id": uid,
                    "type": notif_type,
                    "actor_user_id": actor_user_id,
                    "subject_type": subject_type,
                    "subject_id": subject_id,
                    "read_at": None,
                    "created_at": now,
                }
                for uid in recipient_user_ids
            ],
        )

    def create_team_match_request(
        self, request: TeamMatchRequestEntity
    ) -> TeamMatchRequestEntity:
        row = TeamMatchRequestOrm(
                id=request.id,
                requester_team_id=request.requester_team_id,
                target_team_id=request.target_team_id,
                proposed_played_at=request.proposed_played_at,
                proposed_place=request.proposed_place,
                status=request.status,
                created_at=request.created_at,
        )
        self._session.add(row)
        self._notify(
            recipient_user_ids=self.owner_user_ids(request.target_team_id),
            notif_type=_NOTIFY_TEAM_MATCH_REQUESTED,
            actor_user_id=None,
            subject_id=request.id,
            now=request.created_at,
        )
        self._session.commit()
        return self._to_team_match_request(row)

    def find_team_match_request(
        self, request_id: UUID
    ) -> TeamMatchRequestEntity | None:
        row = self._session.get(TeamMatchRequestOrm, request_id)
        return None if row is None else self._to_team_match_request(row)

    def list_team_match_requests(
        self, team_id: UUID
    ) -> list[TeamMatchRequestEntity]:
        stmt = (
            select(TeamMatchRequestOrm)
            .where(
                or_(
                    TeamMatchRequestOrm.requester_team_id == team_id,
                    TeamMatchRequestOrm.target_team_id == team_id,
                )
            )
            .order_by(TeamMatchRequestOrm.created_at.desc())
        )
        return [
            self._to_team_match_request(row)
            for row in self._session.execute(stmt).scalars()
        ]

    def accept_team_match_request(
        self, request_id: UUID
    ) -> TeamMatchRequestEntity:
        """확정 경기 생성 + 신청 팀 알림 + **두 팀의 다른 `pending` 신청 정리**를
        전부 한 트랜잭션에서 한다 — 동시 확정(이중 예약) 방지가 목적이다.
        """
        row = self._session.get(TeamMatchRequestOrm, request_id)
        now = datetime.now(timezone.utc)

        match = MatchOrm(
            id=uuid4(),
            team_id=row.requester_team_id,
            opponent_team_id=row.target_team_id,
            played_at=row.proposed_played_at,
            place=row.proposed_place,
        )
        self._session.add(match)
        self._session.flush()

        row.status = ACCEPTED
        row.responded_at = now
        row.match_id = match.id

        self._notify(
            recipient_user_ids=self.owner_user_ids(row.requester_team_id),
            notif_type=_NOTIFY_TEAM_MATCH_ACCEPTED,
            actor_user_id=None,
            subject_id=row.id,
            now=now,
        )
        self._cancel_other_pending(row, now)

        self._session.commit()
        return self._to_team_match_request(row)

    def _cancel_other_pending(
        self, accepted: TeamMatchRequestOrm, now: datetime
    ) -> None:
        """`accepted`가 확정시킨 두 팀이 걸린 **다른** `pending` 신청을 전부
        `cancelled`로 정리하고, 그 신청의 양쪽(신청·대상) 주장에게 알린다.
        """
        involved = {accepted.requester_team_id, accepted.target_team_id}
        others = self._session.execute(
            select(TeamMatchRequestOrm).where(
                TeamMatchRequestOrm.id != accepted.id,
                TeamMatchRequestOrm.status == "pending",
                or_(
                    TeamMatchRequestOrm.requester_team_id.in_(involved),
                    TeamMatchRequestOrm.target_team_id.in_(involved),
                ),
            )
        ).scalars().all()
        for other in others:
            other.status = CANCELLED
            other.responded_at = now
            recipients = self.owner_user_ids(
                other.requester_team_id
            ) + self.owner_user_ids(other.target_team_id)
            self._notify(
                recipient_user_ids=recipients,
                notif_type=_NOTIFY_TEAM_MATCH_REQUEST_CANCELLED,
                actor_user_id=None,
                subject_id=other.id,
                now=now,
            )

    def reject_team_match_request(
        self, request_id: UUID
    ) -> TeamMatchRequestEntity:
        row = self._session.get(TeamMatchRequestOrm, request_id)
        now = datetime.now(timezone.utc)
        row.status = REJECTED
        row.responded_at = now
        self._notify(
            recipient_user_ids=self.owner_user_ids(row.requester_team_id),
            notif_type=_NOTIFY_TEAM_MATCH_REJECTED,
            actor_user_id=None,
            subject_id=row.id,
            now=now,
        )
        self._session.commit()
        return self._to_team_match_request(row)

    def cancel_team_match_request(
        self, request_id: UUID
    ) -> TeamMatchRequestEntity:
        """신청 팀이 스스로 무른다. 알림 없음(위 포트 docstring 참고)."""
        row = self._session.get(TeamMatchRequestOrm, request_id)
        row.status = CANCELLED
        row.responded_at = datetime.now(timezone.utc)
        self._session.commit()
        return self._to_team_match_request(row)

    def _team_briefs(self, *team_ids: UUID) -> dict[UUID, tuple[str, str]]:
        """`{team_id: (이름, 지역)}`. `team` 은 `user` 컨텍스트라 원시 SQL 이다."""
        stmt = select(_team.c.id, _team.c.name, _team.c.region).where(
            _team.c.id.in_(team_ids)
        )
        return {r[0]: (r[1], r[2]) for r in self._session.execute(stmt)}

    def _squad_slugs(self, *team_ids: UUID) -> dict[UUID, str]:
        """`{team_id: 공개 슬러그}` — 대기 화면이 상대 팀 판을 그리는 데 쓴다.

        🔴 **스쿼드를 아직 안 만든 팀은 이 표에 없다**(생성이 멱등이라 늦게
        생긴다). 없는 것이 정상이라 빈 값으로 채우지 않고 `None` 으로 둔다 —
        `paik` 37번(초대)이 같은 판단을 했다.
        """
        stmt = select(_squad.c.team_id, _squad.c.public_slug).where(
            _squad.c.team_id.in_(team_ids)
        )
        return {r[0]: r[1] for r in self._session.execute(stmt)}

    def _to_team_match_request(
        self, row: TeamMatchRequestOrm
    ) -> TeamMatchRequestEntity:
        # 표시용 값을 여기서 채운다(`paik` 31번) — 화면이 줄마다 팀을 다시
        # 묻지 않게. 한 줄에 한 번만 읽고 두 팀을 같이 가져온다.
        briefs = self._team_briefs(row.requester_team_id, row.target_team_id)
        requester = briefs.get(row.requester_team_id, ("", ""))
        target = briefs.get(row.target_team_id, ("", ""))
        # 판을 찾아갈 슬러그도 같이 싣는다 — 대기 화면이 상대 판을 그린다.
        slugs = self._squad_slugs(row.requester_team_id, row.target_team_id)
        return TeamMatchRequestEntity(
            id=row.id,
            requester_team_id=row.requester_team_id,
            target_team_id=row.target_team_id,
            proposed_played_at=row.proposed_played_at,
            proposed_place=row.proposed_place,
            status=row.status,
            created_at=row.created_at,
            responded_at=row.responded_at,
            match_id=row.match_id,
            requester_team_name=requester[0],
            requester_team_region=requester[1],
            target_team_name=target[0],
            target_team_region=target[1],
            requester_squad_public_slug=slugs.get(row.requester_team_id),
            target_squad_public_slug=slugs.get(row.target_team_id),
        )
