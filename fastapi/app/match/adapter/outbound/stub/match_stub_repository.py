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
from app.match.domain.entities.match_entity import (
    MatchEntity,
    MatchListingEntity,
    PositionNeedEntity,
    TeamMatchRequestEntity,
)
from app.match.domain.rules.application_rules import SIDE_TEAM, SIDE_USER
from app.match.domain.rules.team_match_request_rules import ACCEPTED, CANCELLED, PENDING, REJECTED

_POSITIONS = {
    "football": {"GK": "골키퍼", "DF": "수비수", "MF": "미드필더", "FW": "공격수"},
    "baseball": {"P": "투수", "C": "포수", "IF": "내야수", "OF": "외야수"},
    "basketball": {"G": "가드", "F": "포워드", "C": "센터"},
}

_TEAMS: dict[UUID, str] = {}
# 팀의 표시용 값(이름·지역). 탐색 목록에만 쓰여서 `_TEAMS` 와 나눠 뒀다 —
# 합치면 종목을 읽는 자리가 전부 바뀐다.
_TEAM_META: dict[UUID, tuple[str, str]] = {}
# 팀 스쿼드의 공개 슬러그. **없는 팀이 정상**이라 기본값을 두지 않는다
# (스쿼드 생성이 멱등이라 늦게 생긴다).
_TEAM_SQUAD_SLUG: dict[UUID, str] = {}
_ROLES: dict[tuple[UUID, UUID], str] = {}
_MATCHES: dict[UUID, MatchEntity] = {}
_TEAM_MATCH_REQUESTS: dict[UUID, TeamMatchRequestEntity] = {}


def reset_matches() -> None:
    _TEAMS.clear()
    _TEAM_META.clear()
    _TEAM_SQUAD_SLUG.clear()
    _ROLES.clear()
    _MATCHES.clear()
    _APPLICATIONS.clear()
    _USERS.clear()
    _TEAM_MATCH_REQUESTS.clear()


def register_team(
    team_id: UUID, sport_code: str, name: str = "스텁 팀", region: str = "서울"
) -> None:
    """스텁에는 `team` 테이블이 없다. 검사가 "이 팀은 이 종목"이라고 알려 준다.

    `name`·`region` 은 **탐색 목록에만** 쓰인다. 기본값을 둔 이유는 기존 검사가
    종목만 넘기고 있어서다 — 탐색을 보는 검사만 값을 채운다.
    """
    _TEAMS[team_id] = sport_code
    _TEAM_META[team_id] = (name, region)


def register_squad_slug(team_id: UUID, public_slug: str) -> None:
    """그 팀 스쿼드의 공개 슬러그. 안 부르면 `None` 이고 그것도 정상이다."""
    _TEAM_SQUAD_SLUG[team_id] = public_slug


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

    def delete_application(self, application_id: UUID) -> None:
        _APPLICATIONS.pop(application_id, None)


class StubMatchRepository(StubApplicationsMixin, MatchPort):
    def team_exists(self, team_id: UUID) -> bool:
        return team_id in _TEAMS

    def sport_exists(self, sport_code: str) -> bool:
        return sport_code in _POSITIONS

    def search_upcoming(
        self,
        *,
        sport_code: str | None,
        region: str | None,
        now: datetime,
        offset: int,
        limit: int,
    ) -> tuple[list[MatchListingEntity], int]:
        found = []
        for match in _MATCHES.values():
            if match.played_at <= now:
                continue
            if match.opponent_team_id is not None:
                continue  # 팀 대 팀 확정 경기는 모집이 없다 — 탐색에 안 낸다.
            name, team_region = _TEAM_META.get(match.team_id, ("스텁 팀", "서울"))
            if sport_code and _TEAMS.get(match.team_id) != sport_code:
                continue
            # 실물은 ilike 부분 일치다. 대소문자는 한글에 뜻이 없지만 맞춰 둔다.
            if region and region.lower() not in team_region.lower():
                continue
            found.append(
                MatchListingEntity(
                    match=match,
                    team_name=name,
                    region=team_region,
                    sport_code=_TEAMS.get(match.team_id, ""),
                )
            )

        found.sort(key=lambda listing: listing.match.played_at)
        return found[offset : offset + limit], len(found)

    def team_role_of(self, team_id: UUID, user_id: UUID) -> str | None:
        return _ROLES.get((team_id, user_id))

    def update_match(
        self,
        match_id: UUID,
        *,
        played_at: datetime | None,
        place: str | None,
        needs: list[PositionNeedEntity] | None,
    ) -> None:
        match = _MATCHES[match_id]
        _MATCHES[match_id] = replace(
            match,
            played_at=played_at if played_at is not None else match.played_at,
            place=place if place is not None else match.place,
            needs=needs if needs is not None else match.needs,
        )

    def count_applications(self, match_id: UUID) -> int:
        return sum(1 for a in _APPLICATIONS.values() if a.match_id == match_id)

    def delete_match(self, match_id: UUID, actor_id: UUID) -> None:
        _MATCHES.pop(match_id, None)
        # 🔴 **DB 의 외래키를 흉내낸다.** `team_match_request.match_id` 는
        #    `ON DELETE SET NULL` 이라 경기가 지워지면 실물에서는 저절로
        #    비워진다(`status` 는 `accepted` 로 남는다). 여기서 안 비우면
        #    「물린 경기」가 스텁에서만 살아 있어, 겹치기 방지가 스텁으로는
        #    통과하고 실물에서 다르게 돈다.
        for rid, r in list(_TEAM_MATCH_REQUESTS.items()):
            if r.match_id == match_id:
                _TEAM_MATCH_REQUESTS[rid] = replace(r, match_id=None)

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

    def list_upcoming_matches(
        self, team_id: UUID, now: datetime
    ) -> list[MatchEntity]:
        found = [
            m
            for m in _MATCHES.values()
            if (m.team_id == team_id or m.opponent_team_id == team_id)
            and m.played_at > now
        ]
        return sorted(found, key=lambda m: m.played_at)

    # ------------------------------------------------------------------
    # 팀 대 팀 경기 신청 (`team_match_request`). `paik` 17번.
    # ------------------------------------------------------------------

    def owner_user_ids(self, team_id: UUID) -> list[UUID]:
        return [
            user_id
            for (t, user_id), role in _ROLES.items()
            if t == team_id and role == "owner"
        ]

    def create_team_match_request(
        self, request: TeamMatchRequestEntity
    ) -> TeamMatchRequestEntity:
        """알림 생성은 흉내 내지 않는다 — `notification_stub_repository.py`와
        같은 철학(알림은 DB 테스트만 본다)."""
        requester = _TEAM_META.get(request.requester_team_id, ("", ""))
        target = _TEAM_META.get(request.target_team_id, ("", ""))
        filled = replace(
            request,
            requester_team_name=requester[0],
            requester_team_region=requester[1],
            target_team_name=target[0],
            target_team_region=target[1],
            requester_squad_public_slug=_TEAM_SQUAD_SLUG.get(request.requester_team_id),
            target_squad_public_slug=_TEAM_SQUAD_SLUG.get(request.target_team_id),
        )
        _TEAM_MATCH_REQUESTS[request.id] = filled
        return filled

    def has_live_team_match_request(
        self, team_id: UUID, other_team_id: UUID, now: datetime
    ) -> bool:
        """까닭은 `MatchPort.has_live_team_match_request` 머리말."""
        pair = {team_id, other_team_id}
        return any(
            {r.requester_team_id, r.target_team_id} == pair
            and (
                r.status == PENDING
                or (
                    r.status == ACCEPTED
                    and r.match_id is not None
                    and r.proposed_played_at >= now
                )
            )
            for r in _TEAM_MATCH_REQUESTS.values()
        )

    def find_team_match_request(
        self, request_id: UUID
    ) -> TeamMatchRequestEntity | None:
        return _TEAM_MATCH_REQUESTS.get(request_id)

    def list_team_match_requests(
        self, team_id: UUID
    ) -> list[TeamMatchRequestEntity]:
        found = [
            r
            for r in _TEAM_MATCH_REQUESTS.values()
            if r.requester_team_id == team_id or r.target_team_id == team_id
        ]
        return sorted(found, key=lambda r: r.created_at, reverse=True)

    def accept_team_match_request(
        self, request_id: UUID
    ) -> TeamMatchRequestEntity:
        row = _TEAM_MATCH_REQUESTS[request_id]
        now = datetime.now(timezone.utc)
        match = MatchEntity(
            id=uuid4(),
            team_id=row.requester_team_id,
            opponent_team_id=row.target_team_id,
            played_at=row.proposed_played_at,
            place=row.proposed_place,
        )
        _MATCHES[match.id] = match
        row = replace(row, status=ACCEPTED, responded_at=now, match_id=match.id)
        _TEAM_MATCH_REQUESTS[request_id] = row

        involved = {row.requester_team_id, row.target_team_id}
        for other_id, other in list(_TEAM_MATCH_REQUESTS.items()):
            if other_id == request_id or other.status != PENDING:
                continue
            if (
                other.requester_team_id in involved
                or other.target_team_id in involved
            ):
                _TEAM_MATCH_REQUESTS[other_id] = replace(
                    other, status=CANCELLED, responded_at=now
                )
        return row

    def reject_team_match_request(
        self, request_id: UUID
    ) -> TeamMatchRequestEntity:
        row = replace(
            _TEAM_MATCH_REQUESTS[request_id],
            status=REJECTED,
            responded_at=datetime.now(timezone.utc),
        )
        _TEAM_MATCH_REQUESTS[request_id] = row
        return row

    def cancel_team_match_request(
        self, request_id: UUID
    ) -> TeamMatchRequestEntity:
        row = replace(
            _TEAM_MATCH_REQUESTS[request_id],
            status=CANCELLED,
            responded_at=datetime.now(timezone.utc),
        )
        _TEAM_MATCH_REQUESTS[request_id] = row
        return row
