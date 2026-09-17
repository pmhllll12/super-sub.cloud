"""`/metrics` 가 Prometheus 형식으로 요청 지연 히스토그램을 낸다.

PER-001(목표 소요 시간)·PER-003(P95 500ms)를 검증하려면 요청 지연을 **모아서
분위수**로 봐야 하는데, 지금까지 그걸 낼 자리가 없었다. `prometheus-fastapi-
instrumentator` 가 `app/main.py` 에서 `/metrics` 를 연다. P95 자체는 Prometheus
에서 `histogram_quantile(0.95, ...)` 로 뽑으므로 앱 코드에는 없다.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_metrics_는_prometheus_형식으로_응답한다():
    client = TestClient(app)
    # 히스토그램에 표본이 생기도록 한 번 친다.
    client.get("/health")

    res = client.get("/metrics")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/plain")

    body = res.text
    # 요청 수 카운터 + 지연 히스토그램(P95 의 재료).
    assert "http_requests_total" in body
    assert "http_request_duration_seconds_bucket" in body


def test_metrics_는_openapi_문서에_없다():
    """운영용 엔드포인트라 스키마(공격 표면)에 넣지 않는다."""
    assert "/metrics" not in app.openapi()["paths"]
