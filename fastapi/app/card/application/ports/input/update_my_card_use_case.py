"""내 카드 수정 입력 포트.

🔴 **이름이 `update_my_card` 인데 바꾸는 것은 한 줄뿐이다.** 그게 의도다 —
`public_slug` 는 이미 공유된 주소라 바꾸면 남이 가진 링크가 죽고,
`og_image_key` 는 슬러그에서 규칙으로 나온다. 명령에 그 둘을 담는 자리를
아예 두지 않는 것이 규칙을 코드로 지키는 방법이다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.card.application.dtos.card_dto import UNSET, MyCardResult


@dataclass(frozen=True)
class UpdateMyCardCommand:
    user_id: UUID
    #: `UNSET` 이면 안 건드린다. `None` 이면 **지운다** — 안 정한 상태로
    #: 돌아간다. 값이면 그 값으로 바꾼다(`www` 가 아직 안 보내던 시절엔
    #: 요청마다 늘 채워져 있었지만, `style` 과 한 PATCH 를 나눠 쓰게 되면서
    #: "이번엔 안 보냈다"가 생겼다 — `UpdateVideoCommand` 와 같은 판단).
    tagline: str | None | Any = UNSET
    #: 카드 꾸미기 전체. `UNSET` 이면 안 건드리고, `None` 이면 꾸미기 전으로
    #: 되돌린다. 부분 병합은 하지 않는다(`CardPort.update_style` 참고).
    style: dict | None | Any = UNSET


class UpdateMyCardUseCase(ABC):
    @abstractmethod
    def __call__(self, command: UpdateMyCardCommand) -> MyCardResult:
        """내 카드의 한 줄·꾸미기를 바꾼다. 카드가 없으면 404."""
