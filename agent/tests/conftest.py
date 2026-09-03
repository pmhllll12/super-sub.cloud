"""테스트 공통 격리.

관측 모듈은 **프로세스 전역 상태**를 둘 들고 있다 — 경고를 한 번만 내기 위한
플래그와, 기본 위치에 남기는 우회 흔적 파일이다. 둘 다 테스트 사이에 새면
곤란하다.

- 흔적 파일: 많은 테스트가 `SUPERSUB_METRICS_SINK`를 tmp로 돌리는데, 그러면
  `record()`가 **저장소의 실제 데이터 폴더**(`agent/data/observability/`)에
  흔적을 쓰게 된다. 테스트가 작업 트리를 더럽히면 안 된다.
- 한 번만 내는 플래그: 앞 테스트가 이미 켜 두면 뒤 테스트에서는 경고도 흔적도
  나오지 않아, **테스트 순서에 따라 결과가 달라진다.**
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from supersub_agent import observability as obs  # noqa: E402


@pytest.fixture(autouse=True)
def isolate_observability_globals(tmp_path, monkeypatch):
    """흔적 파일을 tmp로 돌리고, 한 번만 내는 플래그를 매 테스트 초기화한다."""
    monkeypatch.setattr(obs, "REDIRECT_LOG", tmp_path / "sink_redirects.jsonl")
    monkeypatch.setattr(obs, "_WARNED_ONCE", False)
    monkeypatch.setattr(obs, "_REDIRECT_NOTED_ONCE", False)
    yield
