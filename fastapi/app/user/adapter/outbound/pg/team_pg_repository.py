"""`TeamPort` 의 PostgreSQL 구현.

`team`·`team_member`·`user`·`sport` 는 **전부 `user` 컨텍스트의 테이블**이라
ORM 을 그대로 쓴다.

🔴 **`player_card` 만 예외다.** 저쪽은 `card` 컨텍스트라 임포트하지 않고
`table()`/`column()` 으로 읽는다(2026-09-04 추가 — 미결 `paik` 2번).
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import column, insert, select, table, update
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.user.adapter.outbound.orm.sport_orm import SportOrm
from app.user.adapter.outbound.orm.team_invitation_orm import TeamInvitationOrm
from app.user.adapter.outbound.orm.team_member_orm import TeamMemberOrm
from app.user.adapter.outbound.orm.team_orm import TeamOrm
from app.user.adapter.outbound.orm.user_orm import UserOrm
from app.user.application.ports.output.team_port import TeamPort
from app.user.domain.entities.team_entity import (
    TeamEntity,
    TeamInvitationEntity,
    TeamMemberEntity,
)
from app.user.domain.rules.team_invitation_rules import ACCEPTED, PENDING, REJECTED, CANCELLED
from app.user.domain.value_objects.team_role_vo import TeamRole


# 소유하지 않는 테이블에서 **읽기만** 한다. 위 docstring 참조.
_card = table("player_card", column("id"), column("user_id"), column("public_slug"))

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
        stmt = (
            select(TeamInvitationOrm)
            .where(TeamInvitationOrm.team_id == team_id)
            .order_by(TeamInvitationOrm.created_at.desc())
        )
        return [self._to_invitation(r) for r in self._session.execute(stmt).scalars()]

    def list_my_pending_invitations(
        self, user_id: UUID
    ) -> list[TeamInvitationEntity]:
        stmt = (
            select(TeamInvitationOrm)
            .where(
                TeamInvitationOrm.invited_user_id == user_id,
                TeamInvitationOrm.status == PENDING,
            )
            .order_by(TeamInvitationOrm.created_at.desc())
        )
        return [self._to_invitation(r) for r in self._session.execute(stmt).scalars()]

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

    def _to_invitation(self, row: TeamInvitationOrm) -> TeamInvitationEntity:
        return TeamInvitationEntity(
            id=row.id,
            team_id=row.team_id,
            invited_user_id=row.invited_user_id,
            status=row.status,
            created_at=row.created_at,
            responded_at=row.responded_at,
        )
