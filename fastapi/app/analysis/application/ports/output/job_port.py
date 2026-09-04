"""분석 작업 출력 포트.

`VideoPort` 와 나눈 이유는 **부르는 쪽이 다르기 때문**이다. 저쪽은 사람이 올린
클립을 다루고, 여기는 워커(기계)가 큐를 소비한다 — 인증도 다르고 수명도 다르다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.analysis.domain.entities.job_entity import ClaimedJobEntity


class JobPort(ABC):
    @abstractmethod
    def claim_next(self) -> ClaimedJobEntity | None:
        """가장 오래된 `queued` 하나를 `running` 으로 바꾸고 돌려준다. 없으면 None.

        🔴 **읽기와 쓰기를 나누지 않는다.** `SELECT` 로 고른 뒤 `UPDATE` 하면
        워커 둘이 같은 작업을 집는다 — 사이에 다른 쪽이 끼어들 틈이 있다.
        한 문장으로 집고(`... WHERE status='queued' ... RETURNING`), 동시에 들어온
        요청은 **잠긴 행을 건너뛴다**(`SKIP LOCKED`). 건너뛰지 않으면 두 번째
        워커가 첫 번째의 트랜잭션이 끝날 때까지 멈춰 서 있는다.

        **오래된 것부터** 준다. 늦게 올린 사람이 먼저 처리되면 대기 시간이
        예측되지 않는다.
        """

    @abstractmethod
    def reclaim_stale(self, timeout_minutes: int) -> tuple[int, int]:
        """오래 `running` 인 작업을 회수한다. `(다시 큐에 넣은 수, 실패로 끝낸 수)`.

        워커가 **보고 없이 죽으면** 작업이 그대로 남는다. 스스로 `failed` 를
        보고하고 끝나는 경우는 해당하지 않는다 — 여기가 잡는 것은 크래시·강제
        종료·**인스턴스 정지**다(GPU 는 유휴 30분에 자동 종료된다).

        🔴 **한 번은 큐로, 두 번째는 실패로** 보낸다. 되돌리기만 하면 워커를
        죽이는 클립이 큐를 영원히 돌게 된다(`job_rules.reclaim_target`).
        """

    @abstractmethod
    def finish(
        self, job_id: UUID, status: str, failure_reason: str | None
    ) -> str | None:
        """`running` 인 작업을 끝낸다.

        돌려주는 것은 **바꾸지 못했을 때의 현재 상태**다. 성공하면 None.
        없는 작업이면 `"missing"` — 호출한 쪽이 404 와 409 를 가르는 데 쓴다.

        `finished_at` 은 여기서 찍는다. 워커가 보낸 시각을 믿으면 시계가 어긋난
        장비에서 소요 시간이 음수가 된다.
        """
