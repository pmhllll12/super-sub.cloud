"""팀 HTTP 모델. 계약 문서 3-3절."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.shared import Rfc3339


class CreateTeamSchema(BaseModel):
    """`sport_code` 값이 실제로 있는지는 서버가 확인한다(422 `UNKNOWN_SPORT`).

    여기서 고정 목록으로 막지 않는 이유: 종목이 늘 때 **앱 배포 없이 행만 넣으면**
    되게 하기 위해서다.
    """

    name: str = Field(min_length=1, max_length=60)
    region: str = Field(min_length=1, max_length=60)
    sport_code: str = Field(min_length=1, max_length=20)


class UpdateTeamSchema(BaseModel):
    """팀 이름·지역 수정. **보낸 필드만** 바뀐다.

    🔴 **`sport_code` 는 여기 없다.** 포지션·스쿼드·경기가 전부 그 값에
    매달려 있어서, 바꾸면 이미 앉힌 포지션이 다른 종목 것이 된다. 받을
    자리를 아예 안 두는 것이 그 규칙을 지키는 방법이다(카드가
    `public_slug` 를 안 받는 것과 같은 판단).

    🔴 **`null` 로는 못 지운다.** 둘 다 DB 에서 NOT NULL 이고 만들 때
    필수였던 값이라 "안 정한 상태"가 없다 — `null` 을 보내면 422 다
    (`PATCH /me/card` 의 `tagline` 과 다른 점이다. 그쪽은 지울 수 있다).
    안 바꾸려면 **필드를 아예 빼면** 된다.
    """

    name: str | None = Field(default=None, min_length=1, max_length=60)
    region: str | None = Field(default=None, min_length=1, max_length=60)

    @field_validator("name", "region")
    @classmethod
    def _null_is_not_erase(cls, value: str | None) -> str:
        # 기본값은 검증을 안 타므로(pydantic v2) **명시적으로 보낸 `null`** 만
        # 여기 온다 — 「안 보냄」과 구별된다.
        if value is None:
            raise ValueError("null 로 지울 수 없습니다 — 값을 보내거나 필드를 빼십시오")
        return value


class AddMemberSchema(BaseModel):
    """`user_id` 를 비우면 **본인이 가입**하는 것이다. 채우면 주장이 남을 넣는다."""

    user_id: UUID | None = None


class TeamMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    nickname: str
    role: str
    joined_at: Rfc3339
    # 그 사람의 선수 카드. **카드를 안 만든 구성원은 둘 다 `null`** 이고, 그래도
    # 목록에는 남는다 — 팀에는 있는 사람이다.
    #
    # 스쿼드 등재(`POST /teams/{id}/squad/members`)는 `player_card_id` 를 받고,
    # 카드로 가는 링크는 `card_public_slug` 를 쓴다. 화면이 둘 다 필요해서
    # 함께 싣는다(미결 `paik` 2번).
    player_card_id: UUID | None = None
    card_public_slug: str | None = None


class TeamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    region: str
    sport_code: str
    members: list[TeamMemberResponse]


class CreateTeamInvitationSchema(BaseModel):
    """주장이 개인을 초대한다(`min` 20번). 용병 검색 결과의 `user_id`를 그대로 싣는다."""

    invited_user_id: UUID


class TeamInvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    team_id: UUID
    invited_user_id: UUID
    status: str
    created_at: Rfc3339
    responded_at: Rfc3339 | None
