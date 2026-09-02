"""경기 인터랙터. 권한·기한 판단은 `domain/rules/match_rules.py` 가 한다."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

from app.core.errors import ApiError
from app.match.application.dtos.match_dto import (
    CreateMatchCommand,
    MatchQuery,
    MatchResult,
    TeamMatchesQuery,
)
from app.match.application.ports.input.match_use_cases import (
    CreateMatchUseCase,
    ListTeamMatchesUseCase,
    ReadMatchUseCase,
)
from app.match.application.ports.output.match_port import MatchPort
from app.match.application.use_cases.match_assembler import to_match_result
from app.match.domain.entities.match_entity import MatchEntity
from app.match.domain.rules.match_rules import can_register, is_registrable


class CreateMatchInteractor(CreateMatchUseCase):
    def __init__(self, repository: MatchPort) -> None:
        self._repository = repository

    def __call__(self, command: CreateMatchCommand) -> MatchResult:
        if not self._repository.team_exists(command.team_id):
            raise ApiError(404, "TEAM_NOT_FOUND", "팀을 찾을 수 없습니다.")

        role = self._repository.team_role_of(command.team_id, command.actor_id)
        if not can_register(role):
            raise ApiError(403, "FORBIDDEN", "주장만 경기를 등록할 수 있습니다.")

        if not is_registrable(command.played_at, datetime.now(timezone.utc)):
            raise ApiError(422, "PAST_MATCH", "지난 시각으로는 등록할 수 없습니다.")

        codes = [n.position_code for n in command.needs]
        if len(set(codes)) != len(codes):
            # 같은 포지션을 두 줄로 적으면 인원이 갈린다. 유일 제약도 이것을 막지만
            # 그때는 500 이 되므로 여기서 뜻이 있는 에러로 돌려준다.
            raise ApiError(
                422, "DUPLICATE_POSITION", "같은 포지션을 두 번 적을 수 없습니다."
            )

        found = self._repository.find_positions(command.team_id, codes)
        missing = [c for c in codes if c not in found]
        if missing:
            raise ApiError(
                422,
                "UNKNOWN_POSITION",
                f"이 종목에 없는 포지션입니다: {', '.join(missing)}",
            )

        match = MatchEntity(
            id=uuid4(),
            team_id=command.team_id,
            played_at=command.played_at,
            place=command.place,
            needs=[
                replace(found[n.position_code], head_count=n.head_count)
                for n in command.needs
            ],
        )
        self._repository.create_match(match)
        return to_match_result(match)


class ReadMatchInteractor(ReadMatchUseCase):
    def __init__(self, repository: MatchPort) -> None:
        self._repository = repository

    def __call__(self, query: MatchQuery) -> MatchResult:
        match = self._repository.find_match(query.match_id)
        if match is None:
            raise ApiError(404, "MATCH_NOT_FOUND", "경기를 찾을 수 없습니다.")
        return to_match_result(match)


class ListTeamMatchesInteractor(ListTeamMatchesUseCase):
    def __init__(self, repository: MatchPort) -> None:
        self._repository = repository

    def __call__(self, query: TeamMatchesQuery) -> list[MatchResult]:
        """팀이 없으면 404 다.

        빈 배열로 답하면 **없는 팀과 경기 없는 팀이 같아 보인다** — 클라이언트가
        오타 난 id 를 "아직 경기가 없구나"로 읽는다.
        """
        if not self._repository.team_exists(query.team_id):
            raise ApiError(404, "TEAM_NOT_FOUND", "팀을 찾을 수 없습니다.")

        matches = self._repository.list_upcoming_matches(
            query.team_id, datetime.now(timezone.utc)
        )
        return [to_match_result(m) for m in matches]

