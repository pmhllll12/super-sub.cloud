"""분석 워커 — 백엔드 큐에서 작업을 하나씩 집어 분석하고 결과를 되돌려 보고한다.

    uv run python scripts/worker.py           # 큐를 계속 폴링한다 (systemd 가 이걸 돌린다)
    uv run python scripts/worker.py --once    # 한 바퀴만 — 배포 직후 확인용
    uv run python scripts/worker.py --dry-run # 집지 않고 설정만 점검한다

미결 `ho` 17번의 나머지 절반이다. 백엔드가 `claim`·`PATCH` 를 냈고(`f7ea780`),
여기가 그 둘과 `analyze_s3.py` 를 잇는 루프다.

    POST /videos ─> analysis_job(queued)
                        │
       주기적으로 ──────┴─> claim ─> analyze_s3.py ─> PATCH(succeeded|failed)
                            └────────── 이 파일 ──────────┘

규격은 `fastapi/docs/worker-interface.md` 이고 정본은 `api-contract.md` 3-8절이다.

┌ 이 파일이 지키는 것 넷 ─────────────────────────────────────────────────┐
│ (1) `claim` 은 한 바퀴에 **한 번만** 부른다. POST 이고 부를 때마다 작업을 │
│     하나 소비하므로, 실패했다고 다시 부르면 **다른 작업**을 집는다.       │
│ (2) 204 는 오류가 아니다 — 큐가 빈 것이 정상이다. 로그를 남기지 않는다.   │
│ (3) `--rubric` 을 항상 명시한다. 기본값이 축구라 안 주면 야구를 축구로     │
│     채점하고, 그 결과가 틀렸다는 것이 값에 나타나지 않는다.               │
│ (4) `videos/` 에 쓰지 않는다. 읽기 전용 IAM 정책이 의도다.                │
└─────────────────────────────────────────────────────────────────────────┘

🔴 **워커 프로세스 자신은 autostop 의 `BUSY_PATTERN` 에 넣지 않는다.**
큐가 비어 있는 동안에도 이 프로세스는 계속 떠 있으므로, 패턴에 넣으면 인스턴스가
**영영 안 꺼진다**(상시 가동 월 $466). 대신 분석이 도는 동안에는 자식 프로세스가
`analyze_s3.py` 라 기존 패턴에 그대로 걸린다 — 지켜야 할 성질("분석 도중에 꺼지지
않는다")은 그쪽이 만족시킨다. `tests/test_worker.py` 가 그 매칭을 검사한다.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from supersub_agent.scoring import load_rubric  # noqa: E402

# `failure_reason` 컬럼의 상한이다. 넘겨 보내면 잘려서 정작 원인이 사라지므로
# 이쪽에서 먼저 자른다 — 뒤가 아니라 앞을 남긴다(무엇이 실패했는지가 앞에 있다).
FAILURE_REASON_MAX = 255

# 설정이 틀린 것(토큰 없음·401)은 재시작해도 그대로다. systemd 가 이 코드로는
# 재시작하지 않도록 유닛에 `RestartPreventExitStatus=78` 을 걸어 두었다.
# 무한 재시작하면 저널이 401 로 차서 정작 고쳐야 할 줄이 안 보인다.
EXIT_CONFIG = 78


class ConfigError(RuntimeError):
    """설정이 틀렸다 — 재시작으로 풀리지 않는다."""


class RubricUnavailable(RuntimeError):
    """이 작업을 채점할 루브릭을 정할 수 없다 — 실행하지 않고 failed 로 보고한다."""


# --- 설정 -----------------------------------------------------------------


@dataclass(frozen=True)
class Config:
    api_base: str
    token: str
    bucket: str
    reports_uri: str
    rubric_dir: Path
    poll_seconds: float
    http_timeout: float
    analyze_timeout: float
    region: str | None

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Config:
        env = os.environ if env is None else env
        # 🔴 토큰은 저장소에 없다. 정어진 님이 따로 전달하는 값을
        #    /etc/supersub/worker.env 에 넣는다. 백엔드가 비어 있으면 모든
        #    요청이 401 이므로, 여기서도 비어 있으면 아예 시작하지 않는다.
        token = (env.get("SUPERSUB_WORKER_TOKEN") or "").strip()
        if not token:
            raise ConfigError(
                "SUPERSUB_WORKER_TOKEN 이 비어 있다. "
                "deploy/worker.env.example 을 /etc/supersub/worker.env 로 복사해 "
                "값을 채울 것 (값은 저장소에 없다 — 백엔드 담당자에게 받는다)."
            )
        # 🔴 HTTP 헤더는 latin-1 로 인코딩된다. 한글이나 이모지가 섞이면
        #    urllib 이 UnicodeEncodeError 를 내는데, 그것이 ValueError 라서
        #    아래 루프가 **일시적 오류로 착각하고 영원히 재시도한다.** 설정
        #    문제는 설정 문제로 말해야 한다.
        if not token.isascii():
            raise ConfigError(
                "SUPERSUB_WORKER_TOKEN 에 ASCII 가 아닌 문자가 있다. "
                "HTTP 헤더에 실을 수 없는 값이다 — 따옴표나 주석이 섞이지 "
                "않았는지 /etc/supersub/worker.env 를 확인할 것."
            )
        # 🔴 기본값을 두지 않는다. 저장소가 공개라 호스트명을 코드에 박으면
        #    그대로 공개된다. 자리표시자 문자열을 기본값으로 두는 것은 더
        #    나쁘다 — 배포에서 잘못된 URL 로 조용히 붙는다. 없으면 시작하지
        #    않게 해서 **설정 누락이 설정 누락으로 보이게** 한다.
        api_base = (env.get("SUPERSUB_API_BASE") or "").strip()
        if not api_base:
            raise ConfigError(
                "SUPERSUB_API_BASE 가 비어 있다. "
                "deploy/worker.env.example 을 /etc/supersub/worker.env 로 복사해 "
                "백엔드 주소를 채울 것 (값은 저장소에 없다 — 배포 담당자에게 받는다)."
            )
        bucket = env.get("SUPERSUB_S3_BUCKET", "supersub-ai")
        return cls(
            api_base=api_base.rstrip("/"),
            token=token,
            bucket=bucket,
            reports_uri=env.get("SUPERSUB_REPORTS_URI", f"s3://{bucket}/reports"),
            rubric_dir=Path(env.get("SUPERSUB_RUBRIC_DIR", str(ROOT / "rubrics"))),
            # 큐는 대부분 비어 있다. 촘촘히 돌아도 얻는 것이 없고 저널만 는다.
            poll_seconds=float(env.get("SUPERSUB_POLL_SECONDS", "45")),
            http_timeout=float(env.get("SUPERSUB_HTTP_TIMEOUT", "30")),
            # 4K 한 편이 포즈 추출 + 판정까지 수 분이다. 넉넉히 두되 무한은
            # 아니게 — 모델 적재가 멈추면 워커가 영영 그 작업을 붙들고 있다.
            analyze_timeout=float(env.get("SUPERSUB_ANALYZE_TIMEOUT", "3600")),
            region=env.get("SUPERSUB_S3_REGION") or None,
        )


def log(msg: str) -> None:
    """journald 가 시각을 붙이므로 여기서는 안 붙인다."""
    print(f"[worker] {msg}", flush=True)


# --- 백엔드 호출 (urllib — 의존성을 늘리지 않는다, judge.py 와 같은 이유) ----


def _request(
    cfg: Config, method: str, path: str, payload: dict | None = None
) -> tuple[int, bytes]:
    """(상태코드, 본문). 4xx·5xx 도 예외가 아니라 값으로 돌려준다 —
    204·401·409 가 전부 뜻이 다른 정상 흐름이라 호출부에서 갈라야 한다."""
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"{cfg.api_base}{path}", data=data, method=method)
    req.add_header("X-Worker-Token", cfg.token)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=cfg.http_timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def claim(cfg: Config) -> dict | None:
    """작업 하나를 집는다. 큐가 비었으면 None.

    🔴 **여기서 재시도하지 않는다.** 조회처럼 보여도 POST 이고, 한 번 부를
    때마다 작업 하나가 `running` 으로 넘어간다. 응답을 못 받아 다시 부르면
    **같은 것이 아니라 다음 것**을 집어, 앞의 작업은 아무도 안 든 채 `running`
    으로 남는다. 실패는 그냥 이번 바퀴를 넘기고 다음 폴링에 맡긴다.
    """
    status, body = _request(cfg, "POST", "/internal/analysis-jobs/claim")
    if status == 204:
        return None  # 큐가 빈 것은 정상이다 — 로그를 남기지 않는다
    if status == 200:
        return json.loads(body)
    if status == 401:
        raise ConfigError(
            "claim 이 401 이다. SUPERSUB_WORKER_TOKEN 이 서버의 WORKER_TOKEN 과 "
            "다르거나, 서버 쪽 값이 비어 있다 (한쪽만 넣으면 계속 401 이다)."
        )
    raise RuntimeError(f"claim 이 {status} 를 냈다: {body[:200]!r}")


def report_key_from(result_path: Path, bucket: str) -> str | None:
    """분석이 남긴 자리 파일에서 **버킷 상대 키**를 꺼낸다 (미결 `paik` 11번).

    🔴 **자리를 여기서 계산하지 않는다.** 규칙(`analyze_s3.report_targets`)이
    두 곳에 생기면 조용히 갈린다 — 아는 쪽이 파일로 말해 주고 여기는 읽기만
    한다. stdout 을 긁지 않는 것도 같은 이유다(로그 문구가 바뀌면 깨진다).

    없거나·비었거나·모양이 다르면 **None 이다.** 자리를 못 실어도 분석은
    성공한 것이라 보고 자체를 막지 않는다 — 화면이 리포트를 못 찾을 뿐이다.
    """
    try:
        raw = json.loads(result_path.read_text(encoding="utf-8"))
        reports = raw["reports"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if len(reports) != 1:
        # 작업 하나는 영상 하나다. 둘 이상이면 어느 것이 이번 결과인지
        # 정해지지 않으므로 **아무것도 안 싣는다** — 틀린 자리보다 낫다.
        log(f"리포트 자리가 {len(reports)}건이라 싣지 않는다")
        return None
    uri = str(reports[0].get("report_uri", ""))
    prefix = f"s3://{bucket}/"
    if not uri.startswith(prefix):
        # 리포트를 다른 버킷에 두면 버킷 상대 키로는 가리킬 수 없다.
        log(f"리포트가 버킷 {bucket} 밖이라 키로 못 싣는다: {uri}")
        return None
    return uri[len(prefix):]


def report(cfg: Config, job_id: str, status: str, reason: str | None = None,
           report_key: str | None = None) -> bool:
    """결과를 보고한다. 보고가 안 되면 작업이 `running` 인 채로 남는다.

    claim 과 달리 **재시도한다.** 같은 것을 두 번 보고하면 409 로 돌아올 뿐
    새 작업을 소비하지 않아서다 — 되돌릴 수 없는 쪽은 claim 뿐이다.

    `finished_at` 을 보내지 않는다. 서버가 찍는다 — 워커의 시계가 어긋나면
    소요 시간이 음수가 된다.
    """
    payload: dict[str, str] = {"status": status}
    if reason:
        payload["failure_reason"] = reason[:FAILURE_REASON_MAX]
    # 🔴 성공한 작업에만 싣는다 — 실패했으면 가리킬 리포트가 없다.
    #    받는 칸은 정어진 님의 `FinishJobSchema` 다 (미결 `paik` 11번).
    if report_key and status == "succeeded":
        payload["report_key"] = report_key

    for attempt in range(1, 4):
        try:
            code, body = _request(
                cfg, "PATCH", f"/internal/analysis-jobs/{job_id}", payload
            )
        except (urllib.error.URLError, OSError) as exc:
            log(f"보고 실패({attempt}/3) — {type(exc).__name__}: {exc}")
            code, body = 0, b""
        if code == 204:
            return True
        if code in (404, 409, 422):
            # 404 없는 작업 · 409 이미 끝났거나 안 집었음 · 422 상태값이 틀림.
            # 셋 다 재시도가 무의미하다 — 다시 불러도 같은 답이 온다.
            log(f"보고가 {code} 로 거부됐다 (재시도 무의미): {body[:200]!r}")
            return False
        if attempt < 3:
            time.sleep(2 * attempt)
    log(f"보고를 3회 시도했으나 실패했다 — job {job_id} 이 running 으로 남는다")
    return False


# --- 루브릭 고르기 --------------------------------------------------------


def pick_rubric(rubric_dir: Path, sport_code: str) -> Path:
    """그 종목의 `active` 루브릭이 **정확히 하나면** 그것을 쓴다.

    claim 응답에 동작(motion)이 없다. 담을 자리가 아직 없어서인데(미결 `jin`
    17번), 지금은 종목당 active 가 하나씩이라 종목만으로 정해진다.

    🔴 0 개거나 2 개 이상이면 **아무거나 고르지 않고 멈춘다.** draft 를 승격시켜
    둘이 되는 순간 조용히 엉뚱한 루브릭으로 채점되는 것보다, 그 작업이 이유를
    달고 failed 로 남는 편이 낫다. `jin` 17번이 풀려 motion 이 실리면 이 규칙은
    필요 없어진다.
    """
    actives = [
        path
        for path in sorted(Path(rubric_dir).glob("*.yaml"))
        if (r := load_rubric(path)).sport == sport_code and r.is_active
    ]
    if len(actives) == 1:
        return actives[0]
    names = ", ".join(p.stem for p in actives) or "없음"
    raise RubricUnavailable(
        f"채점할 루브릭을 정할 수 없다 (sport={sport_code}, active {len(actives)}개: "
        f"{names}). 종목당 active 가 정확히 하나여야 한다."
    )


# --- 분석 실행 ------------------------------------------------------------


class Stopper:
    """SIGTERM/SIGINT 를 받으면 이번 작업을 정리하고 나간다.

    🔴 분석 중에 받으면 **자식을 끊고 `failed` 로 보고한 뒤** 나간다. 그냥
    죽으면 그 작업이 `running` 인 채로 남아 아무도 다시 집지 못한다 — 회수
    규칙이 아직 없어서(worker-interface.md 「아직 없는 것」) 사실상 영구다.
    `failed` 로 남기면 적어도 무슨 일이 있었는지가 값으로 남는다.
    """

    def __init__(self) -> None:
        self.stop = False
        self.child: subprocess.Popen | None = None

    def install(self) -> None:
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._handle)

    def _handle(self, signum, frame) -> None:  # noqa: ANN001, ARG002
        if self.stop:  # 두 번째 신호는 기다리지 않는다
            raise SystemExit(1)
        self.stop = True
        log(f"신호 {signum} — 이번 작업을 정리하고 멈춘다")
        if self.child is not None and self.child.poll() is None:
            self.child.terminate()


def analyze_command(cfg: Config, job: dict, rubric: Path,
                    result_json: Path | None = None) -> list[str]:
    """자식 프로세스의 명령줄.

    🔴 **`analyze_s3.py` 를 별도 프로세스로 부른다.** import 해서 안에서 돌리면
    autostop 의 `BUSY_PATTERN` 에 안 걸려 **분석 도중에 인스턴스가 꺼진다.**
    종료 코드로 성공·실패를 가르는 것도 프로세스 경계 덕이다.
    """
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "analyze_s3.py"),
        f"s3://{cfg.bucket}/{job['storage_key']}",
        "--rubric",
        str(rubric),  # 🔴 항상 명시한다 — 기본값은 축구다
        "--out",
        cfg.reports_uri,
    ]
    # 🔴 `video_id` 를 넘겨야 리포트가 **계약 자리**에 간다
    # (`reports/<user_id>/<video_id>/report.json`, 미결 `jin` 24번). 안 넘기면
    # 옛 자리(업로드 폴더 + 타임스탬프)로 가고, 「저장」이 원본을 옮겨 놓을
    # 폴더와 리포트가 **따로 놀게 된다.**
    # 없을 수도 있다고 보고 확인한다 — 옛 백엔드는 이 필드를 안 준다.
    if job.get("video_id"):
        cmd += ["--video-id", str(job["video_id"])]
    # side 는 없을 수 있다(null). 그러면 주지 않는다 — analyze_s3.py 의 기본값
    # "auto" 가 스스로 판별한다. None 을 문자열로 넘기면 argparse 가 거부한다.
    if job.get("side") in ("left", "right"):
        cmd += ["--side", job["side"]]
    # 「집중해서 볼 항목」 (미결 `paik` 8번). 백엔드에 이 칸이 아직 없어서
    # 지금은 항상 비어 있다 — 칸이 열리는 날 그대로 흘러가라고 미리 읽는다.
    # 🔴 빈 목록은 실패가 아니라 「전체적으로」다. 없을 때 아무것도 안 붙인다.
    focus = job.get("focus") or []
    if isinstance(focus, str):
        focus = [focus]
    focus = [str(f).strip() for f in focus if str(f).strip()]
    if focus:
        cmd += ["--focus", ",".join(focus)]
    if cfg.region:
        cmd += ["--region", cfg.region]
    # 리포트가 어디 놓였는지를 파일로 받는다 (미결 `paik` 11번).
    if result_json is not None:
        cmd += ["--result-json", str(result_json)]
    return cmd


@dataclass(frozen=True)
class Outcome:
    """분석 한 번의 결과. `note` 가 있으면 종료 코드보다 그쪽이 진짜 이유다 —
    시간 초과나 종료 신호로 **우리가** 죽인 경우라 코드만 보면 오해한다."""

    code: int
    last_line: str
    note: str = ""


def run_analysis(cmd: list[str], timeout: float, stopper: Stopper) -> Outcome:
    """출력은 흘려보내면서 마지막 줄만 들고 있는다.

    통째로 모았다가 한 번에 내면 몇 분짜리 분석이 저널에 아무것도 안 남긴 채
    도는 것처럼 보인다. 반대로 전부 기억하면 failure_reason 에 넣을 수 없다 —
    255자라 스택트레이스를 통째로 넣으면 잘려서 정작 원인이 사라진다.
    """
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    proc = subprocess.Popen(
        cmd, cwd=ROOT, env=env, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    timed_out = threading.Event()

    def kill_it() -> None:
        timed_out.set()
        proc.kill()

    watchdog = threading.Timer(timeout, kill_it)
    watchdog.start()
    # 종료 신호를 받으면 이 자식을 끊는다. 안 끊으면 systemd 가 TimeoutStopSec
    # 뒤에 우리를 SIGKILL 하고, 그러면 보고를 못 해 작업이 running 으로 남는다.
    stopper.child = proc
    last = ""
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip()
            print(line, flush=True)
            if line.strip():
                last = line.strip()
        proc.wait()
    finally:
        watchdog.cancel()
        stopper.child = None

    if timed_out.is_set():
        return Outcome(proc.returncode, last, f"{timeout:.0f}초를 넘겨 중단했다")
    if stopper.stop and proc.returncode != 0:
        return Outcome(
            proc.returncode, last, "워커가 종료 신호를 받아 중단했다 — 다시 걸어야 한다"
        )
    return Outcome(proc.returncode, last)


def failure_reason(outcome: Outcome) -> str:
    """종료 코드를 사람이 읽을 사유로. 길이는 호출부(report)에서 자른다.

    | 0 | 정상                                          |
    | 2 | 품질 게이트 미달 — 사람이 다시 찍어야 풀린다  |
    | 그 외 | 인자 오류·다운로드 실패·모델 적재 실패 등  |
    """
    if outcome.note:
        # 우리가 죽인 경우다. 종료 코드(-9 따위)는 뜻이 없고 note 가 이유다.
        tail = f" (마지막 출력: {outcome.last_line})" if outcome.last_line else ""
        return f"{outcome.note}{tail}"
    if outcome.code == 2:
        # analyze_s3.py 가 "분석 중단: …" 을 마지막에 찍는다. 이미 사람이 읽을
        # 문장이라 그대로 쓴다.
        return (
            f"품질 게이트 미달: {outcome.last_line}"
            if outcome.last_line
            else "품질 게이트 미달"
        )
    if outcome.last_line:
        return f"종료 코드 {outcome.code}: {outcome.last_line}"
    return f"종료 코드 {outcome.code}"


# --- 한 건 처리 -----------------------------------------------------------


def process(cfg: Config, job: dict, stopper: Stopper) -> None:
    """집은 작업 하나를 끝까지 처리한다 — **반드시 보고까지 간다.**

    여기서 예외가 새면 그 작업은 `running` 인 채로 영영 남는다(회수 규칙은 아직
    없다 — worker-interface.md 「아직 없는 것」). 그래서 넓게 잡는다.
    """
    job_id = job["job_id"]
    log(f"작업 {job_id} — {job.get('sport_code')} · {job.get('storage_key')}")

    try:
        rubric = pick_rubric(cfg.rubric_dir, job.get("sport_code", ""))
    except RubricUnavailable as exc:
        log(f"루브릭 미정 — 실행하지 않는다: {exc}")
        report(cfg, job_id, "failed", str(exc))
        return
    except Exception as exc:  # noqa: BLE001 — 루브릭 파일이 깨진 경우
        log(f"루브릭을 읽지 못했다: {type(exc).__name__}: {exc}")
        report(cfg, job_id, "failed", f"루브릭 적재 실패: {exc}")
        return

    log(f"루브릭 {rubric.name}")
    started = time.time()
    # 자식이 리포트 자리를 여기 적는다. 작업마다 새로 만들어 **앞 작업의 값을
    # 물려받지 않게** 한다 — 물려받으면 실패한 작업이 남의 리포트를 가리킨다.
    with tempfile.TemporaryDirectory(prefix="supersub-job-") as tmp:
        result_json = Path(tmp) / "result.json"
        try:
            outcome = run_analysis(
                analyze_command(cfg, job, rubric, result_json),
                cfg.analyze_timeout, stopper,
            )
        except Exception as exc:  # noqa: BLE001 — 실행 자체가 안 된 경우
            log(f"분석을 실행하지 못했다: {type(exc).__name__}: {exc}")
            report(cfg, job_id, "failed",
                   f"분석 실행 실패: {type(exc).__name__}: {exc}")
            return

        elapsed = time.time() - started
        if outcome.code == 0 and not outcome.note:
            key = report_key_from(result_json, cfg.bucket)
            if key is None:
                # 🔴 성공했는데 자리를 못 실은 것은 **드러낸다.** 화면은
                #    리포트를 못 찾고, 저널에 아무 말도 없으면 원인을 못 좁힌다.
                log(f"작업 {job_id} 성공했지만 리포트 자리를 못 실었다")
            log(f"작업 {job_id} 성공 ({elapsed:.0f}초)"
                + (f" — 리포트 {key}" if key else ""))
            report(cfg, job_id, "succeeded", report_key=key)
        else:
            reason = failure_reason(outcome)
            log(f"작업 {job_id} 실패 ({elapsed:.0f}초) — {reason}")
            report(cfg, job_id, "failed", reason)


# --- 루프 -----------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description="분석 큐 폴링 워커")
    ap.add_argument("--once", action="store_true",
                    help="한 바퀴만 돈다 (큐가 비어 있으면 아무것도 안 하고 끝난다)")
    ap.add_argument("--dry-run", action="store_true",
                    help="claim 하지 않고 설정만 점검한다. 🔴 claim 은 확인이 "
                         "아니라 소비라서 점검에 쓸 수 없다")
    args = ap.parse_args()

    try:
        cfg = Config.from_env()
    except ConfigError as exc:
        log(f"설정 오류: {exc}")
        return EXIT_CONFIG

    log(f"API {cfg.api_base} · 버킷 {cfg.bucket} · 리포트 {cfg.reports_uri}")
    log(f"루브릭 {cfg.rubric_dir} · 폴링 {cfg.poll_seconds:.0f}초")
    if args.dry_run:
        for sport in ("baseball", "basketball", "football"):
            try:
                log(f"  {sport} → {pick_rubric(cfg.rubric_dir, sport).name}")
            except RubricUnavailable as exc:
                log(f"  {sport} → 🔴 {exc}")
        return 0

    stopper = Stopper()
    stopper.install()
    consecutive_errors = 0

    while not stopper.stop:
        try:
            job = claim(cfg)
            consecutive_errors = 0
        except ConfigError as exc:
            log(f"설정 오류: {exc}")
            return EXIT_CONFIG
        except (urllib.error.URLError, OSError, ValueError, RuntimeError) as exc:
            # 🔴 여기서 곧바로 claim 을 다시 부르지 않는다. 위 claim() 주석 참고.
            consecutive_errors += 1
            log(f"claim 실패({consecutive_errors}) — {type(exc).__name__}: {exc}")
            job = None

        if job is not None:
            process(cfg, job, stopper)
            if args.once or stopper.stop:
                break
            continue  # 큐에 더 있을 수 있다 — 쉬지 않고 다음 것을 집는다

        if args.once:
            log("큐가 비어 있다")
            break
        # 연달아 실패하면 뜸하게 — 백엔드가 내려가 있을 때 저널을 채우지 않는다.
        wait = cfg.poll_seconds * min(consecutive_errors + 1, 4)
        for _ in range(int(wait)):
            if stopper.stop:
                break
            time.sleep(1)

    log("멈춘다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
