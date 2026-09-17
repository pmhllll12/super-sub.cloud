"""`team` 과 그 구성원. 부록 D 도메인 ①."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.user.domain.value_objects.team_role_vo import TeamRole


@dataclass(frozen=True)
class TeamEntity:
    """팀 1개.

    **종목은 팀이 정한다**(5장 SFR-010) — 경기에 종목 컬럼을 따로 두지 않고
    `match -> team -> sport_code` 로 결정된다(부록 D.4).
    """

    id: UUID
    name: str
    region: str
    sport_code: str
    # 해체 시각(`paik` 35번). `None` 이면 살아 있는 팀이다.
    #
    # 🔴 행을 지우지 않는다 — 지난 경기·평가가 이 팀 이름을 가리킨다
    # (`team_member.left_at` 과 같은 판단, 부록 D.6). 해체된 팀은 **새로
    # 만드는 자리만** 막고 읽기·이력은 그대로다(`sport.active` 와 같다).
    disbanded_at: datetime | None = None

    @property
    def is_disbanded(self) -> bool:
        return self.disbanded_at is not None


@dataclass(frozen=True)
class TeamMemberEntity:
    """지금 소속된 구성원 1명.

    나간 사람은 여기 담지 않는다 — `team_member` 는 `left_at` 으로 소프트 삭제라
    거르는 것은 도메인 규칙의 몫이다(`membership_rules.active_memberships` 와 같은 결).
    """

    user_id: UUID
    nickname: str
    role: TeamRole
    joined_at: datetime
    # 그 사람의 선수 카드. **없을 수 있다** — 카드를 안 만든 구성원도 팀에는
    # 있는 사람이라 목록에서 빼지 않는다(미결 `paik` 2번의 「하지 말 것」).
    #
    # 🔴 둘을 함께 싣는 이유: 스쿼드 등재(`POST /teams/{id}/squad/members`)는
    # 내부 id 를 받고, 카드로 가는 링크는 `public_slug` 를 쓴다. 하나만 주면
    # 화면이 나머지를 얻을 경로가 없다 — 남의 카드를 슬러그로 찾을 수도,
    # 내부 id 로 열 수도 없기 때문이다.
    player_card_id: UUID | None = None
    card_public_slug: str | None = None


@dataclass(frozen=True)
class TeamInvitationEntity:
    """팀이 개인을 데려오는 초대 1건 (`min` 20번).

    `team_match_request`(팀 대 팀)와 상태 전이 모양만 같다 — `status`가
    `pending`/`accepted`/`rejected`/`cancelled` 문자열인 이유도 같다
    (`analysis_job.status`처럼 단계가 늘 때 마이그레이션이 필요 없게).
    수락되면 `team_member`가 새로 생긴다(`team_invitation`은 그 사실을
    따로 담지 않는다 — `team_member.joined_at`로 이미 알 수 있다).
    """

    id: UUID
    team_id: UUID
    invited_user_id: UUID
    status: str
    created_at: datetime
    responded_at: datetime | None = None

    # 초대받은 **사람**(미결 `paik` 39번 후속, 2026-09-17 — 백성검, 정어진 승인).
    #
    # 🔴 **보낸 쪽 화면이 판을 되살리는 값이다.** 주장이 스쿼드 판에 앉힌 사람은
    # 초대로 남는데, id 만으로는 새로고침 뒤에 **누구인지도 무슨 카드인지도**
    # 그릴 수가 없었다. 받는 쪽(`MyTeamInvitationEntity`)에 팀 넉 칸을 실어 준
    # 것과 **같은 이유·같은 방식**이다 — 줄마다 따로 부르지 않게.
    #
    # 🔴 카드를 안 만든 사람은 슬러그가 `None` 이다 — 정상이고, 그때 화면은
    # 이름표로 남는다.
    invited_user_nickname: str | None = None
    invited_user_card_slug: str | None = None

    # 「부르는 자리」(`paik` 37번). 셋 다 `None` 이면 **자리를 안 정한 초대**다.
    #
    # 🔴 대리키와 약칭을 함께 싣는 이유는 `TeamMemberEntity` 의 카드 둘과 같다 —
    # 담는 것은 `position_id`(약칭이 종목 간 겹친다)이고 화면에 나가는 것은
    # 약칭·이름이라, 하나만 주면 나머지를 얻을 경로가 없다. `position_id` 는
    # 저장용이라 API 응답에는 안 나간다.
    position_id: UUID | None = None
    position_code: str | None = None
    position_label: str | None = None


@dataclass(frozen=True)
class MyTeamInvitationEntity:
    """내가 **받은** 초대 한 줄 (`paik` 37번).

    🔴 초대 자체가 아니라 **초대 + 그것을 판단하는 데 필요한 팀 쪽 값**이다.
    받는 사람은 그 팀 소속이 아니어서 팀 화면을 거치지 않고 알림에서 바로
    수락 여부를 정한다 — 이름도 모르는 팀의 초대는 판단할 수가 없다.

    상속이 아니라 **합성**인 이유: 상속으로 칸을 늘리면 초대가 오가는 다른
    경로(`GET /teams/{id}/invitations` 등)에서 그 칸들이 빈 채로 따라다니고,
    그러면 "안 정했다"와 "안 채웠다"를 가를 수 없다.
    """

    invitation: TeamInvitationEntity
    team_name: str
    team_region: str
    team_sport_code: str
    # 그 팀 스쿼드의 공개 슬러그 — `GET /squads/{slug}` 로 판을 그린다.
    # 스쿼드를 아직 안 만든 팀이면 `None` 이다(생성이 멱등이라 늦게 생긴다).
    squad_public_slug: str | None
