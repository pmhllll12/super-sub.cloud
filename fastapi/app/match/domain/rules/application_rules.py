"""지원·제안 규칙. **HTTP도 DB도 없다.**"""

from __future__ import annotations

from uuid import UUID

from app.match.domain.entities.application_entity import ApplicationEntity
from app.match.domain.rules.match_rules import OWNER_ROLE

# 수락할 수 있는 쪽. 문자열 대신 이 상수를 쓰는 이유는 저장소가 어느 컬럼을 채울지
# 이 값으로 고르기 때문이다 — 오타가 나면 조용히 아무 컬럼도 안 찬다.
SIDE_USER = "user"
SIDE_TEAM = "team"


def can_apply(team_role: str | None) -> bool:
    """스스로 지원할 수 있는가. **그 팀 소속이면 안 된다.**

    이 서비스는 팀에 없는 사람을 부르는 용병 매칭이다(1장). 소속 선수가 자기 팀
    경기에 "지원"하는 것은 뜻이 없고, 적합도(SFR-006)도 외부인 기준으로 계산된다.

    ⚠️ 스키마가 막는 것이 아니라 **앱이 정한 규칙**이다. 팀 내부 참가 신청까지
    담게 되면 여기를 고친다.
    """
    return team_role is None


def can_offer(team_role: str | None) -> bool:
    """팀이 특정 사람에게 제안할 수 있는가. 주장만 한다."""
    return team_role == OWNER_ROLE


def acceptable_side(
    application: ApplicationEntity, actor_id: UUID, actor_is_owner: bool
) -> str | None:
    """이 사람이 지금 수락할 수 있는 쪽. 없으면 None.

    **자기 쪽은 이미 차 있다.** 지원한 사람이 자기 지원을 또 수락하는 것은 뜻이
    없으므로, 비어 있는 반대쪽만 채울 수 있다.
    """
    if actor_id == application.user_id and application.user_accepted_at is None:
        return SIDE_USER
    if actor_is_owner and application.team_accepted_at is None:
        return SIDE_TEAM
    return None


def can_remove(
    application: ApplicationEntity, actor_id: UUID, actor_is_owner: bool
) -> bool:
    """이 사람이 이 지원 건을 없앨 수 있는가.

    **무르기와 거절은 같은 동작이다** — 지원 당사자가 하면 무르기, 주최 팀 주장이
    하면 거절이고, 둘 다 **행을 지운다.**

    🔴 **거절을 컬럼으로 담지 않는 이유** (미결 `jin` 16번, A-1 채택):
    `match_application.match_id` 의 삭제 규칙이 RESTRICT 라 **행이 남아 있는 한
    경기를 취소할 수 없다.** 거절 시각 컬럼을 늘리면 부록 D 를 고치고도 그
    막다른 곳이 그대로다. 지금 스키마가 이미 "행이 없으면 취소된다"고 말하고
    있으므로 거기에 맞춘다.

    ⚠️ **그래서 거절 이력이 남지 않는다.** 나중에 필요해지면 컬럼이 아니라
    별도 테이블이어야 한다(행이 남으면 같은 문제가 돌아온다).
    """
    return actor_is_owner or actor_id == application.user_id


def has_stake(
    application: ApplicationEntity, actor_id: UUID, actor_is_owner: bool
) -> bool:
    """이 건에 관계된 사람인가 (지원 당사자이거나 주최 팀 주장이거나).

    `acceptable_side` 가 None 인 이유가 **권한이 없어서**인지 **이미 수락해서**인지를
    가르는 데 쓴다. 둘을 같은 에러로 내면 남의 지원 건이 있는지 없는지가 새어 나간다.
    """
    return actor_id == application.user_id or actor_is_owner
