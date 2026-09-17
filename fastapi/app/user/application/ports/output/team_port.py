"""팀 출력 포트. 구현은 `adapter/outbound/pg/` (계약 테스트는 스텁을 끼운다)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.user.domain.entities.team_entity import (
    MyTeamInvitationEntity,
    TeamEntity,
    TeamInvitationEntity,
    TeamMemberEntity,
)


class TeamPort(ABC):
    @abstractmethod
    def sport_exists(self, sport_code: str) -> bool:
        """`sport` 에 있는 코드인가.

        `team.sport_code` 에는 **외래키가 없다**(부록 D.3 의 외래키 표에 없어서
        늘리지 않았다). 그래서 DB 가 막아 주지 않는 것을 입력 검증으로 거른다 —
        오타로 들어온 종목은 나중에 매칭에서 조용히 아무와도 안 걸린다.

        🔴 **"지금 받는 종목인가"는 이것이 아니라 `sport_is_active` 다** —
        내려간 종목도 행은 남아 있다(`ho` 39번). 읽기·거르기는 그대로
        돌아야 하므로 이 메서드는 `active` 를 안 본다.
        """

    @abstractmethod
    def sport_is_active(self, sport_code: str) -> bool:
        """**지금 새로 받을 수 있는 종목인가**(`sport.active`, `ho` 39번).

        루브릭이 사라진 종목(야구·농구)은 행은 남아 있지만 `false` 다 —
        이미 그 종목으로 올라간 데이터가 참조하고 있어 지울 수 없어서다.
        새로 만드는 자리(팀 만들기)만 이것으로 막는다.
        """

    @abstractmethod
    def find_team(self, team_id: UUID) -> TeamEntity | None: ...

    @abstractmethod
    def update_team(
        self, team_id: UUID, name: str | None, region: str | None
    ) -> TeamEntity | None:
        """팀 이름·지역을 고치고 갱신된 팀을 돌려준다. 없으면 `None`.

        **`None` 인 인자는 안 건드린다.** 둘 다 `None` 이면 아무것도 안 바꾸고
        지금 팀을 돌려준다. 🔴 `sport_code` 를 받는 자리를 두지 않는다 —
        `UpdateTeamCommand` 주석 참고.
        """

    @abstractmethod
    def active_members(self, team_id: UUID) -> list[TeamMemberEntity]:
        """지금 소속된 구성원. **나간 사람(`left_at`)은 담지 않는다.**"""

    @abstractmethod
    def create_team(self, team: TeamEntity, owner_id: UUID) -> None:
        """팀과 `owner` 소속 1건을 **같은 트랜잭션에서** 만든다.

        나눠 쓰면 팀만 생기고 주장이 없는 상태가 남을 수 있다.
        """

    @abstractmethod
    def add_member(self, team_id: UUID, user_id: UUID) -> None:
        """`member` 로 넣는다. 재가입이면 새 행이다(부록 D.7 유일 제약이 셋 묶음)."""

    @abstractmethod
    def mark_left(self, team_id: UUID, user_id: UUID) -> None:
        """`left_at` 을 채운다. **행을 지우지 않는다** — 경기·평가 이력이 참조한다."""

    @abstractmethod
    def user_exists(self, user_id: UUID) -> bool: ...

    # --- 팀 초대 (`min` 20번) ------------------------------------------------

    @abstractmethod
    def create_team_invitation(self, invitation: TeamInvitationEntity) -> None:
        """초대와 그 사람에게 갈 알림을 **같은 트랜잭션에서** 만든다."""

    @abstractmethod
    def find_team_invitation(self, invitation_id: UUID) -> TeamInvitationEntity | None: ...

    @abstractmethod
    def find_pending_invitation(
        self, team_id: UUID, invited_user_id: UUID
    ) -> TeamInvitationEntity | None:
        """그 팀이 그 사람에게 보낸, 아직 답 안 한 초대. 중복 초대를 막는 데 쓴다."""

    @abstractmethod
    def list_team_invitations(self, team_id: UUID) -> list[TeamInvitationEntity]:
        """그 팀이 보낸 초대 전부(상태 무관), 최신순."""

    @abstractmethod
    def list_my_pending_invitations(
        self, user_id: UUID
    ) -> list[MyTeamInvitationEntity]:
        """내가 받은, 아직 답 안 한 초대만, 최신순.

        🔴 **팀 쪽 값을 함께 싣는다**(`paik` 37번) — 받는 사람은 그 팀 소속이
        아니라 팀 화면을 거치지 않고 알림에서 바로 정한다. 스쿼드 슬러그까지
        함께 주면 화면이 이미 있는 `GET /squads/{slug}` 로 판을 그릴 수 있어
        새 경로가 필요 없다.
        """

    @abstractmethod
    def find_position(self, sport_code: str, code: str) -> tuple[UUID, str] | None:
        """`(id, label)`. 약칭은 **종목 안에서만** 유일하므로 종목과 함께 찾는다."""

    @abstractmethod
    def accept_team_invitation(self, invitation_id: UUID) -> TeamInvitationEntity:
        """`accepted`로 놓고 그 팀 주장(들)에게 알린다.

        🔴 **`team_member`를 여기서 만들지 않는다** — 그건 기존
        `JoinTeamUseCase`(자기-가입)가 한다. 이 메서드는 초대 쪽 상태만
        맡는다(인터랙터가 순서를 조율한다).
        """

    @abstractmethod
    def reject_team_invitation(self, invitation_id: UUID) -> TeamInvitationEntity:
        """`rejected`로 놓고 그 팀 주장(들)에게 알린다."""

    @abstractmethod
    def cancel_team_invitation(self, invitation_id: UUID) -> TeamInvitationEntity:
        """`cancelled`로 놓는다. 보낸 쪽이 스스로 무르는 것이라 알림 없음
        (`team_match_request.cancel`과 같은 판단)."""
