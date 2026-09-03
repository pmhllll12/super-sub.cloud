"""경기 인터랙터. 권한·기한 판단은 `domain/rules/match_rules.py` 가 한다."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.core.errors import ApiError
from app.match.application.dtos.match_dto import (
    CancelMatchCommand,
    CreateMatchCommand,
    MatchQuery,
    MatchResult,
    MatchSearchQuery,
    MatchSearchResult,
    PositionNeedInput,
    TeamMatchesQuery,
    UpdateMatchCommand,
)
from app.match.application.ports.input.match_use_cases import (
    CancelMatchUseCase,
    CreateMatchUseCase,
    ListTeamMatchesUseCase,
    ReadMatchUseCase,
    SearchMatchesUseCase,
    UpdateMatchUseCase,
)
from app.match.application.ports.output.match_port import MatchPort
from app.match.application.use_cases.match_assembler import (
    to_listing_result,
    to_match_result,
)
from app.match.domain.entities.match_entity import MatchEntity, PositionNeedEntity
from app.match.domain.rules.match_rules import can_register, is_registrable


def _resolve_needs(
    repository: MatchPort, team_id: UUID, needs: list[PositionNeedInput]
) -> list[PositionNeedEntity]:
    """요청의 포지션 코드를 **그 팀 종목의** 포지션으로 바꾼다.

    등록과 수정이 같은 검증을 쓴다 — 갈리면 한쪽으로만 이상한 값이 들어간다.
    """
    codes = [n.position_code for n in needs]
    if len(set(codes)) != len(codes):
        # 같은 포지션을 두 줄로 적으면 인원이 갈린다. 유일 제약도 이것을 막지만
        # 그때는 500 이 되므로 여기서 뜻이 있는 에러로 돌려준다.
        raise ApiError(
            422, "DUPLICATE_POSITION", "같은 포지션을 두 번 적을 수 없습니다."
        )

    found = repository.find_positions(team_id, codes)
    missing = [c for c in codes if c not in found]
    if missing:
        raise ApiError(
            422,
            "UNKNOWN_POSITION",
            f"이 종목에 없는 포지션입니다: {', '.join(missing)}",
        )
    return [replace(found[n.position_code], head_count=n.head_count) for n in needs]


def _require_captain(repository: MatchPort, match_id: UUID, actor_id: UUID):
    """경기가 있고 부르는 사람이 그 팀 주장인지. 아니면 여기서 끝난다."""
    match = repository.find_match(match_id)
    if match is None:
        raise ApiError(404, "MATCH_NOT_FOUND", "경기를 찾을 수 없습니다.")
    if not can_register(repository.team_role_of(match.team_id, actor_id)):
        raise ApiError(403, "FORBIDDEN", "주장만 경기를 관리할 수 있습니다.")
    return match


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

        match = MatchEntity(
            id=uuid4(),
            team_id=command.team_id,
            played_at=command.played_at,
            place=command.place,
            needs=_resolve_needs(self._repository, command.team_id, command.needs),
        )
        self._repository.create_match(match)
        return to_match_result(match)


class UpdateMatchInteractor(UpdateMatchUseCase):
    """경기를 고친다. **주장만.**

    ⚠️ **지원자가 있어도 막지 않는다.** 시각·장소가 바뀌면 알려야 하지만 알림
    인프라가 없다 — 막아 버리면 오타 하나를 못 고치게 되고, 그쪽이 더 나쁘다.
    계약 문서에 "알림이 안 간다"를 적어 두고 미결 항목으로 올렸다.
    """

    def __init__(self, repository: MatchPort) -> None:
        self._repository = repository

    def __call__(self, command: UpdateMatchCommand) -> MatchResult:
        match = _require_captain(
            self._repository, command.match_id, command.actor_id
        )
        now = datetime.now(timezone.utc)

        # 🔴 **이미 지난 경기는 못 고친다.** 끝난 일을 고치는 것은 기록을 바꾸는
        #    것이지 모집을 고치는 것이 아니다.
        if not is_registrable(match.played_at, now):
            raise ApiError(422, "PAST_MATCH", "지난 경기는 고칠 수 없습니다.")

        if command.played_at is not None and not is_registrable(
            command.played_at, now
        ):
            raise ApiError(422, "PAST_MATCH", "지난 시각으로는 옮길 수 없습니다.")

        needs = (
            None
            if command.needs is None
            else _resolve_needs(self._repository, match.team_id, command.needs)
        )
        self._repository.update_match(
            command.match_id,
            played_at=command.played_at,
            place=command.place,
            needs=needs,
        )

        # 저장된 것을 다시 읽어 돌려준다 — 안 바꾼 항목까지 실제 값으로 채우려면
        # 이 편이 정확하다. 손으로 합치면 저장과 응답이 갈릴 수 있다.
        updated = self._repository.find_match(command.match_id)
        assert updated is not None, "방금 고친 경기가 사라졌다"
        return to_match_result(updated)


class CancelMatchInteractor(CancelMatchUseCase):
    """경기를 취소한다 = **행을 지운다.**

    부록 D 의 `match` 에는 상태 컬럼이 없고 D.8 도 취소를 다루지 않아 `canceled_at`
    을 늘리지 않았다. 대신 **스키마가 이미 말하고 있는 것**을 따른다 —
    `match_application.match_id` 의 삭제 규칙이 RESTRICT 라 지원이 붙은 경기는
    DB 가 못 지우게 한다.
    """

    def __init__(self, repository: MatchPort) -> None:
        self._repository = repository

    def __call__(self, command: CancelMatchCommand) -> None:
        match = _require_captain(
            self._repository, command.match_id, command.actor_id
        )

        if not is_registrable(match.played_at, datetime.now(timezone.utc)):
            # 이미 열린 경기를 "취소"하는 것은 뜻이 없다. 지난 경기를 지우는 것은
            # 관리 기능이지 취소가 아니다.
            raise ApiError(422, "PAST_MATCH", "지난 경기는 취소할 수 없습니다.")

        if self._repository.count_applications(command.match_id) > 0:
            # 🔴 외래키가 이미 막지만 그대로 두면 500 이다. 그리고 지원자에게
            #    알릴 방법이 없어(알림 인프라 없음) **사람이 먼저 정리해야 한다.**
            raise ApiError(
                409,
                "MATCH_HAS_APPLICATIONS",
                "지원자가 있어 취소할 수 없습니다. 지원을 먼저 정리해 주십시오.",
            )

        self._repository.delete_match(command.match_id)


class ReadMatchInteractor(ReadMatchUseCase):
    def __init__(self, repository: MatchPort) -> None:
        self._repository = repository

    def __call__(self, query: MatchQuery) -> MatchResult:
        match = self._repository.find_match(query.match_id)
        if match is None:
            raise ApiError(404, "MATCH_NOT_FOUND", "경기를 찾을 수 없습니다.")
        return to_match_result(match)


class SearchMatchesInteractor(SearchMatchesUseCase):
    """종목·지역으로 다가오는 경기를 찾는다.

    **이 경로가 없으면 용병은 지원할 경기를 찾을 수 없다** — 다른 목록은 전부
    팀 id 를 알아야 한다.
    """

    def __init__(self, repository: MatchPort) -> None:
        self._repository = repository

    def __call__(self, query: MatchSearchQuery) -> MatchSearchResult:
        if query.sport_code and not self._repository.sport_exists(query.sport_code):
            # 🔴 빈 배열로 답하지 않는다. 오타 난 종목과 "그 종목 경기가 없다"가
            #    같아 보이면 사용자는 없는 것을 계속 기다린다.
            raise ApiError(422, "UNKNOWN_SPORT", "지원하지 않는 종목입니다.")

        listings, total = self._repository.search_upcoming(
            sport_code=query.sport_code,
            region=query.region,
            now=datetime.now(timezone.utc),
            offset=(query.page - 1) * query.size,
            limit=query.size,
        )
        return MatchSearchResult(
            items=[to_listing_result(listing) for listing in listings],
            total=total,
            page=query.page,
            size=query.size,
        )


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

