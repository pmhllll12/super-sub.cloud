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


# --- 회수 -------------------------------------------------------------------
# 워커가 **보고 없이 죽으면** 작업이 `running` 인 채 영영 남는다. 스스로 실패를
# 보고하고 죽는 경우(예외를 잡아 `failed` 로 PATCH)는 여기 해당하지 않는다 —
# 회수가 잡는 것은 **크래시·강제 종료·인스턴스 정지**다.
#
# 🔴 이 자리는 GPU 인스턴스의 자동 종료(유휴 30분/최대 12시간) 때문에 실제로
#    일어난다. 분석 도중에 인스턴스가 멈추면 그 작업이 그대로 남는다.

#: 회수했다는 것을 `failure_reason` 에 남길 때 쓰는 표시.
#: 🔴 **컬럼을 늘리지 않고 재시도 횟수를 한 번만 세기 위한 장치다.**
#: `analysis_job` 에 시도 횟수 컬럼이 없고(부록 D), 늘리는 것은 ERD 를 고치는
#: 결정이라 혼자 정하지 않는다. 대신 "회수된 적 있는가"를 이 표시의 유무로 본다.
RECLAIM_MARK = "회수됨"

RECLAIM_FIRST = f"{RECLAIM_MARK}: 워커가 보고 없이 멈췄습니다. 다시 큐에 넣었습니다."
RECLAIM_FINAL = (
    f"{RECLAIM_MARK} 뒤 또 멈췄습니다. 같은 클립에서 워커가 두 번 죽어 중단합니다."
)


def reclaim_target(previously_reclaimed: bool) -> str:
    """멈춘 작업을 어디로 보낼 것인가.

    **한 번은 다시 큐에 넣고, 두 번째는 실패로 끝낸다.**

    되돌리기만 하면 워커를 죽이는 클립(4K 에서 host RAM 이 터지는 것 —
    미결 `ho` 9번이 실측한 자리다)이 **큐를 영원히 돌게 된다.** 반대로 한 번도
    안 되돌리면 인스턴스가 정지하며 멈춘 작업이 전부 버려진다. 그 사이를 잡는다.
    """
    return FAILED if previously_reclaimed else QUEUED
