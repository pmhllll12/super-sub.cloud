"""EC2 배포 경로 — vLLM 판정 백엔드와 S3 URI 처리.

GPU도 네트워크도 쓰지 않는다. vLLM 서버는 urllib을 가로채 흉내낸다 — 실제
서버를 띄우면 이 테스트가 EC2에서만 도는 테스트가 되어 버린다.
"""

from __future__ import annotations

import json
import sys
import urllib.error
from io import BytesIO
from pathlib import Path

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
