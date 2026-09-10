"""`IngestReportInteractor` — 읽고 · 파싱하고 · 저장소에 넘긴다. 미결 `jin` 27번.

DB 는 안 탄다(저장소 스텁). 실제 적재는 `tests/analysis/adapter/test_report_ingest_db.py`.
여기서는 인터랙터가 실패 경로에서 **예외를 올리는지**를 본다 — 부르는 쪽
(`FinishJobInteractor`)이 그걸 삼키는 것이 계약이라, 안 올리면 삼킬 것이 없다.
"""

from __future__ import annotations

import json
import uuid

import pytest

from app.analysis.adapter.outbound.stub.job_stub_repository import (
    StubReportIngestRepository,
    ingested_for,
    reset_ingested,
)
from app.analysis.adapter.outbound.stub.video_stub_repository import (
    FakeStorage,
    put_blob,
    reset_videos,
)
from app.analysis.application.use_cases.report_ingest_interactor import (
    IngestReportInteractor,
)
from app.analysis.application.use_cases.report_parser import UnsupportedReportSchema

_MINIMAL = {
    "schema_version": "1.0",
    "rubric": {"sport": "football", "motion": "instep_shot", "version": "0.1"},
    "judge_model": "exaone-4.0-1.2b",
    "features": {},
    "result": {"score": 50, "summary": "s", "breakdown": [], "skipped": []},
}


@pytest.fixture(autouse=True)
def _reset():
    reset_videos()
    reset_ingested()
    yield
    reset_videos()
    reset_ingested()


def test_저장소에서_읽어_파싱해_넘긴다():
    key = "reports/u/v/report.json"
    put_blob(key, json.dumps(_MINIMAL).encode())
    job_id = uuid.uuid4()

    IngestReportInteractor(FakeStorage(), StubReportIngestRepository())(job_id, key)

    parsed = ingested_for(job_id)
    assert parsed is not None and parsed.rubric_sport == "football"


def test_저장소가_없으면_RuntimeError():
    with pytest.raises(RuntimeError):
        IngestReportInteractor(None, StubReportIngestRepository())(
            uuid.uuid4(), "reports/x.json"
        )


def test_리포트_파일이_없으면_FileNotFoundError():
    with pytest.raises(FileNotFoundError):
        IngestReportInteractor(FakeStorage(), StubReportIngestRepository())(
            uuid.uuid4(), "reports/absent.json"
        )


def test_모르는_스키마는_UnsupportedReportSchema():
    key = "reports/u/v/report.json"
    put_blob(key, json.dumps({**_MINIMAL, "schema_version": "9.0"}).encode())
    with pytest.raises(UnsupportedReportSchema):
        IngestReportInteractor(FakeStorage(), StubReportIngestRepository())(
            uuid.uuid4(), key
        )
