"""`match` 와 필요 포지션. 부록 D 도메인 ④."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class PositionNeedEntity:
    """경기 1건의 포지션 1종 필요분.

    `code`·`label` 은 `position` 에서 읽어 온 표시용이다 — 저장되는 것은
    `position_id` 뿐이다(약칭은 종목 안에서만 유일해서 코드로는 못 가리킨다).
    """

    position_id: UUID
    code: str
    label: str
    head_count: int


@dataclass(frozen=True)
class MatchEntity:
    """등록된 경기 1건.

    🔴 **종목이 없다.** `match -> team -> sport_code` 로 결정된다(부록 D.4).
    여기에 종목을 들이면 팀 종목과 어긋날 수 있는 두 번째 진실이 생긴다.

    `opponent_team_id`가 차 있으면 **팀 대 팀으로 확정된 경기**다(`paik` 17번,
    `team_match_request` 수락으로만 생긴다). 이런 경기는 양쪽 스쿼드가 이미
    차 있다는 전제라 `needs`(모집)가 비어 있다.
    """

    id: UUID
    team_id: UUID
    played_at: datetime
    place: str
    needs: list[PositionNeedEntity] = field(default_factory=list)
    opponent_team_id: UUID | None = None


@dataclass(frozen=True)
class TeamMatchRequestEntity:
    """팀 대 팀 경기 신청 1건. `paik` 17번.

    개인이 경기에 지원하는 `ApplicationEntity`와는 다르다 — 신청 주체도 받는
    사람도 팀(정확히는 그 팀 주장)이다. 상태를 `analysis_job.status`처럼
    자유 문자열로 둔다(`TeamMatchRequestStatus` 참고) — DB 제약을 안 거는 것도
    같은 이유(단계가 늘 때 마이그레이션 없이).
    """

    id: UUID
    requester_team_id: UUID
    target_team_id: UUID
    proposed_played_at: datetime
    proposed_place: str
    status: str
    created_at: datetime
    # 두 팀의 **표시용 값**(`paik` 31번). 알림 판이 「망원 유나이티드가 경기를
    # 걸었습니다」를 쓰려면 id 로는 안 되고, 목록에서 줄마다 `GET /teams/{id}`
    # 를 부르면 N+1 이 된다 — `MatchListingEntity` 가 주최 팀 값을 얹는 것과
    # **같은 자리**다("경기 id 만 주면 화면이 팀을 한 건씩 다시 물어야 한다").
    #
    # 🔴 저장되는 모양이 아니라 **조회 결과**다. 값은 매번 `team` 에서 읽으므로
    # 팀 이름이 바뀌어도 어긋날 수가 없다.
    responded_at: datetime | None = None
    match_id: UUID | None = None
    # 🔴 **저장소가 채운다.** 인터랙터가 새 신청을 만들 때는 비어 있고
    # (`team` 을 읽을 수 없는 자리다), 저장소가 돌려주는 엔티티부터 차 있다.
    # 그래서 기본값이 빈 문자열이다 — "없는 팀"이 아니라 "아직 안 읽었다"다.
    requester_team_name: str = ""
    requester_team_region: str = ""
    target_team_name: str = ""
    target_team_region: str = ""


@dataclass(frozen=True)
class MatchListingEntity:
    """탐색 목록의 한 줄. 경기 하나에 **주최 팀의 표시용 값**을 얹은 것이다.

    용병이 경기를 고르는 기준이 종목·지역·팀이라, 목록에는 그 셋이 함께 있어야
    한다. 경기 id 만 주면 화면이 팀을 한 건씩 다시 물어야 한다.

    🔴 **`MatchEntity` 에 종목을 넣지 않는 원칙은 그대로다.** 이것은 저장되는
    모양이 아니라 **조회 결과**다 — 값은 매번 `team` 에서 읽어 오므로 팀 종목과
    어긋날 수가 없다. 포지션의 `code`·`label` 을 표시용으로 들고 다니는 것과
    같은 자리다.
    """

    match: MatchEntity
    team_name: str
    region: str
    sport_code: str
