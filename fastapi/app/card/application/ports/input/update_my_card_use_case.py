"""내 카드 수정 입력 포트.

🔴 **이름이 `update_my_card` 인데 바꾸는 것은 한 줄뿐이다.** 그게 의도다 —
`public_slug` 는 이미 공유된 주소라 바꾸면 남이 가진 링크가 죽고,
`og_image_key` 는 슬러그에서 규칙으로 나온다. 명령에 그 둘을 담는 자리를
아예 두지 않는 것이 규칙을 코드로 지키는 방법이다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from app.card.application.dtos.card_dto import MyCardResult


@dataclass(frozen=True)
class UpdateMyCardCommand:
    user_id: UUID
    #: `None` 이면 **지운다** — 안 정한 상태로 돌아간다.
    tagline: str | None


class UpdateMyCardUseCase(ABC):
    @abstractmethod
    def __call__(self, command: UpdateMyCardCommand) -> MyCardResult:
        """내 카드의 한 줄을 바꾼다. 카드가 없으면 404."""
