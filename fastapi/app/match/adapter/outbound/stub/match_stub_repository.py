"""메모리 저장소. 계약 테스트가 DB 없이 돌기 위한 것이다.

포지션 목록은 마이그레이션(`20260902_match_tables`)이 넣는 값과 같다. 여기서
갈리면 스텁으로는 통과하고 실물에서 깨진다.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.match.application.ports.output.match_port import MatchPort
from app.match.domain.entities.application_entity import ApplicationEntity
from app.match.domain.entities.match_entity import MatchEntity, PositionNeedEntity
from app.match.domain.rules.application_rules import SIDE_TEAM, SIDE_USER

_POSITIONS = {
    "football": {"GK": "골키퍼", "DF": "수비수", "MF": "미드필더", "FW": "공격수"},
    "baseball": {"P": "투수", "C": "포수", "IF": "내야수", "OF": "외야수"},
    "basketball": {"G": "가드", "F": "포워드", "C": "센터"},
}

_TEAMS: dict[UUID, str] = {}
_ROLES: dict[tuple[UUID, UUID], str] = {}
_MATCHES: dict[UUID, MatchEntity] = {}


def reset_matches() -> None:
    _TEAMS.clear()
    _ROLES.clear()
    _MATCHES.clear()
    _APPLICATIONS.clear()
    _USERS.clear()


def register_team(team_id: UUID, sport_code: str) -> None:
    """스텁에는 `team` 테이블이 없다. 검사가 "이 팀은 이 종목"이라고 알려 준다."""
    _TEAMS[team_id] = sport_code


def register_role(team_id: UUID, user_id: UUID, role: str) -> None:
    _ROLES[(team_id, user_id)] = role


_APPLICATIONS: dict[UUID, ApplicationEntity] = {}
_USERS: dict[UUID, str] = {}


def register_user(user_id: UUID, nickname: str = "지원자") -> None:
    """스텁에는 `user` 테이블이 없다. 검사가 "이 사람은 있다"고 알려 준다."""
    _USERS[user_id] = nickname


class StubApplicationsMixin:
    """지원·제안 부분. 저장소 본체와 같은 모듈에 두어 상태를 공유한다."""

    def user_exists(self, user_id: UUID) -> bool:
        return user_id in _USERS

    def find_application(
        self, match_id: UUID, user_id: UUID
    ) -> ApplicationEntity | None:
        return next(
            (
                a
                for a in _APPLICATIONS.values()
                if a.match_id == match_id and a.user_id == user_id
            ),
            None,
        )

    def find_application_by_id(
        self, application_id: UUID
    ) -> ApplicationEntity | None:
        return _APPLICATIONS.get(application_id)

    def list_applications(self, match_id: UUID) -> list[ApplicationEntity]:
        return [a for a in _APPLICATIONS.values() if a.match_id == match_id]

    def create_application(
        self, match_id: UUID, user_id: UUID, side: str
    ) -> ApplicationEntity:
        now = datetime.now(timezone.utc)
        app = ApplicationEntity(
            id=uuid4(),
            match_id=match_id,
            user_id=user_id,
            nickname=_USERS.get(user_id, "지원자"),
            user_accepted_at=now if side == SIDE_USER else None,
            team_accepted_at=now if side == SIDE_TEAM else None,
        )
        _APPLICATIONS[app.id] = app
        return app

    def accept_application(self, application_id: UUID, side: str) -> ApplicationEntity:
        app = _APPLICATIONS[application_id]
        now = datetime.now(timezone.utc)
        if side == SIDE_USER:
            app = replace(app, user_accepted_at=app.user_accepted_at or now)
        else:
            app = replace(app, team_accepted_at=app.team_accepted_at or now)
        _APPLICATIONS[application_id] = app
        return app


class StubMatchRepository(StubApplicationsMixin, MatchPort):
    def team_exists(self, team_id: UUID) -> bool:
        return team_id in _TEAMS

    def team_role_of(self, team_id: UUID, user_id: UUID) -> str | None:
        return _ROLES.get((team_id, user_id))

    def find_positions(
        self, team_id: UUID, codes: list[str]
    ) -> dict[str, PositionNeedEntity]:
        labels = _POSITIONS.get(_TEAMS.get(team_id, ""), {})
        return {
            code: PositionNeedEntity(
                position_id=uuid4(), code=code, label=labels[code], head_count=0
            )
            for code in codes
            if code in labels
        }

    def create_match(self, match: MatchEntity) -> None:
        _MATCHES[match.id] = match

    def find_match(self, match_id: UUID) -> MatchEntity | None:
        return _MATCHES.get(match_id)
