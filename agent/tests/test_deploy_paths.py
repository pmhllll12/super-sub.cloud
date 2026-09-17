"""EC2 배포 경로 — vLLM 판정 백엔드와 S3 URI 처리.

GPU도 네트워크도 쓰지 않는다. vLLM 서버는 urllib을 가로채 흉내낸다 — 실제
서버를 띄우면 이 테스트가 EC2에서만 도는 테스트가 되어 버린다.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import urllib.error
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from supersub_agent import storage  # noqa: E402
from supersub_agent.judge import VLLM_URL_ENV, Judge, extract_json  # noqa: E402


# -- URI 처리 ------------------------------------------------------------

def test_parse_s3_uri_splits_bucket_and_key():
    assert storage.parse_s3_uri("s3://bkt/videos/a.mp4") == ("bkt", "videos/a.mp4")


@pytest.mark.parametrize(
    "bad", ["https://bkt/a.mp4", "s3://bkt", "s3://bkt/", "/local/a.mp4"]
)
def test_parse_s3_uri_rejects_non_objects(bad):
    """버킷만 있는 URI를 통과시키면 boto3가 알아보기 어려운 오류를 낸다."""
    with pytest.raises(ValueError):
        storage.parse_s3_uri(bad)


def test_join_uri_does_not_double_slashes():
    assert storage.join_uri("s3://bkt/reports/", "clip", "a.json") == (
        "s3://bkt/reports/clip/a.json"
    )


# -- JSON 추출 (두 백엔드 공용) --------------------------------------------

def test_extract_json_takes_the_object_out_of_chatter():
    """모델이 문장을 덧붙여도 JSON만 꺼낸다 — 로컬·vLLM 경로가 함께 쓴다."""
    text = '설명입니다. {"evidence": "무릎각 141.7도", "metric_ref": "x"} 끝.'
    assert extract_json(text) == {"evidence": "무릎각 141.7도", "metric_ref": "x"}


@pytest.mark.parametrize("text", ["JSON이 없다", "{깨진 json", "[1, 2, 3]"])
def test_extract_json_returns_none_when_unusable(text):
    assert extract_json(text) is None


# -- vLLM 백엔드 ----------------------------------------------------------

class _FakeResponse(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def _serve(monkeypatch, models: list[str], content: str = "", *, http_error=None):
    """urllib을 가로채 vLLM 서버를 흉내낸다. 보낸 요청 본문을 모아 돌려준다."""
    sent: list[dict] = []

    def fake_urlopen(req, timeout=None):
        url = req if isinstance(req, str) else req.full_url
        if url.endswith("/v1/models"):
            body = {"data": [{"id": m} for m in models]}
            return _FakeResponse(json.dumps(body).encode())
        sent.append(json.loads(req.data.decode()))
        if http_error is not None and len(sent) == 1:
            raise urllib.error.HTTPError(url, http_error, "nope", {}, None)
        payload = {"choices": [{"message": {"content": content}}]}
        return _FakeResponse(json.dumps(payload).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    return sent


def test_base_url_comes_from_the_environment(monkeypatch):
    """환경변수만으로 백엔드가 바뀐다 — api.py·analyze.py를 고치지 않는다."""
    monkeypatch.delenv(VLLM_URL_ENV, raising=False)
    assert Judge().base_url is None
    assert Judge().backend == "transformers"

    monkeypatch.setenv(VLLM_URL_ENV, "http://127.0.0.1:8000")
    assert Judge().base_url == "http://127.0.0.1:8000"
    assert Judge().backend == "vllm"


def test_load_rejects_a_server_serving_another_model(monkeypatch):
    """--served-model-name이 어긋나면 load()에서 걸린다.

    포즈 추출에 수십 초를 쓴 뒤 404를 보는 것보다, 시작하자마자 이름이 다르다고
    말해 주는 편이 낫다.
    """
    _serve(monkeypatch, models=["/opt/supersub/models/exaone-4.0-1.2b"])
    judge = Judge(base_url="http://127.0.0.1:8000")

    with pytest.raises(RuntimeError, match="서빙하지 않는다"):
        judge.load()


def test_load_reports_an_unreachable_server(monkeypatch):
    def boom(req, timeout=None):
        raise urllib.error.URLError("Connection refused")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    with pytest.raises(RuntimeError, match="연결할 수 없다"):
        Judge(base_url="http://127.0.0.1:8000").load()


def test_remote_judging_asks_for_a_schema_and_greedy_decoding(monkeypatch):
    sent = _serve(
        monkeypatch,
        models=[Judge().model_id],
        content='{"evidence": "무릎각 141.7도로 하단이다", "metric_ref": "knee"}',
    )
    judge = Judge(base_url="http://127.0.0.1:8000")
    judge.load()
    out = judge._generate_remote([{"role": "user", "content": "x"}])

    assert out["evidence"].startswith("무릎각")
    assert sent[0]["temperature"] == 0.0, "판정은 재현되어야 한다"
    assert "guided_json" in sent[0], "스키마 강제를 먼저 시도한다"


def test_remote_judging_falls_back_when_schema_is_refused(monkeypatch):
    """vLLM 버전에 따라 guided_json을 모른다. 로컬과 같은 규약으로 내려간다."""
    sent = _serve(
        monkeypatch,
        models=[Judge().model_id],
        content='좋습니다 {"evidence": "설명", "metric_ref": "knee"}',
        http_error=400,
    )
    judge = Judge(base_url="http://127.0.0.1:8000")
    judge.load()
    out = judge._generate_remote([{"role": "user", "content": "x"}])

    assert out["metric_ref"] == "knee"
    assert len(sent) == 2 and "guided_json" not in sent[1]


def test_remote_unload_does_not_touch_torch(monkeypatch):
    """서버는 우리 것이 아니다 — unload가 GPU를 건드리면 안 된다.

    analyze.py가 finally에서 unload를 부르는데, 원격 백엔드에서 torch를
    import하면 CPU 전용 환경에서 그때 터진다.
    """
    _serve(monkeypatch, models=[Judge().model_id])
    judge = Judge(base_url="http://127.0.0.1:8000")
    judge.load()

    monkeypatch.setitem(sys.modules, "torch", None)  # import하면 실패한다
    judge.unload()
    assert judge.backend == "vllm"


def test_judging_without_load_still_fails_loudly(monkeypatch):
    monkeypatch.setenv(VLLM_URL_ENV, "http://127.0.0.1:8000")
    with pytest.raises(RuntimeError, match="load"):
        Judge().judge_criterion(object(), {})


# -- 미리보기 (analyze_s3.py) ---------------------------------------------

def _load_analyze_s3():
    spec = importlib.util.spec_from_file_location(
        "analyze_s3", Path(__file__).resolve().parent.parent / "scripts" / "analyze_s3.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["analyze_s3"] = mod
    spec.loader.exec_module(mod)
    return mod


def _fake_pose(tmp_path, n=8, w=96, h=128):
    """실제 영상 파일 + 지어낸 키포인트로 PoseResult를 만든다.

    load_frames()가 파일을 다시 디코딩하므로 진짜 파일이어야 한다 — 그 재디코딩이
    미리보기 경로의 핵심이라 흉내내면 검사할 것이 없어진다.
    """
    from supersub_agent.pose import PoseResult

    path = tmp_path / "clip.mp4"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (w, h))
    assert writer.isOpened()
    for _ in range(n):
        writer.write(np.full((h, w, 3), 90, dtype=np.uint8))
    writer.release()

    kps = np.zeros((n, 17, 3), dtype=np.float64)
    kps[:, :, 0] = np.linspace(20, w - 20, 17)
    kps[:, :, 1] = np.linspace(20, h - 20, 17)
    kps[:, :, 2] = 0.9
    return PoseResult(
        keypoints=kps, source_fps=10.0, sampled_fps=10.0,
        video_path=str(path), target_fps=10,
    )


def test_build_previews_makes_both_artifacts(tmp_path):
    """임팩트 정지화면과 추적 영상 둘 다 나온다 — 그림이 EC2 산출물에 실린다."""
    a3 = _load_analyze_s3()
    pose = _fake_pose(tmp_path)
    out = a3.build_previews(pose, impact=3, work=tmp_path)

    assert set(out) == {"impact_image", "tracked_video"}
    assert out["impact_image"].stat().st_size > 0
    assert out["tracked_video"].stat().st_size > 0


def test_build_previews_returns_nothing_without_frames(tmp_path):
    """합성 키포인트 경로에는 영상이 없다 — 조용히 빈 결과를 돌려준다."""
    from supersub_agent.pose import PoseResult

    a3 = _load_analyze_s3()
    pose = PoseResult(
        keypoints=np.zeros((4, 17, 3)), source_fps=10.0, sampled_fps=10.0,
        video_path=None,
    )
    assert a3.build_previews(pose, impact=1, work=tmp_path) == {}


def test_preview_failure_does_not_break_the_analysis(tmp_path, monkeypatch):
    """렌더링이 실패해도 측정·판정은 유효하다 — 미리보기는 검수 편의다."""
    a3 = _load_analyze_s3()
    pose = _fake_pose(tmp_path)

    def boom(*a, **k):
        raise RuntimeError("인코더를 열 수 없습니다")

    monkeypatch.setattr(a3, "render_tracked_clip", boom)
    out = a3.build_previews(pose, impact=3, work=tmp_path)

    assert "tracked_video" not in out
    assert "impact_image" in out, "먼저 만들어진 것은 남는다"


# -- 판정 동시 호출 (2026-09-15) -------------------------------------------
#
# 항목당 2~3초가 순차로 쌓여 EC2 판정이 17초였다. 원격일 때만 동시에 던진다.
# 아래 셋이 그 변경이 지켜야 할 성질이다.

class _Rubric:
    sport = "football"

    def __init__(self, criteria):
        self._criteria = criteria

    def applicable_criteria(self, features):
        return tuple(self._criteria)


class _Criterion:
    """프롬프트를 만드는 데 필요한 만큼만 흉내낸다 (build_prompt 참고)."""

    def __init__(self, cid, grade):
        self.id = cid
        self.name = "디딤발 무릎 굽히기"
        self.rationale = ""
        self.measured_by = ("knee",)
        self.band_metric = "knee"
        self.grades = {0: "거의 안 굽음", 1: "조금 굽음", 2: "충분히 굽음"}
        self.anchors = ()
        self._grade = grade

    def grade_for(self, features):
        return self._grade

    # 🔴 **일부러 빈 값을 돌려준다** (미결 23번 가-2). `build_prompt` 는
    #    `grades_plain` 이 없으면 `grades` 로 떨어지는데, 이 스텁이 그
    #    **폴백 경로**를 지나는 쪽이다. 여기에 문구를 채워 넣으면 폴백이
    #    실제로 도는지 아무도 안 보게 된다 — 이 배선 검사가 보는 것은
    #    프롬프트 문구가 아니라 **동시성과 순서**다.
    def plain_for(self, grade, value=None):
        return ""

    def plain_all(self, grade):
        return ""


def _judge_with_fake_server(monkeypatch, *, delay: float = 0.0):
    """모든 항목이 같은 문장을 받는 vLLM. 지연을 주면 동시성이 시간에 드러난다."""
    import time as _t

    def fake_urlopen(req, timeout=None):
        url = req if isinstance(req, str) else req.full_url
        if url.endswith("/v1/models"):
            body = {"data": [{"id": Judge().model_id}]}
            return _FakeResponse(json.dumps(body).encode())
        _t.sleep(delay)
        payload = {"choices": [{"message": {"content":
                   '{"evidence": "무릎이 덜 굽었다", "metric_ref": "knee"}'}}]}
        return _FakeResponse(json.dumps(payload).encode())

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    judge = Judge(base_url="http://127.0.0.1:8000")
    judge.load()
    return judge


def test_remote_judging_runs_the_criteria_at_the_same_time(monkeypatch):
    """6항목이 순차로 쌓이지 않는다 — 가장 느린 하나로 줄어든다."""
    import time as _t

    judge = _judge_with_fake_server(monkeypatch, delay=0.2)
    rubric = _Rubric([_Criterion(f"c{i}", i % 3) for i in range(6)])

    t0 = _t.time()
    out = judge.judge_all(rubric, {"knee": 141.7})
    elapsed = _t.time() - t0

    assert len(out) == 6
    assert elapsed < 0.2 * 6 / 2, f"순차로 돌고 있다 ({elapsed:.2f}초)"


def test_concurrency_cannot_move_a_grade(monkeypatch):
    """🔴 등급은 코드가 정한 값 그대로다 — 모델도, 실행 순서도 못 바꾼다.

    이것이 이 변경을 안전하게 만드는 성질이다. 깨지면 같은 영상의 점수가
    동시 실행 여부에 따라 달라진다.
    """
    judge = _judge_with_fake_server(monkeypatch)
    grades = {f"c{i}": i % 3 for i in range(6)}
    rubric = _Rubric([_Criterion(cid, g) for cid, g in grades.items()])

    out = judge.judge_all(rubric, {"knee": 141.7})

    assert {cid: j["grade"] for cid, j in out.items()} == grades


def test_the_report_keeps_the_rubric_order(monkeypatch):
    """먼저 끝난 항목이 앞으로 오지 않는다 — 화면의 항목 순서가 흔들린다."""
    judge = _judge_with_fake_server(monkeypatch)
    ids = [f"c{i}" for i in range(6)]
    rubric = _Rubric([_Criterion(cid, 1) for cid in ids])

    assert list(judge.judge_all(rubric, {"knee": 1.0})) == ids


def test_local_judging_stays_sequential(monkeypatch):
    """로컬은 GPU에 모델이 하나다 — 동시에 불러 봐야 얻을 것이 없고,
    outlines·transformers 가 여러 스레드에서 안전하다는 보장도 없다."""
    monkeypatch.delenv(VLLM_URL_ENV, raising=False)
    judge = Judge()
    judge._model = object()          # load() 를 지나온 것처럼 보이게만 한다
    seen: list[str] = []

    def fake_one(criterion, features, sport=""):
        seen.append(criterion.id)
        return {"grade": 1, "evidence": "", "metric_ref": "knee"}

    monkeypatch.setattr(judge, "judge_criterion", fake_one)
    rubric = _Rubric([_Criterion(f"c{i}", 1) for i in range(4)])
    judge.judge_all(rubric, {})

    assert seen == ["c0", "c1", "c2", "c3"]
