"""분석 작업의 상태 규칙. **HTTP도 DB도 없다.**

`analysis_job.status` 의 값 목록과 옮겨 갈 수 있는 방향을 여기 한 곳에 둔다.
ORM 주석이 값 목록을 적어 두었지만 **DB 제약으로 걸지 않기로 했으므로**
(단계가 늘어날 때 마이그레이션 없이 넣기 위해서다) 지키는 자리가 코드에 있어야
한다.

```
queued ──claim──> running ──finish──> succeeded
                          └─finish──> failed
```

🔴 **`queued` 에서 바로 끝내지 않는다.** 워커가 집지 않은 작업이 성공·실패로
가면 "누가 돌렸나"가 사라지고 `started_at` 이 빈 채로 `finished_at` 만 찬다 —
PER-001 이 보려는 것이 그 두 시각의 차이다.
"""

from __future__ import annotations

QUEUED = "queued"
RUNNING = "running"
SUCCEEDED = "succeeded"
FAILED = "failed"

#: 워커가 끝났다고 보고할 수 있는 값. `queued`·`running` 은 여기 없다 —
#: 그것은 보고가 아니라 진행 상태다.
TERMINAL = frozenset({SUCCEEDED, FAILED})


def is_terminal(status: str) -> bool:
    return status in TERMINAL


def can_finish(current: str) -> bool:
    """지금 상태에서 끝낼 수 있는가. **집은 것만 끝낼 수 있다.**

    이미 끝난 작업을 다시 끝내는 것도 막는다 — 워커가 재시도로 두 번 보고하면
    `finished_at` 이 뒤로 밀려 소요 시간이 늘어난 것처럼 보인다.
    """
    return current == RUNNING
