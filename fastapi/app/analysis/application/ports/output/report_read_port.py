"""출력 포트 — 리포트 조회. 미결 `jin` 27번.

`ReportView` 를 DB 에서 조립한다. 포트를 두는 이유는 계약 테스트가 실제 DB 없이
돌게 하기 위해서다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.analysis.application.dtos.report_view_dto import ReportView


class ReportReadPort(ABC):
    @abstractmethod
    def find_for_video(self, video_id: UUID, user_id: UUID) -> ReportView | None:
        """자기 영상의 적재된 리포트. 영상이 없거나 남의 것이면, **또는** 아직
        적재가 안 됐으면 `None` — 둘의 구별은 부르는 쪽이
        (`video` 존재 여부로) 한다.
        """
