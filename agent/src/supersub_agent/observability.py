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

# sink 우회 흔적도 프로세스당 한 번만 남긴다 — 같은 이유다.
_REDIRECT_NOTED_ONCE = False

# 기록 위치. agent/data/ 는 .gitignore 대상이라 런타임 데이터가 커밋되지 않는다.
# 환경변수로 덮어쓸 수 있게 둔다 — 배포마다 볼륨이 다르다.
DEFAULT_SINK = (
    Path(__file__).resolve().parent.parent.parent
    / "data" / "observability" / "service_input_metrics.jsonl"
)

# **우회 흔적.** `SUPERSUB_METRICS_SINK`로 우회했을 때 기본 위치 옆에 한 줄 남긴다.
# (명시적 `sink=` 인자는 호출부 코드에 보이므로 남기지 않는다 — `record` 참고.)
#
# 왜 별도 파일인가: 관측 레코드는 "그대로 한 행으로 INSERT할 수 있는 평면 구조"
# 여야 한다(위 모듈 설명). 표식을 같은 JSONL에 섞으면 그 계약이 깨진다.
#
# 왜 필요한가: `SUPERSUB_METRICS_SINK`로 우회하면 기본 위치는 **비어 있는 채로
# 남는다.** 그래서 "서비스 분석 0건"이 (a)진짜 0건 (b)sink 고장 (c)다른 곳에
# 기록됨 을 구분하지 못한다. 2026-08-31에 실제로 (c)를 (a)로 읽었다 —
# 개발 확인용으로 /tmp에 돌려 둔 상태에서 프로덕션 경로로 3건이 돌았다.
# 읽는 시점에 환경변수가 안 걸려 있으면 로그만으로는 되짚을 수 없으므로,
# **기본 위치에 흔적을 남겨** 나중에 읽는 사람이 알 수 있게 한다.
REDIRECT_LOG = DEFAULT_SINK.parent / "sink_redirects.jsonl"

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
    subject=None,
    subject_box_frames: int = 0,
    subject_area_jumps: int = 0,
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
    if subject is not None:
        rec.update(
            summarize_subject_selection(subject, subject_box_frames, subject_area_jumps)
        )
    return rec


# 관측 레코드에 실을 대상 선택 필드 — **전부 스칼라다.** 레코드는 "그대로 한 행으로
# INSERT할 수 있는 평면 구조"여야 한다(모듈 설명). 선택 박스 시계열 자체는 결과
# 봉투로 나가고 여기에는 넣지 않는다.
def summarize_subject_selection(
    subject, subject_box_frames: int, subject_area_jumps: int = 0
) -> dict:
    """대상을 어떻게 골랐는지를 평면 스칼라로.

    🔴 **여기서 재는 것도 정확성이 아니다.** "사람이 지정했는가", "못 맞춰
    떨어졌는가"는 라벨 없이 셀 수 있지만 "옳은 사람을 골랐는가"는 아니다.
    그래도 이 값들이 있어야 **"사람 지정이 얼마나 자주 실패하는가"** 를
    정답 없이 잰다 — 없으면 실패가 통계로 남지 않는다.
    """
    return {
        # "auto" | "specified" | "fallback"
        "subject_source": subject.source,
        "subject_specified": subject.source != "auto",
        # 지정이 있었는데 못 맞춘 비율의 분자가 된다.
        "subject_fallback": subject.source == "fallback",
        "subject_anchor_frame": subject.anchor_frame,
        "subject_anchor_iou": subject.anchor_iou,
        "subject_grid_offset_frames": subject.grid_offset_frames,
        # 찍은 시각이 분석 창 밖이었는가 (업로드 60초 대 창 10초).
        "subject_at_clamped": subject.clamped,
        "subject_continuity_breaks": subject.continuity_breaks,
        # 🔴 끊김 0이 "잘 따라갔다"는 뜻이 아니다 — 신원이 바뀔 때는 겹침이
        # 넉넉하다. 넓이가 크게 뛴 횟수가 그 의심을 센다(pose.count_area_jumps).
        "subject_area_jumps": subject_area_jumps,
        # 대상을 실제로 고른 프레임 수 — 0에 가까우면 분석 자체가 빈 것이다.
        "subject_box_frames": subject_box_frames,
    }


def resolve_sink(sink: str | os.PathLike | None = None) -> tuple[Path, str]:
    """어느 sink를 쓰는지와 **왜 그것인지**를 함께 돌려준다.

    origin은 `"argument"` · `"env"` · `"default"` 중 하나다. 경로만으로는
    우회 여부를 알 수 없어서 — 환경변수가 기본 경로와 같은 값을 담고 있을 수도
    있고, 반대로 인자로 기본과 다른 경로를 줄 수도 있다 — 출처를 따로 돌려준다.

    쓰는 쪽(`record`)·읽는 쪽(`load`)·보고 스크립트가 **같은 해석**을 쓰게
    한 곳에 모아 둔다. 세 곳에 같은 `sink or env or DEFAULT` 를 복사해 두면
    하나만 고쳐졌을 때 "어디에 썼는지"와 "어디를 읽는지"가 갈린다.
    """
    if sink is not None:
        return Path(sink), "argument"
    env = os.environ.get("SUPERSUB_METRICS_SINK")
    if env:
        return Path(env), "env"
    return DEFAULT_SINK, "default"


def _note_redirect(path: Path, origin: str) -> None:
    """기본 위치에 "여기가 아니라 저기에 썼다"는 흔적을 남긴다 (프로세스당 1회).

    최선 노력이다 — 실패해도 분석을 막지 않는다. 기본 위치가 쓰기 불가라서
    우회한 경우에는 흔적도 못 남기는데, 그때는 경고 로그가 유일한 단서다.
    """
    global _REDIRECT_NOTED_ONCE
    if _REDIRECT_NOTED_ONCE:
        return
    _REDIRECT_NOTED_ONCE = True

    _log.warning(
        "서비스 입력 관측을 기본 위치가 아닌 곳에 기록한다 (%s, 출처 %s). "
        "기본 위치(%s)는 비어 있게 되므로 '분석 0건'으로 읽히지 않도록 "
        "%s 에 흔적을 남긴다.", path, origin, DEFAULT_SINK, REDIRECT_LOG)

    line = json.dumps({
        "at": datetime.now(timezone.utc).isoformat(),
        "sink": str(path),
        "origin": origin,
        "pid": os.getpid(),
    }, ensure_ascii=False) + "\n"
    try:
        REDIRECT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(REDIRECT_LOG, "a", encoding="utf-8") as fh:
            fh.write(line)
    except OSError as exc:
        _log.warning("우회 흔적을 남기지 못했다 (%s: %s).", REDIRECT_LOG, exc)


def load_redirects() -> list[dict]:
    """기본 위치에 남은 우회 흔적. 없으면 빈 목록이다.

    "분석 0건"을 읽었을 때 **다른 곳에 기록됐을 가능성**을 되짚는 데 쓴다.
    """
    if not REDIRECT_LOG.exists():
        return []
    out = []
    for line in REDIRECT_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def record(rec: dict, sink: str | os.PathLike | None = None) -> Path | None:
    """레코드 한 줄을 append한다. 실패하면 None을 돌려준다.

    **저장 실패(OSError)는 삼킨다** — 디스크가 차거나 볼륨이 안 붙었다고 해서
    사용자의 분석이 실패하면 안 된다. 다만 **프로세스당 한 번 경고를 남긴다**:
    조용히 넘기면 "서비스 입력이 0건"과 "sink가 고장남"을 구분할 수 없다.

    **환경변수로 sink를 우회하면 기본 위치에 흔적을 남긴다** (프로세스당 1회,
    `REDIRECT_LOG`). 우회하면 기본 위치가 비어 있게 되어 "분석 0건"이 진짜
    0건인지 다른 곳에 기록된 것인지 구분되지 않는다 — 2026-08-31에 실제로
    혼동했다. 명시적 `sink=` 인자는 호출부에 보이므로 흔적을 남기지 않는다.

    **직렬화 오류는 삼키지 않는다.** build_record가 내는 값은 전부 우리가
    통제하는 기본형이므로, 직렬화가 깨졌다면 그것은 운영 환경 문제가 아니라
    프로그래밍 오류다. 조용히 넘기면 관측이 영구히 비어 있는데 원인을 알 수
    없게 된다. 그래서 파일을 열기 **전에** 직렬화한다.
    """
    line = json.dumps(rec, ensure_ascii=False) + "\n"   # TypeError는 그대로 올린다

    path, origin = resolve_sink(sink)
    # **환경변수 우회만 흔적을 남긴다.** 명시적 `sink=` 인자는 호출부 코드에
    # 그대로 보이는 의도적 선택이라 나중에 되짚을 수 있다. 사고를 낸 것은
    # 눈에 안 보이고 읽는 시점엔 이미 사라져 있는 환경변수 쪽이다.
    # 인자까지 흔적을 남기면 테스트·도구가 부를 때마다 쌓여 신호가 죽는다.
    if origin == "env":
        _note_redirect(path, origin)
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
    path, _ = resolve_sink(sink)
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
