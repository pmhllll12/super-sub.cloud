"""스쿼드 인터랙터. 권한 판단은 `domain/rules/squad_rules.py` 가 한다."""

from __future__ import annotations

from uuid import UUID

from app.card.application.dtos.squad_dto import (
    CreateSquadCommand,
    DischargeMemberCommand,
    EnlistCardCommand,
    PublicSquadQuery,
    SquadCreation,
    SquadResult,
    TeamSquadQuery,
)
from app.card.application.ports.input.squad_use_cases import (
    CreateSquadUseCase,
    DischargeMemberUseCase,
    EnlistCardUseCase,
    PublicSquadUseCase,
    TeamSquadUseCase,
)
from app.card.application.ports.output.squad_port import SquadPort
from app.card.application.use_cases.squad_assembler import to_squad_result
from app.card.domain.entities.squad_entity import SquadEntity
from app.card.domain.rules.squad_rules import can_manage, can_read
from app.core.errors import ApiError


def _require_owner(repository: SquadPort, team_id: UUID, actor_id: UUID) -> None:
    """팀이 있고 부르는 사람이 주장인지. 아니면 여기서 끝난다."""

    if not repository.team_exists(team_id):
        raise ApiError(404, "TEAM_NOT_FOUND", "팀을 찾을 수 없습니다.")
    if not can_manage(repository.team_role_of(team_id, actor_id)):
        raise ApiError(403, "FORBIDDEN", "주장만 스쿼드를 관리할 수 있습니다.")


def _squad_of(repository: SquadPort, team_id: UUID) -> SquadEntity:
    """이 팀의 스쿼드. 없으면 404 — 만들기 전에는 등재할 대상이 없다."""
    squad = repository.find_by_team(team_id)
    if squad is None:
        raise ApiError(404, "SQUAD_NOT_FOUND", "스쿼드가 없습니다.")
    return squad


class CreateSquadInteractor(CreateSquadUseCase):
    def __init__(self, repository: SquadPort) -> None:
        self._repository = repository

    def __call__(self, command: CreateSquadCommand) -> SquadCreation:
        """**멱등이다.** 두 번 불러도 스쿼드는 하나고 슬러그도 그대로다.

        공유 링크가 재시도로 바뀌면 안 되기 때문이다 — `POST /me/card` 와 같은
        판단이다.
        """
        _require_owner(self._repository, command.team_id, command.actor_id)
        squad, created = self._repository.create_for_team(command.team_id)
        return SquadCreation(squad=to_squad_result(squad), created=created)


class TeamSquadInteractor(TeamSquadUseCase):
    def __init__(self, repository: SquadPort) -> None:
        self._repository = repository

    def __call__(self, query: TeamSquadQuery) -> SquadResult:
        if not self._repository.team_exists(query.team_id):
            raise ApiError(404, "TEAM_NOT_FOUND", "팀을 찾을 수 없습니다.")
        if not can_read(self._repository.team_role_of(query.team_id, query.actor_id)):
            # 슬러그를 아는 사람은 누구나 볼 수 있으므로 비밀을 지키는 검사가
            # 아니다. **팀 id 로 남의 팀 구성을 훑는 것**을 막는 자리다.
            raise ApiError(403, "FORBIDDEN", "팀 구성원만 볼 수 있습니다.")
        return to_squad_result(_squad_of(self._repository, query.team_id))


class PublicSquadInteractor(PublicSquadUseCase):
    def __init__(self, repository: SquadPort) -> None:
        self._repository = repository

    def __call__(self, query: PublicSquadQuery) -> SquadResult:
        squad = self._repository.find_by_slug(query.public_slug)
        if squad is None:
            raise ApiError(404, "SQUAD_NOT_FOUND", "스쿼드를 찾을 수 없습니다.")
        return to_squad_result(squad)


class EnlistCardInteractor(EnlistCardUseCase):
    def __init__(self, repository: SquadPort) -> None:
        self._repository = repository

    def __call__(self, command: EnlistCardCommand) -> SquadResult:
        _require_owner(self._repository, command.team_id, command.actor_id)
        squad = _squad_of(self._repository, command.team_id)

        owner = self._repository.card_owner(command.player_card_id)
        if owner is None:
            raise ApiError(404, "CARD_NOT_FOUND", "카드를 찾을 수 없습니다.")

        # 🔴 스쿼드는 **팀의** 카드 묶음이다(부록 D 도메인 ③). 아무 카드나 넣을 수
        #    있으면 남의 선수로 팀을 꾸민 것처럼 보이게 만들 수 있다.
        #
        #    ⚠️ 이것은 스키마가 아니라 **앱이 정한 규칙**이다. 용병을 스쿼드에
        #    넣어야 할 일이 생기면 여기를 고치면 된다(외래키는 그대로 둔다).
        if not can_read(self._repository.team_role_of(command.team_id, owner)):
            raise ApiError(
                422, "NOT_TEAM_MEMBER", "팀 구성원의 카드만 등재할 수 있습니다."
            )

        found = self._repository.find_position(command.team_id, command.position_code)
        if found is None:
            raise ApiError(
                422, "UNKNOWN_POSITION", "이 종목에 없는 포지션입니다."
            )
        position_id, _ = found

        try:
            self._repository.enlist(squad.id, command.player_card_id, position_id)
        except ValueError:
            # 저장소가 유일 제약 위반을 이것으로 바꿔 올린다. 500 으로 새어 나가면
            # 클라이언트가 "서버가 터졌다"로 읽는다.
            raise ApiError(
                409, "ALREADY_ENLISTED", "이미 등재된 카드입니다."
            ) from None

        return to_squad_result(_squad_of(self._repository, command.team_id))


class DischargeMemberInteractor(DischargeMemberUseCase):
    def __init__(self, repository: SquadPort) -> None:
        self._repository = repository

    def __call__(self, command: DischargeMemberCommand) -> SquadResult:
        _require_owner(self._repository, command.team_id, command.actor_id)
        squad = _squad_of(self._repository, command.team_id)

        found = self._repository.find_member(command.member_id)
        # 🔴 **그 등재가 이 팀 스쿼드의 것인지 확인한다.** 안 하면 주장이 남의
        #    스쿼드에서 카드를 뺄 수 있다 — id 만 알면 되기 때문이다.
        if found is None or found[0] != squad.id:
            raise ApiError(404, "MEMBER_NOT_FOUND", "등재를 찾을 수 없습니다.")

        self._repository.discharge(command.member_id)
        return to_squad_result(_squad_of(self._repository, command.team_id))
