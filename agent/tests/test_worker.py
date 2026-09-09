"""분석 워커 — 큐 폴링 루프 (scripts/worker.py).

네트워크도 GPU도 S3도 쓰지 않는다. 백엔드는 `_request`를 가로채 흉내내고,
분석은 부르지 않는다 — 실제로 부르면 이 테스트가 EC2에서만 도는 테스트가 된다.

**여기 검사들이 막고 있는 것은 전부 "조용히 틀리는" 종류다.** 워커는 사람이
안 보는 동안 도는 것이라, 틀려도 화면에 아무것도 안 나타난다.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def _load_script(name: str):
    """scripts/ 의 스크립트를 모듈로 읽는다 (패키지가 아니라 실행 파일이다)."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def worker():
    return _load_script("worker")


@pytest.fixture
def cfg(worker, tmp_path):
    return worker.Config.from_env(
        {
            "SUPERSUB_WORKER_TOKEN": "wk_test_0000",
            "SUPERSUB_API_BASE": "https://example.invalid/api/v1",
            "SUPERSUB_POLL_SECONDS": "0",
        }
    )


def _job(**over) -> dict:
    job = {
        "job_id": "9a2e",
        "video_id": "1b3c",
        "storage_key": "videos/user-1/clip.mp4",
        "sport_code": "baseball",
        "side": "right",
        "duration_ms": 4200,
    }
    job.update(over)
    return job


# -- 설정 ------------------------------------------------------------------


def test_a_missing_token_stops_before_claiming(worker):
    """🔴 토큰이 비면 시작하지 않는다.

    백엔드는 값이 비어 있으면 **모든 요청을 401** 로 돌려준다. 그대로 돌면
    저널이 401로 차고, systemd가 무한 재시작해 정작 고쳐야 할 줄이 묻힌다.
    """
    with pytest.raises(worker.ConfigError, match="SUPERSUB_WORKER_TOKEN"):
        worker.Config.from_env({"SUPERSUB_API_BASE": "https://x/api/v1"})


def test_a_non_ascii_token_is_a_config_error_not_a_hiccup(worker):
    """🔴 헤더는 latin-1 이다 — 한글이 섞이면 urllib 이 UnicodeEncodeError 를 낸다.

    그것이 `ValueError` 라서 폴링 루프가 **일시적 오류로 착각하고 영원히
    재시도한다.** 저널에는 인코딩 오류만 흐르고 정작 원인(따옴표나 주석이
    딸려 들어간 토큰)은 아무 데도 안 적힌다. 2026-09-07 에 실제로 그랬다.
    """
    with pytest.raises(worker.ConfigError, match="ASCII"):
        worker.Config.from_env({"SUPERSUB_WORKER_TOKEN": "비밀-값"})


def test_an_empty_api_base_is_a_config_error(worker):
    """🔴 백엔드 주소에 기본값을 두지 않는다 — 저장소가 공개다.

    호스트명을 코드에 박으면 그대로 공개된다(미결 `jin` 22번). 그렇다고
    자리표시자 문자열을 기본값으로 두면 **배포에서 잘못된 URL 로 조용히
    붙는다** — 설정 누락이 설정 누락으로 보이지 않는다. 없으면 시작하지
    않는 쪽이 맞다.

    이 검사를 지우면 다음 사람이 "편의상" 기본값을 되살리고 호스트명이
    다시 공개된다.
    """
    with pytest.raises(worker.ConfigError, match="SUPERSUB_API_BASE"):
        worker.Config.from_env({"SUPERSUB_WORKER_TOKEN": "t"})


def test_reports_prefix_defaults_under_the_bucket(worker):
    c = worker.Config.from_env(
        {
            "SUPERSUB_WORKER_TOKEN": "t",
            "SUPERSUB_API_BASE": "https://example.invalid/api/v1",
            "SUPERSUB_S3_BUCKET": "다른버킷",
        }
    )
    assert c.reports_uri == "s3://다른버킷/reports"


# -- 루브릭 고르기 ----------------------------------------------------------


@pytest.mark.parametrize(
    ("sport", "expected"),
    [
        ("baseball", "baseball_pitching"),
        ("basketball", "basketball_jump_shot"),
        ("football", "football_instep_shot"),
    ],
)
def test_picks_the_one_active_rubric_of_the_sport(worker, sport, expected):
    """worker-interface.md 2절의 표 그대로다. draft는 고르지 않는다."""
    assert worker.pick_rubric(ROOT / "rubrics", sport).stem == expected


def _rubric_copy(src: Path, dest: Path, status: str) -> None:
    text = re.sub(r"^status: \w+$", f"status: {status}", src.read_text(encoding="utf-8"),
                  flags=re.MULTILINE)
    dest.write_text(text, encoding="utf-8")


def test_refuses_to_guess_when_two_are_active(worker, tmp_path):
    """🔴 draft를 승격시켜 둘이 되는 순간 **멈춘다.**

    아무거나 고르면 인사이드 패스를 인스텝 슈팅 루브릭으로 채점하고도 결과에
    아무 표시가 남지 않는다. 동작(motion)이 응답에 실리기 전까지의 방어선이다.
    """
    for name in ("football_instep_shot", "football_inside_pass"):
        _rubric_copy(ROOT / "rubrics" / f"{name}.yaml", tmp_path / f"{name}.yaml",
                     "active")

    with pytest.raises(worker.RubricUnavailable) as exc:
        worker.pick_rubric(tmp_path, "football")
    # 사유가 failure_reason 으로 나간다 — 무엇이 겹쳤는지 이름이 들어 있어야 한다.
    assert "instep_shot" in str(exc.value) and "inside_pass" in str(exc.value)


def test_refuses_a_sport_with_no_active_rubric(worker, tmp_path):
    _rubric_copy(ROOT / "rubrics" / "baseball_pitching.yaml",
                 tmp_path / "baseball_pitching.yaml", "draft")
    with pytest.raises(worker.RubricUnavailable, match="0개"):
        worker.pick_rubric(tmp_path, "baseball")


# -- 분석 명령줄 ------------------------------------------------------------


def test_the_command_always_names_a_rubric(worker, cfg):
    """🔴 `--rubric` 을 생략하면 기본값이 축구 인스텝 슈팅이다.

    야구 영상이 축구 루브릭으로 채점되고, **그 결과가 틀렸다는 것이 값에
    나타나지 않는다.** 이 검사를 지우면 그 결함이 조용히 돌아온다.
    """
    cmd = worker.analyze_command(cfg, _job(), ROOT / "rubrics/baseball_pitching.yaml")
    assert "--rubric" in cmd
    assert cmd[cmd.index("--rubric") + 1].endswith("baseball_pitching.yaml")


def test_the_command_writes_only_under_reports(worker, cfg):
    """워커는 `videos/` 를 읽기만 한다 — IAM 정책이 읽기 전용인 것이 의도다."""
    cmd = worker.analyze_command(cfg, _job(), ROOT / "rubrics/baseball_pitching.yaml")
    assert cmd[cmd.index("--out") + 1] == "s3://supersub-ai/reports"
    assert "s3://supersub-ai/videos/user-1/clip.mp4" in cmd


def test_the_command_carries_the_video_id(worker, cfg):
    """🔴 `video_id` 를 안 넘기면 리포트가 **계약 자리 밖**에 쌓인다.

    「저장」(`jin` 24번)은 원본을 `reports/<user_id>/<video_id>/source.mp4` 로
    옮긴다. 리포트가 옛 자리(업로드 폴더 + 타임스탬프)에 있으면 한 영상에 대한
    것이 두 군데로 갈린다.
    """
    cmd = worker.analyze_command(cfg, _job(), ROOT / "rubrics/baseball_pitching.yaml")
    assert cmd[cmd.index("--video-id") + 1] == "1b3c"


def test_the_video_id_is_omitted_when_the_job_has_none(worker, cfg):
    """옛 백엔드는 이 필드를 안 준다. 그때는 옛 자리로 가야지 죽으면 안 된다."""
    cmd = worker.analyze_command(cfg, _job(video_id=None),
                                 ROOT / "rubrics/baseball_pitching.yaml")
    assert "--video-id" not in cmd
    assert "None" not in cmd


def test_side_is_omitted_when_the_job_has_none(worker, cfg):
    """`side` 는 null 일 수 있다. None을 문자열로 넘기면 argparse가 거부한다."""
    cmd = worker.analyze_command(cfg, _job(side=None),
                                 ROOT / "rubrics/baseball_pitching.yaml")
    assert "--side" not in cmd
    assert "None" not in cmd

    cmd = worker.analyze_command(cfg, _job(side="left"),
                                 ROOT / "rubrics/baseball_pitching.yaml")
    assert cmd[cmd.index("--side") + 1] == "left"


def _busy_pattern() -> str:
    """autostop 이 "작업 중"으로 보는 패턴을 설정 예시에서 그대로 읽는다."""
    text = (ROOT / "deploy" / "autostop.conf.example").read_text(encoding="utf-8")
    match = re.search(r"^BUSY_PATTERN='(.+)'$", text, flags=re.MULTILINE)
    assert match, "autostop.conf.example 에서 BUSY_PATTERN 을 찾지 못했다"
    return match.group(1)


def test_the_analysis_child_is_seen_as_busy_by_autostop(worker, cfg):
    """🔴 분석 도중에 인스턴스가 꺼지면 안 된다.

    autostop 은 `pgrep -f` 로 "작업 중"을 판정한다. 워커가 analyze_s3.py 를
    **별도 프로세스로** 부르기 때문에 기존 패턴에 그대로 걸린다 — import 해서
    안에서 돌리도록 바꾸면 이 검사가 깨지고, 실제로는 분석 도중에 전원이
    내려간다(그때 그 작업은 running 인 채로 남는다).

    파이썬 `re` 는 POSIX 문자클래스(`[[:space:]]`)를 모르므로 실제 `grep -E`
    로 맞춰 본다 — 번역하면 그 번역이 틀릴 수 있다.
    """
    cmd = worker.analyze_command(cfg, _job(), ROOT / "rubrics/baseball_pitching.yaml")
    cmdline = " ".join(cmd)
    found = subprocess.run(
        ["grep", "-Eq", _busy_pattern()], input=cmdline, text=True, check=False
    )
    assert found.returncode == 0, (
        f"autostop 이 이 명령줄을 '작업 중'으로 보지 못한다:\n  {cmdline}\n"
        f"  패턴: {_busy_pattern()}"
    )


def test_the_worker_itself_is_not_seen_as_busy(worker):
    """🔴 반대쪽도 지킨다 — 폴링 프로세스는 "작업 중"이 **아니어야** 한다.

    워커는 큐가 비어 있는 동안에도 계속 떠 있다. BUSY_PATTERN 에 워커 이름을
    넣으면 인스턴스가 영영 안 꺼진다(상시 가동 월 $466). 지켜야 할 성질은
    "분석 도중에 안 꺼진다"이고 그건 위 검사가 맡는다.
    """
    cmdline = f"{sys.executable} {ROOT}/scripts/worker.py"
    found = subprocess.run(
        ["grep", "-Eq", _busy_pattern()], input=cmdline, text=True, check=False
    )
    assert found.returncode != 0, (
        "워커 폴링 프로세스가 '작업 중'으로 잡힌다 — 인스턴스가 안 꺼진다"
    )


# -- 실패 사유 --------------------------------------------------------------


def test_quality_gate_keeps_the_message_from_the_script(worker):
    outcome = worker.Outcome(code=2, last_line="분석 중단: 유효 프레임이 12개뿐이다")
    assert worker.failure_reason(outcome).startswith("품질 게이트 미달")
    assert "유효 프레임" in worker.failure_reason(outcome)


def test_other_codes_carry_the_code_and_the_last_line(worker):
    reason = worker.failure_reason(worker.Outcome(code=1, last_line="botocore 404"))
    assert "1" in reason and "botocore 404" in reason


def test_a_killed_run_says_so_instead_of_showing_the_signal(worker):
    """우리가 죽인 경우 종료 코드(-9 따위)는 뜻이 없다 — 이유가 값으로 남아야 한다."""
    reason = worker.failure_reason(
        worker.Outcome(code=-9, last_line="[측정] 46프레임", note="3600초를 넘겨 중단했다")
    )
    assert "3600초" in reason


# -- 백엔드 호출 ------------------------------------------------------------


def _intercept(worker, monkeypatch, responses):
    """`_request` 를 가로챈다. 보낸 것을 모아 돌려준다."""
    sent: list[tuple[str, str, dict | None]] = []
    queue = list(responses)

    def fake(cfg, method, path, payload=None):
        sent.append((method, path, payload))
        return queue.pop(0) if queue else (500, b"")

    monkeypatch.setattr(worker, "_request", fake)
    return sent


def test_an_empty_queue_is_not_an_error(worker, cfg, monkeypatch):
    """🔴 204 를 오류로 다루면 저널이 빈 폴링으로 찬다. 큐가 빈 것이 정상이다."""
    _intercept(worker, monkeypatch, [(204, b"")])
    assert worker.claim(cfg) is None


def test_claim_is_called_exactly_once_per_attempt(worker, cfg, monkeypatch):
    """🔴 claim 은 조회가 아니라 **소비**다.

    한 번 부를 때마다 작업 하나가 running 으로 넘어가므로, 실패했다고 안에서
    다시 부르면 **다른 작업**을 집는다 — 앞의 것은 아무도 안 든 채 남는다.
    """
    sent = _intercept(worker, monkeypatch, [(503, b"gateway")])
    with pytest.raises(RuntimeError):
        worker.claim(cfg)
    assert len(sent) == 1, "claim 이 안에서 재시도했다"


def test_a_401_is_fatal_rather_than_retried(worker, cfg, monkeypatch):
    _intercept(worker, monkeypatch, [(401, b"")])
    with pytest.raises(worker.ConfigError, match="401"):
        worker.claim(cfg)


def test_the_failure_reason_fits_the_column(worker, cfg, monkeypatch):
    """🔴 `failure_reason` 은 255자다. 넘겨 보내면 잘려서 원인이 사라진다."""
    sent = _intercept(worker, monkeypatch, [(204, b"")])
    worker.report(cfg, "9a2e", "failed", "긴사유" * 200)

    _, path, payload = sent[0]
    assert path.endswith("/9a2e")
    assert len(payload["failure_reason"]) == worker.FAILURE_REASON_MAX


def test_a_success_report_carries_no_reason_and_no_timestamp(worker, cfg, monkeypatch):
    """`finished_at` 은 서버가 찍는다 — 워커 시계가 어긋나면 소요가 음수가 된다."""
    sent = _intercept(worker, monkeypatch, [(204, b"")])
    assert worker.report(cfg, "9a2e", "succeeded") is True
    assert sent[0][2] == {"status": "succeeded"}


@pytest.mark.parametrize("code", [404, 409, 422])
def test_a_rejected_report_is_not_retried(worker, cfg, monkeypatch, code):
    """404 없는 작업 · 409 이미 끝남 · 422 상태값 오류 — 다시 물어도 같은 답이다."""
    sent = _intercept(worker, monkeypatch, [(code, b"")])
    assert worker.report(cfg, "9a2e", "failed", "사유") is False
    assert len(sent) == 1


def test_a_lost_report_is_retried(worker, cfg, monkeypatch):
    """보고가 안 되면 작업이 running 으로 남는다. 두 번 보내도 409 일 뿐이다."""
    sent = _intercept(worker, monkeypatch, [(502, b""), (204, b"")])
    monkeypatch.setattr(worker.time, "sleep", lambda s: None)
    assert worker.report(cfg, "9a2e", "succeeded") is True
    assert len(sent) == 2


# -- 한 건 처리 -------------------------------------------------------------


def test_an_unpickable_rubric_fails_the_job_without_running_it(
    worker, cfg, monkeypatch, tmp_path
):
    """루브릭을 못 고르면 **분석을 돌리지 않고** failed 로 보고한다."""
    sent = _intercept(worker, monkeypatch, [(204, b"")])

    def never(*a, **k):
        raise AssertionError("분석이 실행됐다")

    monkeypatch.setattr(worker, "run_analysis", never)
    cfg_no_rubrics = worker.Config.from_env(
        {
            "SUPERSUB_WORKER_TOKEN": "t",
            "SUPERSUB_API_BASE": "https://example.invalid/api/v1",
            "SUPERSUB_RUBRIC_DIR": str(tmp_path),
        }
    )
    worker.process(cfg_no_rubrics, _job(), worker.Stopper())

    method, path, payload = sent[0]
    assert method == "PATCH" and payload["status"] == "failed"
    assert "루브릭" in payload["failure_reason"]


def test_a_finished_job_is_always_reported(worker, cfg, monkeypatch):
    """성공하면 succeeded 로 옮겨진다 — 안 옮기면 큐가 안 줄어든다."""
    sent = _intercept(worker, monkeypatch, [(204, b"")])
    monkeypatch.setattr(
        worker, "run_analysis", lambda cmd, timeout, stopper: worker.Outcome(0, "저장: …")
    )
    worker.process(cfg, _job(), worker.Stopper())
    assert sent[0][2] == {"status": "succeeded"}


def test_a_crash_inside_the_analysis_still_reports(worker, cfg, monkeypatch):
    """🔴 예외가 새면 그 작업은 running 인 채로 영영 남는다 (회수 규칙이 없다)."""
    sent = _intercept(worker, monkeypatch, [(204, b"")])

    def boom(cmd, timeout, stopper):
        raise OSError("실행 파일을 찾을 수 없다")

    monkeypatch.setattr(worker, "run_analysis", boom)
    worker.process(cfg, _job(), worker.Stopper())
    assert sent[0][2]["status"] == "failed"


# -- analyze_s3.py 와의 계약 ------------------------------------------------


def test_a_single_video_propagates_its_exit_code(monkeypatch):
    """🔴 **이 검사를 지우면 실패가 성공으로 보고된다.**

    워커는 종료 코드 하나로 succeeded/failed 를 가른다. analyze_s3.main 이
    영상 한 편짜리 호출에서도 SystemExit 를 삼키면, 품질 게이트에 걸려 리포트가
    없는 분석이 `succeeded` 로 올라간다 — 화면에는 아무 표시도 안 남는다.
    2026-09-07 에 실제로 그 상태였다(주석은 "그대로 올라간다"였는데 코드가
    삼키고 있었다).
    """
    a3 = _load_script("analyze_s3")
    monkeypatch.setattr(a3, "resolve_videos", lambda uri, region: ["s3://b/v/one.mp4"])
    monkeypatch.setattr(a3, "load_rubric", lambda p: _StubRubric())

    def gate_failure(*a, **k):
        raise SystemExit(2)

    monkeypatch.setattr(a3, "analyze_one", gate_failure)
    monkeypatch.setattr(
        sys, "argv",
        ["analyze_s3.py", "s3://b/v/one.mp4", "--rubric", "r.yaml", "--out", "s3://b/r"],
    )
    with pytest.raises(SystemExit) as exc:
        a3.main()
    assert exc.value.code == 2


def test_a_folder_scan_still_ends_zero_when_some_clips_fail(monkeypatch):
    """여러 편일 때는 반대다 — 한 편의 품질 미달로 스캔 전체가 실패가 되면
    재시도가 무한히 돈다. 두 규칙이 함께 있어야 뜻이 맞는다."""
    a3 = _load_script("analyze_s3")
    monkeypatch.setattr(
        a3, "resolve_videos", lambda uri, region: ["s3://b/v/a.mp4", "s3://b/v/b.mp4"]
    )
    monkeypatch.setattr(a3, "load_rubric", lambda p: _StubRubric())

    def gate_failure(*a, **k):
        raise SystemExit(2)

    monkeypatch.setattr(a3, "analyze_one", gate_failure)
    monkeypatch.setattr(
        sys, "argv",
        ["analyze_s3.py", "s3://b/v/", "--rubric", "r.yaml", "--out", "s3://b/r"],
    )
    a3.main()  # 예외 없이 반환한다 = 종료 코드 0


def test_there_is_only_one_queue(monkeypatch):
    """🔴 큐를 소비하는 길은 **하나뿐**이어야 한다 (미결 jin 20번, 2026-09-08).

    `analyze_s3.py --skip-analyzed` 는 `reports/` 유무로 "안 돈 것"을 가리는
    두 번째 큐였다. 큐의 정본은 `analysis_job` 이고 그것을 집는 것은 worker.py 다.
    둘을 같이 두면 워커가 집어 `running` 으로 돌리는 사이 스캔이 같은 영상을 또
    돈다 — `reports/` 는 분석이 **끝나야** 생기기 때문이다. GPU 시간이 두 배로
    나가고 리포트가 둘 생기는데, **어느 쪽도 오류로 보이지 않는다.**

    되살리려면 이 검사를 지워야 한다. 지우기 전에 위 문단을 읽을 것.
    """
    a3 = _load_script("analyze_s3")
    monkeypatch.setattr(
        sys, "argv",
        ["analyze_s3.py", "s3://b/v/", "--rubric", "r.yaml", "--out", "s3://b/r",
         "--skip-analyzed"],
    )
    with pytest.raises(SystemExit) as exc:
        a3.main()
    assert exc.value.code == 2, (
        "--skip-analyzed 가 다시 살아 있다 — 큐가 둘이 된다"
    )


class _StubRubric:
    sport = "baseball"
    motion = "pitching"
    version = "0.1"
    criteria = ()
