"""분석 워커 — 큐 폴링 루프 (scripts/worker.py).

네트워크도 GPU도 S3도 쓰지 않는다. 백엔드는 `_request`를 가로채 흉내내고,
분석은 부르지 않는다 — 실제로 부르면 이 테스트가 EC2에서만 도는 테스트가 된다.

**여기 검사들이 막고 있는 것은 전부 "조용히 틀리는" 종류다.** 워커는 사람이
안 보는 동안 도는 것이라, 틀려도 화면에 아무것도 안 나타난다.
"""

from __future__ import annotations

import importlib.util
import json
import re
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
        "sport_code": "football",
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


def test_picks_the_one_active_rubric_of_the_sport(worker):
    """worker-interface.md 2절의 표 그대로다. draft는 고르지 않는다."""
    assert worker.pick_rubric(ROOT / "rubrics", "football").stem == "football_instep_shot"


@pytest.mark.parametrize("sport", ["baseball", "basketball", "", "soccer"])
def test_a_sport_we_do_not_support_is_refused_not_guessed(worker, sport):
    """🔴 축구 단일 종목이다 (2026.09.11) — 그래도 **기본값으로 때우지 않는다.**

    백엔드는 아직 다른 `sport_code` 를 실어 보낼 수 있다(참조 테이블에 남아
    있다 — 미결 `jin` 17번). 그때 축구 루브릭으로 채점하면 **결과가 틀렸다는
    것이 값에 나타나지 않는다.** 루브릭이 없으면 그 작업은 사유를 달고
    failed 로 남아야 한다.

    `soccer` 도 거부한다 — 데이터셋 출처 쪽 이름이고 루브릭의 종목 코드는
    `football` 이다. 둘을 섞으면 조용히 안 걸린다.
    """
    with pytest.raises(worker.RubricUnavailable, match="0개"):
        worker.pick_rubric(ROOT / "rubrics", sport)


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
    """draft 밖에 없으면 고르지 않는다 — 승격은 사람이 한다."""
    _rubric_copy(ROOT / "rubrics" / "football_instep_shot.yaml",
                 tmp_path / "football_instep_shot.yaml", "draft")
    with pytest.raises(worker.RubricUnavailable, match="0개"):
        worker.pick_rubric(tmp_path, "football")


# -- 분석 명령줄 ------------------------------------------------------------


def test_the_command_always_names_a_rubric(worker, cfg):
    """🔴 `--rubric` 을 생략하면 기본값이 축구 인스텝 슈팅이다.

    인사이드 패스 영상이 인스텝 루브릭으로 채점되고, **그 결과가 틀렸다는
    것이 값에 나타나지 않는다.** 이 검사를 지우면 그 결함이 조용히 돌아온다.
    (축구 단일 종목이 된 뒤에도 같다 — 동작이 둘이다.)
    """
    cmd = worker.analyze_command(cfg, _job(), ROOT / "rubrics/football_inside_pass.yaml")
    assert "--rubric" in cmd
    assert cmd[cmd.index("--rubric") + 1].endswith("football_inside_pass.yaml")


def test_the_command_writes_only_under_reports(worker, cfg):
    """워커는 `videos/` 를 읽기만 한다 — IAM 정책이 읽기 전용인 것이 의도다."""
    cmd = worker.analyze_command(cfg, _job(), ROOT / "rubrics/football_inside_pass.yaml")
    assert cmd[cmd.index("--out") + 1] == "s3://supersub-ai/reports"
    assert "s3://supersub-ai/videos/user-1/clip.mp4" in cmd


def test_the_command_carries_the_video_id(worker, cfg):
    """🔴 `video_id` 를 안 넘기면 리포트가 **계약 자리 밖**에 쌓인다.

    「저장」(`jin` 24번)은 원본을 `reports/<user_id>/<video_id>/source.mp4` 로
    옮긴다. 리포트가 옛 자리(업로드 폴더 + 타임스탬프)에 있으면 한 영상에 대한
    것이 두 군데로 갈린다.
    """
    cmd = worker.analyze_command(cfg, _job(), ROOT / "rubrics/football_inside_pass.yaml")
    assert cmd[cmd.index("--video-id") + 1] == "1b3c"


def test_the_video_id_is_omitted_when_the_job_has_none(worker, cfg):
    """옛 백엔드는 이 필드를 안 준다. 그때는 옛 자리로 가야지 죽으면 안 된다."""
    cmd = worker.analyze_command(cfg, _job(video_id=None),
                                 ROOT / "rubrics/football_inside_pass.yaml")
    assert "--video-id" not in cmd
    assert "None" not in cmd


def test_side_is_omitted_when_the_job_has_none(worker, cfg):
    """`side` 는 null 일 수 있다. None을 문자열로 넘기면 argparse가 거부한다."""
    cmd = worker.analyze_command(cfg, _job(side=None),
                                 ROOT / "rubrics/football_inside_pass.yaml")
    assert "--side" not in cmd
    assert "None" not in cmd

    cmd = worker.analyze_command(cfg, _job(side="left"),
                                 ROOT / "rubrics/football_inside_pass.yaml")
    assert cmd[cmd.index("--side") + 1] == "left"


# -- 🔴 여기 있던 autostop 검사 셋을 지웠다 (2026.09.21) --------------------
#
# `test_the_analysis_child_is_seen_as_busy_by_autostop` ·
# `test_the_worker_itself_is_not_seen_as_busy` ·
# `test_the_detect_child_is_seen_as_busy_by_autostop` 과 공용 `_busy_pattern()`.
#
# 셋 다 `deploy/autostop.conf.example` 의 `BUSY_PATTERN` 을 읽어 "분석 중인
# 인스턴스가 꺼지지 않는다"를 지키고 있었는데, **오토스탑을 팀 결정으로
# 없앴다**(`a16848b`, 2026-09-18 — `deploy/` 의 autostop 파일 6개 삭제).
# 읽을 파일이 사라져 세 검사가 `FileNotFoundError` 로 죽고 있었다.
#
# 🔴 **되살리지 않는다.** 지키던 성질("분석 도중에 전원이 내려가지 않는다")은
# 결함이 고쳐진 것이 아니라 **판정 주체가 없어진 것**이다 — 이제 인스턴스는
# 사람이 끈다(`fastapi/docs/api-contract.md` 의 2026-09-18 정정도 같은 말).
# 자동 종료를 다시 넣게 되면 그때 이 검사도 **함께** 되살린다. 그 전까지
# 여기에 `BUSY_PATTERN` 을 읽는 코드를 다시 두면 또 빨개진다.


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


def test_every_backend_call_names_itself_in_the_user_agent(worker, cfg, monkeypatch):
    """🔴 UA 를 안 주면 urllib 이 `Python-urllib/3.x` 를 보내고, 백엔드 앞단
    Cloudflare 가 그 문자열을 403(`error code: 1010`)으로 끊는다. 2026.09.16
    08:27 부터 워커가 작업을 한 건도 못 집은 원인이다 — **오리진까지 가지
    않으므로 백엔드 로그에는 아무것도 안 남고**, 워커 저널의 403 만 보고
    토큰을 의심하게 된다. `_request` 하나만 보면 되는 이유는 claim 과 보고가
    둘 다 여기를 지나서다.
    """
    seen: list = []

    class _Resp:
        status = 204

        def read(self) -> bytes:
            return b""

        def __enter__(self):
            return self

        def __exit__(self, *exc) -> bool:
            return False

    def fake_urlopen(req, timeout=None):
        seen.append(req)
        return _Resp()

    monkeypatch.setattr(worker.urllib.request, "urlopen", fake_urlopen)
    worker._request(cfg, "POST", "/internal/analysis-jobs/claim")

    ua = seen[0].get_header("User-agent")
    assert ua, "UA 를 안 주면 urllib 이 기본값을 채운다"
    assert "Python-urllib" not in ua


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
    """성공하면 succeeded 로 옮겨진다 — 안 옮기면 큐가 안 줄어든다.

    성공 보고에는 **리포트 자리가 함께 실린다** (미결 `jin` 27번) — 그래서
    이 스텁은 자식이 자리를 적은 것까지 흉내낸다. 자리가 없는 경우는
    `test_a_success_is_never_reported_without_a_report_key` 가 따로 본다.
    """
    sent = _intercept(worker, monkeypatch, [(204, b"")])

    def analysis(cmd, timeout, stopper):
        path = Path(cmd[cmd.index("--result-json") + 1])
        path.write_text(json.dumps({"reports": [
            {"report_uri": "s3://supersub-ai/reports/u1/v9/report.json"},
        ]}), encoding="utf-8")
        return worker.Outcome(0, "저장: …")

    monkeypatch.setattr(worker, "run_analysis", analysis)
    worker.process(cfg, _job(), worker.Stopper())
    assert sent[0][2] == {"status": "succeeded",
                          "report_key": "reports/u1/v9/report.json"}


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
    sport = "football"
    motion = "instep_shot"
    version = "0.1"
    criteria = ()
    # 집중 항목 검증이 대조하는 목록 (미결 `paik` 8번).
    criterion_ids = ("follow_through", "guide_hand")


# -- 리포트 자리를 완료 보고에 싣는다 (미결 `paik` 11번) ----------------------
#
# 🔴 **여기 검사들이 막고 있는 것**: 분석은 끝나는데 백엔드가 리포트 파일을
#    못 찾는 상태. 자리를 정하는 규칙은 `analyze_s3.report_targets` 안에만
#    있어서 바깥에서는 계산할 수 없다. 워커가 안 실으면 화면은 영영 mock 이다.


def _result_file(tmp_path, uri, name="result.json"):
    p = tmp_path / name
    p.write_text(json.dumps({"reports": [{"video": "s3://b/v.mp4",
                                          "report_uri": uri}]}), encoding="utf-8")
    return p


def test_the_report_key_is_read_from_the_file_the_analysis_wrote(worker, tmp_path):
    """버킷 상대 키로 꺼낸다 — 백엔드의 `storage_key` 와 같은 모양이다."""
    f = _result_file(tmp_path, "s3://supersub-ai/reports/u1/v9/report.json")
    assert worker.report_key_from(f, "supersub-ai") == "reports/u1/v9/report.json"


def test_a_missing_or_broken_result_file_yields_no_key(worker, tmp_path):
    """자리 파일이 없거나 깨졌으면 **키를 지어내지 않는다.**

    이 함수는 키만 낸다. 키가 없을 때 무엇을 보고할지는 `process` 가 정하고,
    그 답은 「실패」다 — 성공 보고에는 항상 `report_key` 가 실린다는 것이
    계약이 되었다(미결 `jin` 27번). 아래
    `test_a_success_is_never_reported_without_a_report_key` 가 그것을 지킨다.
    """
    assert worker.report_key_from(tmp_path / "없음.json", "supersub-ai") is None
    broken = tmp_path / "broken.json"
    broken.write_text("{ 이건 JSON 이 아니다", encoding="utf-8")
    assert worker.report_key_from(broken, "supersub-ai") is None
    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"reports": []}), encoding="utf-8")
    assert worker.report_key_from(empty, "supersub-ai") is None


def test_a_report_in_another_bucket_is_not_sent_as_a_key(worker, tmp_path):
    """🔴 버킷 상대 키는 **그 버킷 안에서만** 뜻이 있다.

    `SUPERSUB_REPORTS_URI` 가 다른 버킷을 가리키면 키만으로는 못 가리킨다.
    틀린 자리를 싣느니 안 싣는다 — 백엔드가 없는 객체를 읽으려 든다.
    """
    f = _result_file(tmp_path, "s3://다른버킷/reports/u1/v9/report.json")
    assert worker.report_key_from(f, "supersub-ai") is None


def test_two_reports_are_ambiguous_so_nothing_is_sent(worker, tmp_path):
    """작업 하나는 영상 하나다. 둘이면 어느 것이 이번 결과인지 안 정해진다."""
    f = tmp_path / "two.json"
    f.write_text(json.dumps({"reports": [
        {"report_uri": "s3://supersub-ai/reports/u1/a/report.json"},
        {"report_uri": "s3://supersub-ai/reports/u1/b/report.json"},
    ]}), encoding="utf-8")
    assert worker.report_key_from(f, "supersub-ai") is None


def test_the_analysis_is_told_where_to_write_its_result(worker, cfg, tmp_path):
    """워커가 자리 파일을 지정해야 자식이 적는다."""
    cmd = worker.analyze_command(cfg, _job(), Path("r.yaml"), tmp_path / "r.json")
    assert "--result-json" in cmd
    assert str(tmp_path / "r.json") in cmd


def test_a_succeeded_report_carries_the_key_and_a_failed_one_does_not(
    worker, cfg, monkeypatch
):
    """🔴 실패한 작업에 자리를 실으면 **없는 파일을 가리킨다.**"""
    sent = _intercept(worker, monkeypatch, [(204, b""), (204, b"")])
    worker.report(cfg, "j1", "succeeded", report_key="reports/u1/v9/report.json")
    worker.report(cfg, "j2", "failed", "품질 미달",
                  report_key="reports/u1/v9/report.json")
    assert sent[0][2] == {"status": "succeeded",
                          "report_key": "reports/u1/v9/report.json"}
    assert "report_key" not in sent[1][2]


def test_a_finished_job_reports_the_place_the_analysis_actually_wrote(
    worker, cfg, monkeypatch, tmp_path
):
    """끝에서 끝까지 — 자식이 적은 자리가 `PATCH` 본문에 실려 나가는가.

    🔴 이것이 이 항목의 전부다. 앞의 조각들이 다 맞아도 여기서 안 실리면
    백엔드는 여전히 리포트를 못 찾는다.
    """
    def analysis_that_writes_its_place(cmd, timeout, stopper):
        path = Path(cmd[cmd.index("--result-json") + 1])
        path.write_text(json.dumps({"reports": [
            {"video": "s3://supersub-ai/videos/u1/clip.mp4",
             "report_uri": "s3://supersub-ai/reports/u1/1b3c/report.json"},
        ]}), encoding="utf-8")
        return worker.Outcome(code=0, last_line="")

    monkeypatch.setattr(worker, "run_analysis", analysis_that_writes_its_place)
    monkeypatch.setattr(worker, "pick_rubric", lambda d, s: Path("r.yaml"))
    sent = _intercept(worker, monkeypatch, [(204, b"")])

    worker.process(cfg, _job(), worker.Stopper())

    assert sent[-1][0] == "PATCH"
    assert sent[-1][2] == {"status": "succeeded",
                           "report_key": "reports/u1/1b3c/report.json"}


def test_the_place_file_does_not_leak_between_jobs(worker, cfg, monkeypatch):
    """🔴 앞 작업의 자리를 물려받으면 **실패한 작업이 남의 리포트를 가리킨다.**

    작업마다 새 임시 폴더를 쓰는 것이 그것을 막는다. 두 번째 작업의 분석이
    아무것도 안 적었는데 첫 번째의 값이 실리면 이 검사가 빨개진다.
    """
    seen: list[Path] = []

    def analysis(cmd, timeout, stopper):
        path = Path(cmd[cmd.index("--result-json") + 1])
        seen.append(path)
        if len(seen) == 1:
            path.write_text(json.dumps({"reports": [
                {"report_uri": "s3://supersub-ai/reports/u1/first/report.json"},
            ]}), encoding="utf-8")
        return worker.Outcome(code=0, last_line="")

    monkeypatch.setattr(worker, "run_analysis", analysis)
    monkeypatch.setattr(worker, "pick_rubric", lambda d, s: Path("r.yaml"))
    sent = _intercept(worker, monkeypatch, [(204, b""), (204, b"")])

    worker.process(cfg, _job(job_id="j1"), worker.Stopper())
    worker.process(cfg, _job(job_id="j2"), worker.Stopper())

    assert sent[0][2]["report_key"] == "reports/u1/first/report.json"
    assert "report_key" not in sent[1][2]
    # 두 번째는 자리를 못 실었으므로 **실패**로 나간다 (미결 `jin` 27번).
    assert sent[1][2]["status"] == "failed"
    assert seen[0] != seen[1], "두 작업이 같은 자리 파일을 썼다"


@pytest.mark.parametrize(
    "wrote, why",
    [
        (None, "자리 파일을 아예 안 적었다"),
        ({"reports": []}, "빈 목록"),
        ({"reports": [{"report_uri": "s3://다른버킷/reports/u1/v/report.json"}]},
         "다른 버킷"),
        ({"reports": [{"report_uri": "s3://supersub-ai/reports/u1/a/report.json"},
                      {"report_uri": "s3://supersub-ai/reports/u1/b/report.json"}]},
         "두 건이라 모호"),
    ],
)
def test_a_success_is_never_reported_without_a_report_key(
    worker, cfg, monkeypatch, wrote, why
):
    """🔴 **키 없는 `succeeded` 는 영원히 빈 리포트다** (미결 `jin` 27번).

    적재가 `report_key` 로 S3 를 읽어 들이기로 정해졌으므로, 키가 없으면
    적재할 것이 없다. 그런데 작업은 `succeeded` 로 닫혀 있어 **화면은 아무것도
    못 찾고 사용자에게는 다시 시도할 방법도 안 보인다.** 실패로 드러내면
    적어도 재시도가 된다 — 그 약속을 여기서 지킨다.
    """
    def analysis(cmd, timeout, stopper):
        if wrote is not None:
            path = Path(cmd[cmd.index("--result-json") + 1])
            path.write_text(json.dumps(wrote), encoding="utf-8")
        return worker.Outcome(code=0, last_line="")

    monkeypatch.setattr(worker, "run_analysis", analysis)
    monkeypatch.setattr(worker, "pick_rubric", lambda d, s: Path("r.yaml"))
    sent = _intercept(worker, monkeypatch, [(204, b"")])

    worker.process(cfg, _job(), worker.Stopper())

    body = sent[-1][2]
    assert body["status"] == "failed", f"{why}: 키 없이 성공으로 보고됐다"
    assert "report_key" not in body
    assert "report_key" in body["failure_reason"], "원인이 안 적혔다"


def test_the_analysis_records_where_it_put_the_report(monkeypatch, tmp_path):
    """자식 쪽 절반 — `--result-json` 에 자리를 적는가.

    워커가 아무리 잘 읽어도 자식이 안 적으면 못 싣는다. 두 검사가 짝이다.
    """
    a3 = _load_script("analyze_s3")
    monkeypatch.setattr(a3, "resolve_videos", lambda uri, region: ["s3://b/v/one.mp4"])
    monkeypatch.setattr(a3, "load_rubric", lambda p: _StubRubric())
    monkeypatch.setattr(
        a3, "analyze_one",
        lambda *a, **k: "s3://b/reports/u1/v9/report.json",
    )
    out = tmp_path / "result.json"
    monkeypatch.setattr(sys, "argv", [
        "analyze_s3.py", "s3://b/v/one.mp4", "--rubric", "r.yaml",
        "--out", "s3://b/reports", "--result-json", str(out),
    ])
    a3.main()
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["reports"] == [
        {"video": "s3://b/v/one.mp4",
         "report_uri": "s3://b/reports/u1/v9/report.json"},
    ]


def test_a_failed_single_analysis_writes_no_place_file(monkeypatch, tmp_path):
    """🔴 실패했는데 자리 파일이 남으면 **없는 리포트를 가리키게 된다.**

    한 편짜리 호출은 SystemExit 가 그대로 올라가므로 파일 쓰는 자리에 못 온다.
    그것이 워커의 「없으면 안 싣는다」와 짝을 이룬다.
    """
    a3 = _load_script("analyze_s3")
    monkeypatch.setattr(a3, "resolve_videos", lambda uri, region: ["s3://b/v/one.mp4"])
    monkeypatch.setattr(a3, "load_rubric", lambda p: _StubRubric())

    def gate_failure(*a, **k):
        raise SystemExit(2)

    monkeypatch.setattr(a3, "analyze_one", gate_failure)
    out = tmp_path / "result.json"
    monkeypatch.setattr(sys, "argv", [
        "analyze_s3.py", "s3://b/v/one.mp4", "--rubric", "r.yaml",
        "--out", "s3://b/reports", "--result-json", str(out),
    ])
    with pytest.raises(SystemExit):
        a3.main()
    assert not out.exists()


# -- 「집중해서 볼 항목」 (미결 `paik` 8번) ----------------------------------
#
# 🔴 **판단은 A안이다**: 채점은 그대로 두고 화면 강조용으로만 싣는다.
#    B안(고른 것만 채점 + 가중치 재정규화)을 택하지 않은 이유는 같은 영상이
#    고른 것에 따라 다른 점수를 내면 **선수끼리 비교가 안 되기** 때문이다.
#    아래 검사들이 B안으로 슬며시 넘어가는 것을 막는다.


def test_the_focus_choice_is_passed_through_when_the_job_has_one(worker, cfg):
    cmd = worker.analyze_command(
        cfg, _job(focus=["follow_through", "guide_hand"]), Path("r.yaml"))
    assert cmd[cmd.index("--focus") + 1] == "follow_through,guide_hand"


def test_no_focus_means_the_whole_thing_not_a_failure(worker, cfg):
    """🔴 빈 목록은 「전체적으로」다 — 기본이자 가장 흔한 경우다.

    백엔드에 아직 칸이 없어서 지금은 **항상** 이 갈래를 탄다. 여기서 죽으면
    모든 분석이 죽는다.
    """
    for job in (_job(), _job(focus=None), _job(focus=[]), _job(focus=["", "  "])):
        cmd = worker.analyze_command(cfg, job, Path("r.yaml"))
        assert "--focus" not in cmd
        assert "None" not in cmd


# -- 「이 사람으로 분석」 (미결 `paik` 6번) -----------------------------------
#
#    백엔드가 claim 응답에 `subject_box`(정규화 0~1 네 값)와 `subject_at_ms` 를
#    싣는다. 워커는 그것을 자식에게 넘기기만 한다 — 규격은
#    `fastapi/docs/worker-interface.md` 1절.


def test_the_subject_box_is_passed_through_when_the_job_has_one(worker, cfg):
    """찍은 사람이 실제로 분석되려면 지정이 자식까지 가야 한다."""
    cmd = worker.analyze_command(
        cfg, _job(subject_box=[0.39, 0.35, 0.12, 0.4], subject_at_ms=4200),
        Path("r.yaml"))
    assert cmd[cmd.index("--subject-box") + 1] == "0.39,0.35,0.12,0.4"
    assert cmd[cmd.index("--subject-at-ms") + 1] == "4200"


def test_no_subject_box_means_pick_automatically_not_a_failure(worker, cfg):
    """🔴 지정이 없는 것은 **정식 경로**다 — 지금은 거의 모든 작업이 이쪽이다.

    둘 다 생략 = 「자동으로 고르기」이고 실패가 아니다(계약). 여기서 플래그가
    붙으면 자식이 `None` 을 좌표로 읽고 죽어 **모든 자동 분석이 죽는다.**
    """
    for job in (_job(),
                _job(subject_box=None, subject_at_ms=None),
                _job(subject_box=None, subject_at_ms=4200)):
        cmd = worker.analyze_command(cfg, job, Path("r.yaml"))
        assert "--subject-box" not in cmd
        assert "None" not in cmd


def test_a_half_given_subject_is_not_passed_as_half(worker, cfg):
    """🔴 박스만 있고 시각이 없으면 **아무것도 붙이지 않는다.**

    하나만 붙이면 자식이 「박스를 주면 시각도 함께」로 죽는데, 그것은 지정이
    없는 것과 **다른 사건**이다 — 지정이 없으면 자동으로 골라 정상 분석돼야
    한다. 계약이 both-or-neither 를 등록 시점에 막지만, 그것이 뚫렸을 때
    **분석 전체가 죽는 쪽으로 무너지지 않게** 한다.
    """
    cmd = worker.analyze_command(
        cfg, _job(subject_box=[0.39, 0.35, 0.12, 0.4]), Path("r.yaml"))
    assert "--subject-box" not in cmd
    assert "--subject-at-ms" not in cmd


def test_the_worker_does_not_re_validate_the_subject_box(worker, cfg):
    """🔴 범위 밖 좌표도 **그대로 넘긴다** — 판정은 한 곳에서만 한다.

    무엇이 올바른 지정인가는 `pose.parse_subject_spec` 하나가 정한다. 워커가
    같은 규칙을 복사해 미리 거르면, 두 곳이 갈렸을 때 **같은 입력이 경로에
    따라 통과했다 막혔다 한다**(미결 10번의 형태). 잘못된 값은 자식이 0 아닌
    코드로 죽고 그 사유가 `failure_reason` 에 남는 것이 옳은 실패다.
    """
    cmd = worker.analyze_command(
        cfg, _job(subject_box=[640, 360, 200, 400], subject_at_ms=4200),
        Path("r.yaml"))
    assert cmd[cmd.index("--subject-box") + 1] == "640,360,200,400"


def test_focus_does_not_change_the_score(worker):
    """🔴 A안의 전부 — 고른 것이 점수를 바꾸면 안 된다.

    `aggregate` 는 `focus` 를 아예 모른다. 이 검사가 빨개진다는 것은 누군가
    채점 경로에 focus 를 끌어들였다는 뜻이고, 그 순간 같은 영상의 점수가
    사용자 선택에 따라 달라진다.
    """
    import inspect

    from supersub_agent import scoring

    assert "focus" not in inspect.getsource(scoring.aggregate)
    assert "focus" not in inspect.getsource(scoring.Rubric.applicable_criteria)


def test_an_unknown_focus_id_is_recorded_not_swallowed(monkeypatch):
    """🔴 화면이 낡은 id 를 보내면 **드러나야 한다.**

    조용히 버리면 사용자가 고른 것이 아무 일도 안 일어난 채 사라지고, 왜
    강조가 안 되는지 아무도 모른다. 그렇다고 분석을 죽이지도 않는다 —
    강조 힌트 하나 때문에 리포트가 통째로 없어지는 것이 더 나쁘다.
    """
    a3 = _load_script("analyze_s3")
    rubric = _StubRubric()
    env = a3.focus_envelope(rubric, "follow_through,없는항목")
    assert env["applied"] == ["follow_through"]
    assert env["unknown"] == ["없는항목"]
    assert env["requested"] == ["follow_through", "없는항목"]


def test_an_empty_focus_envelope_is_all_three_empty(monkeypatch):
    a3 = _load_script("analyze_s3")
    for value in (None, "", "  ", ",,"):
        assert a3.focus_envelope(_StubRubric(), value) == {
            "requested": [], "applied": [], "unknown": []
        }


def test_the_report_says_which_video_it_is_about(monkeypatch, tmp_path):
    """🔴 봉투가 스스로 어느 영상인지 말해야 한다 (미결 `jin` 24번 (1)).

    `source_video` 는 「저장」 뒤에 죽는다 — `keep` 이 원본을 `reports/` 로
    옮기고 `videos/` 쪽을 지운다. `video_id` 가 없으면 그 순간 **리포트 안에서
    어느 영상 것인지 가리키는 값이 하나도 안 남고**, 읽는 쪽이 S3 키를 파싱해
    되짚어야 한다 — 자리 규칙이 두 곳에 생기는 형태다(`paik` 11번에서 배제했다).

    배치·평가 실행에는 `video_id` 가 없으므로 그때는 `None` 이다. 🔴 모르면
    지어내지 않는다 — 빈 문자열이나 파일명으로 채우면 없는 행을 가리킨다.
    """
    a3 = _load_script("analyze_s3")
    import ast
    import inspect

    # 봉투는 `build_report` 가 짓는다 (미결 `jin` 27번에서 `analyze_one` 에서
    # 떼어냈다 — 검사할 수 있게 하려고). 모듈 최상위 함수라 getsource 가
    # 0열부터 준다 — dedent·cleandoc 을 걸면 오히려 들여쓰기가 깨진다.
    tree = ast.parse(inspect.getsource(a3.build_report))
    keys = {
        k.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Dict)
        for k in node.keys
        if isinstance(k, ast.Constant) and isinstance(k.value, str)
    }
    assert "video_id" in keys, "리포트 봉투에 video_id 가 없다"
    assert "source_video" in keys


def test_the_default_poll_interval_is_not_the_users_waiting_room(worker):
    """🔴 이 값의 **절반이 사용자가 보는 대기 시간**이다 (2026-09-15).

    45초였을 때 분석은 1분대인데 그 앞에 평균 22.5초가 붙었다 — 아무 일도
    일어나지 않는 시간이다. 빈 claim 은 로그를 남기지 않으므로(`claim()`)
    촘촘하게 돌아도 저널이 늘지 않고, 자동 종료는 이 주기가 아니라 분석 자식
    프로세스를 본다.

    올리고 싶어지면 **그만큼이 대기 시간에 붙는다**는 것을 먼저 보라고 이
    검사가 있다. 밀린 작업은 이 값과 무관하게 연달아 처리된다.
    """
    cfg = worker.Config.from_env(
        {"SUPERSUB_WORKER_TOKEN": "wk_test_0000",
         "SUPERSUB_API_BASE": "https://example.invalid/api/v1"}
    )
    assert cfg.poll_seconds <= 10, "기본 폴링이 대기 시간을 지배한다"


# -- 검출(`detect`) 작업 ----------------------------------------------------
#
#    같은 큐에 종류가 둘이 됐다 (미결 `ho` 44번). `claim` 응답의 `job_type` 이
#    갈라 주고, `detect` 면 `detect_subjects.py` 를 불러 `detection_result` 로
#    보고한다. 규격은 `fastapi/docs/worker-interface.md` 6절.
#
#    🔴 여기 검사들이 지키는 성질은 **분석 경로가 안 바뀌는 것**과 **화면이
#    받은 박스가 분석에 그대로 돌아가는 것** 둘이다.


DETECT_RESULT = {
    "people": [{"box": [0.287, 0.199, 0.168, 0.666], "score": 0.909}],
    "ball": {"x": 0.661, "y": 0.706, "score": 0.918},
    "frame": 30,
    "at_clamped": False,
    "source_video": "s3://supersub-ai/videos/user-1/clip.mp4",
}


def _detect_job(**over) -> dict:
    """검출 작업의 claim 응답. 🔴 `sport_code` 가 **없다** — `detect` 작업에는
    비어 있을 수 있다는 것이 규격이고(6절 2번), 그래도 돌아야 한다."""
    job = {
        "job_id": "7c1d",
        "video_id": "1b3c",
        "storage_key": "videos/user-1/clip.mp4",
        "job_type": "detect",
        "subject_at_ms": 1000,
    }
    job.update(over)
    return job


def _detect_run(worker, monkeypatch, result: dict | str | None, code: int = 0,
                last_line: str = "") -> list[list[str]]:
    """검출 자식을 흉내낸다 — 받은 명령줄을 모아 돌려준다."""
    seen: list[list[str]] = []

    def fake(cmd, timeout, stopper):
        seen.append(cmd)
        if result is not None:
            path = Path(cmd[cmd.index("--result-json") + 1])
            path.write_text(
                result if isinstance(result, str)
                else json.dumps(result, ensure_ascii=False),
                encoding="utf-8",
            )
        return worker.Outcome(code, last_line)

    monkeypatch.setattr(worker, "run_analysis", fake)
    return seen


def test_a_detect_job_calls_the_detector_not_the_analysis(worker, cfg, monkeypatch):
    """🔴 `job_type` 을 안 보고 분석으로 넘기면 `sport_code` 가 비어 있어서
    루브릭 단계에서 엉뚱한 사유로 죽는다 — 사용자에게는 「채점할 루브릭이
    없다」가 나가는데 이 작업은 채점을 부탁한 적이 없다."""
    _intercept(worker, monkeypatch, [(204, b"")])
    seen = _detect_run(worker, monkeypatch, DETECT_RESULT)

    worker.process(cfg, _detect_job(), worker.Stopper())

    cmd = " ".join(seen[0])
    assert "detect_subjects.py" in cmd
    assert "analyze_s3.py" not in cmd
    assert "--rubric" not in cmd, "검출은 채점하지 않는다"
    assert "--out" not in cmd, "검출은 리포트를 안 만든다"


def test_the_detector_looks_at_the_frame_the_screen_showed(worker, cfg, monkeypatch):
    """🔴 `--at-ms` 가 `subject_at_ms` 와 같아야 **같은 화면**을 본다.

    화면은 이 목록에서 고른 박스를 그대로 분석에 넘긴다(`--subject-box` ·
    `--subject-at-ms`). 시각이 어긋나면 사용자가 본 적 없는 프레임의 후보를
    내주고, 그 박스로 분석하면 **다른 사람이 분석된다.**
    """
    _intercept(worker, monkeypatch, [(204, b"")])
    seen = _detect_run(worker, monkeypatch, DETECT_RESULT)

    worker.process(cfg, _detect_job(subject_at_ms=4200), worker.Stopper())

    assert seen[0][seen[0].index("--at-ms") + 1] == "4200"


def test_the_candidates_are_reported_unchanged(worker, cfg, monkeypatch):
    """🔴 자식이 낸 JSON을 **그대로** 싣는다 (6절 3번).

    좌표는 정규화 0~1 이고 `people[].box` 가 그대로 `--subject-box` 로 돌아가는
    것이 이 기능의 전부다. 워커가 키를 고르거나 좌표를 손보면 **화면이 받는
    박스와 분석이 받는 박스가 갈린다.**
    """
    sent = _intercept(worker, monkeypatch, [(204, b"")])
    _detect_run(worker, monkeypatch, DETECT_RESULT)

    worker.process(cfg, _detect_job(), worker.Stopper())

    method, path, payload = sent[0]
    assert method == "PATCH" and path.endswith("/7c1d")
    assert payload["status"] == "succeeded"
    assert payload["detection_result"] == DETECT_RESULT


def test_a_detect_report_never_carries_a_report_key(worker, cfg, monkeypatch):
    """🔴 `detect` 작업은 리포트가 없다 (6절 「하지 말 것」).

    실어 보내면 받는 쪽이 **없는 S3 객체**를 적재하려다 실패한다 — 그쪽 설계가
    「`report_key` 가 없으면 적재를 안 한다」로 되어 있어서다.
    """
    sent = _intercept(worker, monkeypatch, [(204, b"")])
    _detect_run(worker, monkeypatch, DETECT_RESULT)

    worker.process(cfg, _detect_job(), worker.Stopper())

    assert "report_key" not in sent[0][2]


def test_nobody_in_the_frame_is_a_success_not_a_failure(worker, cfg, monkeypatch):
    """🔴 0명은 정상 경로다. 화면은 0명이면 드래그로 떨어진다 — 실패로 만들면
    화면이 「사람이 없습니다」로 막아 버리고 사용자는 찍을 방법이 없어진다."""
    sent = _intercept(worker, monkeypatch, [(204, b"")])
    _detect_run(worker, monkeypatch, {"people": [], "ball": None, "frame": 30})

    worker.process(cfg, _detect_job(), worker.Stopper())

    payload = sent[0][2]
    assert payload["status"] == "succeeded"
    assert payload["detection_result"]["people"] == []


def test_a_broken_candidate_file_is_not_reported_as_success(worker, cfg, monkeypatch):
    """🔴 실을 것이 없는 성공은 성공이 아니다 — `report_key` 와 같은 판단이다.

    빈 목록으로 succeeded 를 내면 화면은 **영원히 빈 목록**이고 작업은 끝난
    것으로 남아 다시 걸 방법조차 안 보인다.
    """
    for broken in ("{깨진", json.dumps({"ball": None}), None):
        sent = _intercept(worker, monkeypatch, [(204, b"")])
        _detect_run(worker, monkeypatch, broken)

        worker.process(cfg, _detect_job(), worker.Stopper())

        assert sent[0][2]["status"] == "failed"


def test_a_detect_job_without_a_time_is_refused_rather_than_guessed(
    worker, cfg, monkeypatch
):
    """🔴 시각을 지어내면 **화면이 본 것과 다른 프레임**의 후보가 나간다.

    사용자는 자기가 보던 사람이 목록에 없는 이유를 알 수 없고, 그 상태가
    「검출이 사람을 못 잡는다」로 보인다 — 실제로는 다른 화면을 본 것이다.
    """
    sent = _intercept(worker, monkeypatch, [(204, b"")])

    def never(*a, **k):
        raise AssertionError("검출이 실행됐다")

    monkeypatch.setattr(worker, "run_analysis", never)
    worker.process(cfg, _detect_job(subject_at_ms=None), worker.Stopper())

    assert sent[0][2]["status"] == "failed"
    assert "subject_at_ms" in sent[0][2]["failure_reason"]


def test_a_detect_failure_does_not_tell_the_user_to_film_again(worker):
    """🔴 종료 코드 2의 뜻이 분석과 다르다.

    분석의 2는 「품질 게이트 미달(다시 찍어야 풀린다)」이고 검출의 2는 「그
    시각의 프레임을 못 읽었다」다. 분석 쪽 문구를 그대로 쓰면 사용자가 멀쩡한
    영상을 다시 찍는다 — 미결 41번이 실서버에서 아홉 번 그런 형태다.
    """
    reason = worker.detect_failure_reason(
        worker.Outcome(2, "후보를 낼 수 없다: 읽을 프레임이 없다")
    )
    assert "품질 게이트" not in reason
    assert "다시" not in reason
    assert "후보를 낼 수 없다" in reason


def test_an_unknown_job_type_is_refused_not_guessed(worker, cfg, monkeypatch):
    """🔴 백엔드가 종류를 늘렸는데 워커가 낡았을 때, 추측한 쪽은 **틀린 결과를
    succeeded 로** 보고한다 — 큐는 줄고 사용자는 엉뚱한 것을 본다."""
    sent = _intercept(worker, monkeypatch, [(204, b"")])

    def never(*a, **k):
        raise AssertionError("모르는 종류를 실행했다")

    monkeypatch.setattr(worker, "run_analysis", never)
    worker.process(cfg, _detect_job(job_type="transcode"), worker.Stopper())

    assert sent[0][2]["status"] == "failed"
    assert "transcode" in sent[0][2]["failure_reason"]


@pytest.mark.parametrize("job_type", ["analyze", None])
def test_an_analyze_job_still_goes_to_the_analysis(worker, cfg, monkeypatch, job_type):
    """🔴 분석 경로가 안 바뀌는 것이 이 변경의 조건이다.

    `None` 쪽은 **이 필드가 생기기 전의 백엔드**다 — 필드가 없다고 실패하면
    배포 순서에 따라 모든 분석이 멈춘다(`video_id` 와 같은 이유로 확인한다).
    """
    _intercept(worker, monkeypatch, [(204, b"")])
    seen: list[list[str]] = []

    def fake(cmd, timeout, stopper):
        seen.append(cmd)
        path = Path(cmd[cmd.index("--result-json") + 1])
        path.write_text(json.dumps({"reports": [
            {"report_uri": "s3://supersub-ai/reports/u1/v9/report.json"},
        ]}), encoding="utf-8")
        return worker.Outcome(0, "저장: …")

    monkeypatch.setattr(worker, "run_analysis", fake)
    job = _job() if job_type is None else _job(job_type=job_type)
    worker.process(cfg, job, worker.Stopper())

    assert "analyze_s3.py" in " ".join(seen[0])
    assert "detect_subjects.py" not in " ".join(seen[0])


# 🔴 여기 있던 `test_the_detect_child_is_seen_as_busy_by_autostop` 도 위
# 「autostop 검사 셋을 지웠다」와 같은 이유로 지웠다 (2026.09.21).
