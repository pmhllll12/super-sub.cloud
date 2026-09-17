"""`TeamPort` 의 PostgreSQL 구현.

`team`·`team_member`·`user`·`sport` 는 **전부 `user` 컨텍스트의 테이블**이라
ORM 을 그대로 쓴다.

🔴 **`player_card` 만 예외다.** 저쪽은 `card` 컨텍스트라 임포트하지 않고
`table()`/`column()` 으로 읽는다(2026-09-04 추가 — 미결 `paik` 2번).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import column, insert, select, table, update
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.user.adapter.outbound.orm.position_orm import PositionOrm
from app.user.adapter.outbound.orm.sport_orm import SportOrm
from app.user.adapter.outbound.orm.team_invitation_orm import TeamInvitationOrm
from app.user.adapter.outbound.orm.team_member_orm import TeamMemberOrm
from app.user.adapter.outbound.orm.team_orm import TeamOrm
from app.user.adapter.outbound.orm.user_orm import UserOrm
from app.user.application.ports.output.team_port import TeamPort
from app.user.domain.entities.team_entity import (
    MyTeamInvitationEntity,
    TeamEntity,
    TeamInvitationEntity,
    TeamMemberEntity,
)
from app.user.domain.rules.team_invitation_rules import ACCEPTED, PENDING, REJECTED, CANCELLED
from app.user.domain.value_objects.team_role_vo import TeamRole


# 소유하지 않는 테이블에서 **읽기만** 한다. 위 docstring 참조.
_card = table("player_card", column("id"), column("user_id"), column("public_slug"))

# `squad` 도 `card` 컨텍스트다 — 위와 같은 이유로 임포트하지 않는다(`paik` 37번).
_squad = table("squad", column("team_id"), column("public_slug"))

# `match` 컨텍스트의 둘. 해체가 이력을 건드리지 않는지 보려면 앞으로 있을
# 경기를 세야 하고, 대기 중인 경기 신청은 닫아야 한다(`paik` 35번).
_match = table(
    "match", column("id"), column("team_id"), column("opponent_team_id"),
    column("played_at"),
)
_team_match_request = table(
    "team_match_request", column("id"), column("requester_team_id"),
    column("target_team_id"), column("status"), column("responded_at"),
)
# `app.match.domain.rules.team_match_request_rules` 의 값과 같다 — 컨텍스트끼리
# 임포트하지 않으므로 값만 복제한다(위 알림 타입들과 같은 판단).
_MATCH_REQUEST_PENDING = "pending"
_MATCH_REQUEST_CANCELLED = "cancelled"

# `notification` 은 `notification` 컨텍스트의 테이블이다. 임포트하지 않고
# 원시 SQL 로 쓴다 — `user_pg_repository.py`의 `_notification`과 같은 방식·이유.
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
# 임포트하지 않으므로 값만 복제 — `match_pg_repository.py`와 같은 판단).
_NOTIFY_TEAM_INVITATION_SENT = "team_invitation_sent"
_NOTIFY_TEAM_INVITATION_ACCEPTED = "team_invitation_accepted"
_NOTIFY_TEAM_INVITATION_REJECTED = "team_invitation_rejected"
_SUBJECT_TEAM_INVITATION = "team_invitation"


class TeamPgRepository(TeamPort):
    def __init__(self, session: Session) -> None:
        self._session = session

    def sport_exists(self, sport_code: str) -> bool:
        stmt = select(SportOrm.code).where(SportOrm.code == sport_code)
        return self._session.execute(stmt).first() is not None

    def sport_is_active(self, sport_code: str) -> bool:
        stmt = select(SportOrm.code).where(
            SportOrm.code == sport_code, SportOrm.active.is_(True)
        )
        return self._session.execute(stmt).first() is not None

    def user_exists(self, user_id: UUID) -> bool:
        stmt = select(UserOrm.id).where(UserOrm.id == user_id)
        return self._session.execute(stmt).first() is not None

    def find_team(self, team_id: UUID) -> TeamEntity | None:
        row = self._session.get(TeamOrm, team_id)
        if row is None:
            return None
        return TeamEntity(
            id=row.id,
            name=row.name,
            region=row.region,
            sport_code=row.sport_code,
            disbanded_at=row.disbanded_at,
        )

    def update_team(
        self, team_id: UUID, name: str | None, region: str | None
    ) -> TeamEntity | None:
        """🔴 `values()` 에 이름·지역만 둔다 — `sport_code` 를 여기서 바꿀 수
        있게 열어 두면 언젠가 누가 쓴다. 포지션·스쿼드·경기가 전부 그 값에
        매달려 있어서, 바뀌면 이미 앉힌 포지션이 다른 종목 것이 된다.
        """
        values = {}
        if name is not None:
            values["name"] = name
        if region is not None:
            values["region"] = region
        if not values:
            # 바꿀 것이 없으면 갱신을 안 돈다 — 없는 팀 판정은 조회가 한다.
            return self.find_team(team_id)

        changed = self._session.execute(
            update(TeamOrm).where(TeamOrm.id == team_id).values(**values)
        ).rowcount
        if not changed:
            self._session.rollback()
            return None
        self._session.commit()
        return self.find_team(team_id)

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

    def set_member_role(self, team_id: UUID, user_id: UUID, role: str) -> None:
        self._session.execute(
            update(TeamMemberOrm)
            .where(
                TeamMemberOrm.team_id == team_id,
                TeamMemberOrm.user_id == user_id,
                TeamMemberOrm.left_at.is_(None),
            )
            .values(role=role)
        )
        self._session.commit()

    # --- 팀 해체 (`paik` 35번) -----------------------------------------------

    def has_upcoming_match(self, team_id: UUID) -> bool:
        now = datetime.now(timezone.utc)
        stmt = select(_match.c.id).where(
            _match.c.played_at > now,
            (_match.c.team_id == team_id)
            | (_match.c.opponent_team_id == team_id),
        )
        return self._session.execute(stmt).first() is not None

    def disband_team(self, team_id: UUID) -> None:
        now = datetime.now(timezone.utc)
        self._session.execute(
            update(TeamOrm)
            .where(TeamOrm.id == team_id, TeamOrm.disbanded_at.is_(None))
            .values(disbanded_at=now)
        )
        # 남은 구성원을 전부 내보낸다 — `GET /me` 의 `teams` 가 `left_at` 으로
        # 거르므로, 이걸 빼면 해체한 팀이 모두의 목록에 그대로 남는다.
        self._session.execute(
            update(TeamMemberOrm)
            .where(
                TeamMemberOrm.team_id == team_id,
                TeamMemberOrm.left_at.is_(None),
            )
            .values(left_at=now)
        )
        # 대기 중이던 초대를 닫는다 — 안 닫으면 해체된 팀의 초대가 남의
        # 초대함에 남고, 수락하면 죽은 팀에 들어가게 된다.
        self._session.execute(
            update(TeamInvitationOrm)
            .where(
                TeamInvitationOrm.team_id == team_id,
                TeamInvitationOrm.status == PENDING,
            )
            .values(status=CANCELLED, responded_at=now)
        )
        # 경기 신청도 같다(보낸 것·받은 것 둘 다). `match` 컨텍스트라 원시 SQL.
        self._session.execute(
            _team_match_request.update()
            .where(
                _team_match_request.c.status == _MATCH_REQUEST_PENDING,
                (_team_match_request.c.requester_team_id == team_id)
                | (_team_match_request.c.target_team_id == team_id),
            )
            .values(status=_MATCH_REQUEST_CANCELLED, responded_at=now)
        )
        self._session.commit()

    # --- 팀 초대 (`min` 20번) ------------------------------------------------

    def _owner_user_ids(self, team_id: UUID) -> list[UUID]:
        stmt = select(TeamMemberOrm.user_id).where(
            TeamMemberOrm.team_id == team_id,
            TeamMemberOrm.role == str(TeamRole.OWNER),
            TeamMemberOrm.left_at.is_(None),
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
                    "subject_type": _SUBJECT_TEAM_INVITATION,
                    "subject_id": subject_id,
                    "read_at": None,
                    "created_at": now,
                }
                for uid in recipient_user_ids
            ],
        )

    def create_team_invitation(self, invitation: TeamInvitationEntity) -> None:
        self._session.add(
            TeamInvitationOrm(
                id=invitation.id,
                team_id=invitation.team_id,
                invited_user_id=invitation.invited_user_id,
                status=invitation.status,
                position_id=invitation.position_id,
                created_at=invitation.created_at,
            )
        )
        self._notify(
            recipient_user_ids=[invitation.invited_user_id],
            notif_type=_NOTIFY_TEAM_INVITATION_SENT,
            actor_user_id=None,
            subject_id=invitation.id,
            now=invitation.created_at,
        )
        self._session.commit()

    def find_team_invitation(self, invitation_id: UUID) -> TeamInvitationEntity | None:
        row = self._session.get(TeamInvitationOrm, invitation_id)
        return None if row is None else self._to_invitation(row)

    def find_pending_invitation(
        self, team_id: UUID, invited_user_id: UUID
    ) -> TeamInvitationEntity | None:
        row = self._session.execute(
            select(TeamInvitationOrm).where(
                TeamInvitationOrm.team_id == team_id,
                TeamInvitationOrm.invited_user_id == invited_user_id,
                TeamInvitationOrm.status == PENDING,
            )
        ).scalars().first()
        return None if row is None else self._to_invitation(row)

    def list_team_invitations(self, team_id: UUID) -> list[TeamInvitationEntity]:
        """보낸 초대 전부. **초대받은 사람의 닉네임·카드 슬러그를 함께 싣는다.**

        🔴 **보낸 쪽 화면이 판을 되살리는 값이다**(2026-09-17). 주장이 스쿼드
        판에 앉힌 사람은 초대로 남는데, id 만으로는 새로고침 뒤에 누구인지도
        무슨 카드인지도 그릴 수가 없었다. 받는 쪽에 팀 넉 칸을 실어 준 것과
        같은 이유다 — **줄마다 따로 부르지 않게.**

        🔴 `player_card` 는 `card` 컨텍스트라 원시 쿼리로 **바깥 조인**한다.
        카드를 안 만든 사람은 `None` 이고 그것도 정상이다.
        """
        card_slug = (
            select(_card.c.public_slug)
            .where(_card.c.user_id == TeamInvitationOrm.invited_user_id)
            .limit(1)
            .scalar_subquery()
        )
        stmt = (
            select(TeamInvitationOrm, UserOrm.nickname, card_slug)
            .join(UserOrm, UserOrm.id == TeamInvitationOrm.invited_user_id)
            .where(TeamInvitationOrm.team_id == team_id)
            .order_by(TeamInvitationOrm.created_at.desc())
        )
        # 🔴 엔티티가 `frozen` 이라 대입이 아니라 `replace` 다.
        return [
            replace(
                self._to_invitation(row),
                invited_user_nickname=nickname,
                invited_user_card_slug=slug,
            )
            for row, nickname, slug in self._session.execute(stmt)
        ]

    def list_my_pending_invitations(
        self, user_id: UUID
    ) -> list[MyTeamInvitationEntity]:
        # 스쿼드는 `team_id` 에 유일 제약이 없다(`squad_orm.py` 참고 — ERD 에
        # 없는 제약은 늘리지 않았고 앱이 팀당 하나로 다룬다). 그래서 상관
        # 서브쿼리에 `limit(1)` 을 건다 — 여러 행이 생겨도 질의가 안 깨진다.
        squad_slug = (
            select(_squad.c.public_slug)
            .where(_squad.c.team_id == TeamInvitationOrm.team_id)
            .limit(1)
            .scalar_subquery()
        )
        stmt = (
            select(TeamInvitationOrm, TeamOrm, squad_slug)
            .join(TeamOrm, TeamOrm.id == TeamInvitationOrm.team_id)
            .where(
                TeamInvitationOrm.invited_user_id == user_id,
                TeamInvitationOrm.status == PENDING,
            )
            .order_by(TeamInvitationOrm.created_at.desc())
        )
        return [
            MyTeamInvitationEntity(
                invitation=self._to_invitation(invitation),
                team_name=team.name,
                team_region=team.region,
                team_sport_code=team.sport_code,
                squad_public_slug=slug,
            )
            for invitation, team, slug in self._session.execute(stmt)
        ]

    def accept_team_invitation(self, invitation_id: UUID) -> TeamInvitationEntity:
        row = self._session.get(TeamInvitationOrm, invitation_id)
        now = datetime.now(timezone.utc)
        row.status = ACCEPTED
        row.responded_at = now
        self._notify(
            recipient_user_ids=self._owner_user_ids(row.team_id),
            notif_type=_NOTIFY_TEAM_INVITATION_ACCEPTED,
            actor_user_id=row.invited_user_id,
            subject_id=row.id,
            now=now,
        )
        self._session.commit()
        return self._to_invitation(row)

    def reject_team_invitation(self, invitation_id: UUID) -> TeamInvitationEntity:
        row = self._session.get(TeamInvitationOrm, invitation_id)
        now = datetime.now(timezone.utc)
        row.status = REJECTED
        row.responded_at = now
        self._notify(
            recipient_user_ids=self._owner_user_ids(row.team_id),
            notif_type=_NOTIFY_TEAM_INVITATION_REJECTED,
            actor_user_id=row.invited_user_id,
            subject_id=row.id,
            now=now,
        )
        self._session.commit()
        return self._to_invitation(row)

    def cancel_team_invitation(self, invitation_id: UUID) -> TeamInvitationEntity:
        """보낸 팀이 스스로 무른다. 알림 없음(위 포트 docstring 참고)."""
        row = self._session.get(TeamInvitationOrm, invitation_id)
        row.status = CANCELLED
        row.responded_at = datetime.now(timezone.utc)
        self._session.commit()
        return self._to_invitation(row)

    def find_position(self, sport_code: str, code: str) -> tuple[UUID, str] | None:
        stmt = select(PositionOrm.id, PositionOrm.label).where(
            PositionOrm.sport_code == sport_code, PositionOrm.code == code
        )
        row = self._session.execute(stmt).first()
        return None if row is None else (row[0], row[1])

    def _to_invitation(self, row: TeamInvitationOrm) -> TeamInvitationEntity:
        # 자리를 정한 초대만 포지션 한 줄을 더 읽는다. 목록이 작고(한 사람이
        # 받은 대기 초대·한 팀이 보낸 초대) 같은 포지션은 세션 identity map 이
        # 재사용하므로 조인으로 넓히는 대신 이 편을 골랐다.
        position = (
            None
            if row.position_id is None
            else self._session.get(PositionOrm, row.position_id)
        )
        return TeamInvitationEntity(
            id=row.id,
            team_id=row.team_id,
            invited_user_id=row.invited_user_id,
            status=row.status,
            created_at=row.created_at,
            responded_at=row.responded_at,
            position_id=row.position_id,
            position_code=None if position is None else position.code,
            position_label=None if position is None else position.label,
        )
