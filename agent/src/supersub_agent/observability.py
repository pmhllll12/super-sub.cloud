"""서비스 입력 관측 — 분석 1건마다 입력 분포 메타데이터를 남긴다.

**여기서 재는 것은 입력 노출(input exposure)과 측정 동작(measurement behavior)이지
대상 선택의 정확성(correctness)이 아니다.** 화면에 사람이 몇 명 잡혔는지는
관측할 수 있지만 그중 누가 분석 대상이어야 했는지는 라벨 없이 알 수 없다.
이 모듈의 어떤 값도 정확도의 근거로 쓰지 않는다.

원본 영상은 저장하지 않는다. 남기는 것은 집계값뿐이고 개인 식별 정보를
복제하지 않는다 — 레코드는 `analysis_id`로만 다른 도메인과 이어진다.

저장 형태를 JSONL로 둔 이유
---------------------------
백엔드(`fastapi/`)에는 아직 영상·분석 도메인이 없다(테이블은 user·card 계열
8개뿐이고 agent를 호출하지도 않는다). 지금 DB 테이블을 만들면 아무도 쓰지 않는
스키마가 생기고 `analysis_id`의 의미·FK·보존정책을 도메인 소유자 없이 확정하게
된다. 그래서 관측이 실제로 일어나는 곳(agent) 옆에 append-only JSONL로 남기고,
레코드는 **그대로 한 행으로 INSERT할 수 있는 평면 구조**로 만든다. 영상 도메인이
생기면 이 파일을 그 테이블로 옮기면 된다 (스키마 제안은
`docs/service-input-observability.md`).
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

# 표준 logging만 쓴다 — 이 저장소에 로깅 규약이 아직 없으므로 새 프레임워크를
# 들이지 않는다. 핸들러를 붙이지 않아 호스트 애플리케이션의 설정을 따른다.
_log = logging.getLogger(__name__)

# 저장 실패 경고는 프로세스당 한 번만 낸다. 프레임마다가 아니라 분석마다
# 호출되지만, 볼륨이 안 붙은 환경에서는 매 분석마다 같은 줄이 쌓인다.
_WARNED_ONCE = False

# 기록 위치. agent/data/ 는 .gitignore 대상이라 런타임 데이터가 커밋되지 않는다.
# 환경변수로 덮어쓸 수 있게 둔다 — 배포마다 볼륨이 다르다.
DEFAULT_SINK = (
    Path(__file__).resolve().parent.parent.parent
    / "data" / "observability" / "service_input_metrics.jsonl"
)

# 히스토그램에서 이 값 이상을 한 칸으로 묶는다. 표시용 상한일 뿐이고
# frames_with_ge2_person 같은 집계값은 원본 카운트로 계산한다.
HISTOGRAM_CAP = 6


def summarize_candidate_counts(counts: Sequence[int]) -> dict:
    """프레임별 후보 수 목록을 집계한다.

    counts[t] = t번째 **분석 프레임**에서 검출된 person candidate 수.
    사람이 하나도 없던 프레임도 0으로 들어와야 한다 — 빠뜨리면 분모가 어긋난다.

    multi_person_frame_ratio의 분모는 **분석 프레임 전체**다(0인 프레임 포함).
    "화면에 사람이 여럿인 상황에 얼마나 노출되는가"를 재는 값이므로, 사람이
    안 잡힌 프레임을 분모에서 빼면 노출이 과대평가된다.
    """
    n = len(counts)
    hist = Counter(int(c) for c in counts)
    ge2 = sum(v for k, v in hist.items() if k >= 2)
    return {
        "analyzed_frame_count": n,
        "frames_with_0_person": hist.get(0, 0),
        "frames_with_1_person": hist.get(1, 0),
        "frames_with_2_person": hist.get(2, 0),
        "frames_with_3plus_person": sum(v for k, v in hist.items() if k >= 3),
        "frames_with_ge2_person": ge2,
        "multi_person_frame_ratio": round(ge2 / n, 6) if n else 0.0,
        "max_candidate_count": max(hist) if hist else 0,
        # 키는 JSON에서 문자열이 된다. 상한 이상은 "6+"로 묶는다.
        "candidate_count_histogram": {
            (str(k) if k < HISTOGRAM_CAP else f"{HISTOGRAM_CAP}+"): v
            for k, v in sorted(
                Counter(
                    min(int(c), HISTOGRAM_CAP) for c in counts
                ).items()
            )
        },
    }


def build_record(
    *,
    source_fps: float,
    sampled_fps: float,
    eligible_counts: Sequence[int],
    raw_counts: Sequence[int] | None = None,
    analysis_id: str | None = None,
    rubric_key: str | None = None,
    analyzed_at: str | None = None,
) -> dict:
    """분석 1건의 관측 레코드를 만든다.

    eligible_counts — production selector가 실제로 후보로 보는 사람 수
      (검출 점수 >= pose.PERSON_ELIGIBLE_THRESHOLD). **기본 지표는 이쪽이다.**
      Phase A/B 평가가 쓴 DET_THRESHOLD와 같은 기준이라 그 결과와 비교된다.
    raw_counts — 검출기가 person으로 낸 것 전부(후처리 임계값 통과분).
      둘의 차이는 "낮은 점수로 잡힌 사람이 얼마나 있는가"를 보여준다.
    """
    rec = {
        "analysis_id": analysis_id or uuid.uuid4().hex,
        "analyzed_at": analyzed_at or datetime.now(timezone.utc).isoformat(),
        "rubric_key": rubric_key,
        "source_fps": round(float(source_fps), 4),
        "sampled_fps": round(float(sampled_fps), 4),
        **summarize_candidate_counts(eligible_counts),
    }
    if raw_counts is not None:
        raw = summarize_candidate_counts(raw_counts)
        rec["raw_frames_with_ge2_person"] = raw["frames_with_ge2_person"]
        rec["raw_multi_person_frame_ratio"] = raw["multi_person_frame_ratio"]
        rec["raw_candidate_count_histogram"] = raw["candidate_count_histogram"]
    return rec


def record(rec: dict, sink: str | os.PathLike | None = None) -> Path | None:
    """레코드 한 줄을 append한다. 실패하면 None을 돌려준다.

    **저장 실패(OSError)는 삼킨다** — 디스크가 차거나 볼륨이 안 붙었다고 해서
    사용자의 분석이 실패하면 안 된다. 다만 **프로세스당 한 번 경고를 남긴다**:
    조용히 넘기면 "서비스 입력이 0건"과 "sink가 고장남"을 구분할 수 없다.

    **직렬화 오류는 삼키지 않는다.** build_record가 내는 값은 전부 우리가
    통제하는 기본형이므로, 직렬화가 깨졌다면 그것은 운영 환경 문제가 아니라
    프로그래밍 오류다. 조용히 넘기면 관측이 영구히 비어 있는데 원인을 알 수
    없게 된다. 그래서 파일을 열기 **전에** 직렬화한다.
    """
    line = json.dumps(rec, ensure_ascii=False) + "\n"   # TypeError는 그대로 올린다

    path = Path(sink or os.environ.get("SUPERSUB_METRICS_SINK") or DEFAULT_SINK)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line)
        return path
    except OSError as exc:
        global _WARNED_ONCE
        if not _WARNED_ONCE:
            _WARNED_ONCE = True
            _log.warning(
                "서비스 입력 관측을 기록하지 못했다 (%s: %s). 분석은 계속하지만 "
                "이후 입력 분포 집계가 비어 있게 된다.", path, exc)
        return None


def load(sink: str | os.PathLike | None = None) -> list[dict]:
    """기록된 레코드를 읽는다. 깨진 줄은 건너뛴다(append 중 잘린 줄 대비)."""
    path = Path(sink or os.environ.get("SUPERSUB_METRICS_SINK") or DEFAULT_SINK)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def aggregate(records: Iterable[dict]) -> dict:
    """여러 분석 레코드를 서비스 입력 분포로 합산한다.

    clip 단위 값과 frame 단위 값을 섞지 않는다 — 프레임 비율은 프레임 총합으로,
    클립 수는 클립 단위로 센다.
    """
    recs = list(records)
    if not recs:
        return {"total_clips": 0, "total_analyzed_frames": 0}

    frames = sum(r.get("analyzed_frame_count", 0) for r in recs)
    ge2 = sum(r.get("frames_with_ge2_person", 0) for r in recs)
    hist: Counter = Counter()
    for r in recs:
        for k, v in (r.get("candidate_count_histogram") or {}).items():
            hist[k] += v

    def med(key):
        vals = sorted(r[key] for r in recs if r.get(key) is not None)
        if not vals:
            return None
        m = len(vals) // 2
        return vals[m] if len(vals) % 2 else round((vals[m - 1] + vals[m]) / 2, 4)

    return {
        "total_clips": len(recs),
        "total_analyzed_frames": frames,
        "frames_with_0_person": sum(r.get("frames_with_0_person", 0) for r in recs),
        "frames_with_1_person": sum(r.get("frames_with_1_person", 0) for r in recs),
        "frames_with_ge2_person": ge2,
        "multi_person_frame_ratio": round(ge2 / frames, 6) if frames else 0.0,
        "clips_with_any_multi_person": sum(
            1 for r in recs if r.get("frames_with_ge2_person", 0) > 0),
        "median_source_fps": med("source_fps"),
        "median_sampled_fps": med("sampled_fps"),
        "median_analyzed_frame_count": med("analyzed_frame_count"),
        "candidate_count_histogram": dict(sorted(hist.items())),
    }
