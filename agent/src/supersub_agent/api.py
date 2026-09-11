"""로컬 확인용 웹 UI.

    uv run uvicorn supersub_agent.api:app --host 0.0.0.0 --port 8000
    → http://localhost:8000

두 가지 경로를 제공한다.
  - 합성 데이터 실행: 영상 없이 [B]~[D] 구간만. 지금 검증된 범위.
  - 영상 업로드:     [A]까지 포함한 전 구간. 아직 실클립으로 검증되지 않았다.

임시 확인용이다. 인증·동시성·작업 큐가 없으므로 서비스 용도로 쓰지 않는다.
정식 구성은 비동기 잡(analysis_job) + WebSocket 진행률이다.
"""

from __future__ import annotations

import shutil
import tempfile
import re
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from .features import (
    InsufficientQuality,
    extract_features,
    frame_metrics_as_seconds,
    keypoint_quality_envelope,
    verify_rubric_coverage,
)
from .judge import Judge
from .scoring import CONFIDENT_MARGIN, RubricError, aggregate, discover_rubrics

if TYPE_CHECKING:                      # pose는 무겁다(torch·cv2) — 실행 시에는 늦게 부른다
    from .pose import PoseResult

ROOT = Path(__file__).resolve().parent.parent.parent
RUBRIC_DIR = ROOT / "rubrics"
# 기본 루브릭. 루브릭 추가는 rubrics/에 파일을 넣는 것으로 끝난다.
DEFAULT_RUBRIC = "football/instep_shot"


def get_rubric(key: str | None = None):
    """키로 루브릭을 고른다. 매 요청 적재하므로 파일을 고치면 바로 반영된다."""
    rubrics = discover_rubrics(RUBRIC_DIR)
    chosen = key or DEFAULT_RUBRIC
    if chosen not in rubrics:
        raise RubricError(
            f"루브릭 {chosen!r}가 없습니다. 사용 가능: {sorted(rubrics)}"
        )
    return rubrics[chosen]

# 업로드 임시 파일은 실디스크에 둔다.
#
# WSL2에서 /tmp는 tmpfs — 즉 RAM이다(2GB, .wslconfig의 memory 상한을 나눠 씀).
# 기본값을 그대로 두면 영상 한 편이 RAM을 두 번 먹는다: Starlette의 UploadFile이
# 1MB를 넘는 순간 TMPDIR로 스풀하고, 여기서 임시 파일로 한 벌 더 복사한다.
# 그 위에 포즈 모델과 판정 모델이 올라가면 OOM이거나 /tmp가 먼저 찬다.
# tempfile.tempdir를 여기서 바꾸면 두 경로가 한꺼번에 ext4로 내려간다.
TMP_DIR = ROOT / "data" / "tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(TMP_DIR)

app = FastAPI(title="Super-Sub 자세 분석 에이전트")

_judge: Judge | None = None


def get_judge() -> Judge:
    """판정 모델은 한 번만 적재해 재사용한다 (적재에 10초 이상 걸린다)."""
    global _judge
    if _judge is None:
        j = Judge(model_size="1.2B")
        j.load()
        _judge = j
    return _judge


def synthetic_keypoints() -> np.ndarray:
    """pose.py 출력과 같은 형식의 합성 키포인트."""
    import sys

    sys.path.insert(0, str(ROOT / "tests"))
    from test_features import build_sequence

    return build_sequence()


def impact_preview(
    frames: list[np.ndarray] | None, keypoints: np.ndarray, impact: int
) -> str | None:
    """임팩트 순간 스켈레톤 미리보기 (data URI).

    "에이전트가 이 자세를 이렇게 봤다"를 눈으로 확인시키는 것이 목적이다.
    이미 들고 있는 프레임과 키포인트로 만들므로 **추가 추론 비용이 없다.**
    합성 데이터 경로에는 프레임이 없어 None을 돌려준다.
    """
    if not frames or not (0 <= impact < len(frames)):
        return None
    from .pose import crop_to_person, draw_overlay, encode_preview

    kps = keypoints[impact]
    return encode_preview(crop_to_person(draw_overlay(frames[impact], kps), kps))


PREVIEW_DIR = ROOT / "data" / "previews"
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
PREVIEW_KEEP = 20          # 디스크가 빠듯한 환경이라 오래된 것부터 지운다
PREVIEW_NAME = re.compile(r"^[0-9a-f]{32}\.webm$")


def _prune_previews() -> None:
    files = sorted(PREVIEW_DIR.glob("*.webm"), key=lambda p: p.stat().st_mtime)
    for old in files[:-PREVIEW_KEEP]:
        old.unlink(missing_ok=True)


def tracked_preview(
    frames: list[np.ndarray] | None, keypoints: np.ndarray, impact: int, fps: float
) -> str | None:
    """대상을 따라가는 스켈레톤 영상을 만들고 조회 경로를 돌려준다."""
    if not frames:
        return None
    from .pose import render_tracked_clip

    name = f"{uuid.uuid4().hex}.webm"
    try:
        render_tracked_clip(frames, keypoints, PREVIEW_DIR / name, fps, impact=impact)
    except Exception:  # noqa: BLE001 — 미리보기 실패가 분석을 막지 않는다
        return None
    _prune_previews()
    return f"/api/preview/{name}"


@app.get("/api/preview/{name}")
def api_preview(name: str) -> FileResponse:
    # 경로 조작 방지 — 우리가 만든 이름 형식만 허용한다.
    if not PREVIEW_NAME.match(name):
        raise HTTPException(404, "없는 미리보기입니다")
    path = PREVIEW_DIR / name
    if not path.exists():
        raise HTTPException(404, "만료된 미리보기입니다")
    return FileResponse(path, media_type="video/webm")


def build_timebase(
    features: dict, frame_count: int, pose: "PoseResult | None"
) -> dict:
    """프레임 단위 값이 놓인 격자와 그 물리 시간 (미결 7번 E-3).

    **`frames: 300`도 `impact_frame: 62`도 그 자체로는 뜻이 없다.** 어느 격자에서
    솎은 것인지 모르면 초로 옮길 수 없고, 목표 fps를 실효 fps인 양 쓰면 20%
    어긋난다(`pose.read_frames`). 그래서 값과 격자를 **같은 봉투에** 넣는다.

    🔴 **모르면 지어내지 않는다.** 합성 키포인트 경로에는 소스 영상이 없어
    실효 fps가 정의되지 않는다. 그때는 `known: false`를 내고 초를 붙이지
    않는다 — 그럴듯한 기본값(예전 `fps=12.0`)을 채워 넣는 것이 이 결함이
    생긴 방식이다.

    🔴 **`features`를 바꾸지 않는다.** 여기서 만든 것은 결과 봉투의 형제
    블록이라 판정 입력이 그대로다 — 기존 평가(B-2~B-6)와 비교가 끊기지 않는다.
    """
    if pose is None:
        return {
            "known": False,
            "why": "합성 키포인트 경로 — 소스 영상이 없어 실효 fps가 정의되지 않는다",
            "frames": frame_count,
        }

    sampled_fps = float(pose.sampled_fps)
    seconds = frame_metrics_as_seconds(features, sampled_fps)
    return {
        "known": True,
        # 원본 fps와 실효 fps는 다르다. 둘 다 적어야 어디서 솎였는지 보인다.
        "source_fps": round(float(pose.source_fps), 4),
        "sampled_fps": round(sampled_fps, 4),
        "target_fps": int(pose.target_fps),
        # step = 원본 몇 장마다 한 장을 남겼는가. sampled_fps에서 되짚은 값이다.
        "step": max(1, round(float(pose.source_fps) / sampled_fps)) if sampled_fps else None,
        "frames": frame_count,
        "analyzed_seconds": round(frame_count / sampled_fps, 3),
        # 🔴 **뒷부분을 안 봤으면 그렇게 말한다.** 업로드 상한(60초)이 분석
        # 창(10초)보다 길어서 조용히 앞부분만 분석되고 있었다 — 사용자에게는
        # 아무 표시도 안 났다(미결 jin 11번). 상한을 어느 쪽에 맞출지는 아직
        # 결정 전이고, 결정과 무관하게 **잘렸다는 사실**은 봉투에 있어야 한다.
        "truncated": bool(pose.truncated),
        # 원본 길이. 컨테이너가 모르면 None이다 — 지어내지 않는다.
        "source_seconds": pose.source_seconds,
        # 무엇이 잘랐는가: "window"(보기로 한 만큼 봤다) · "memory_guard"
        # (자원 때문에 **의도한 창을 못 지켰다**). 안 잘렸으면 None.
        # 둘을 뭉뚱그리면 「10초 보기로 하고 6.7초만 봤다」가 안 보인다.
        "limited_by": pose.limited_by,
        # 프레임 단위 지표를 초로. 어느 것이 인덱스이고 어느 것이 길이인지는
        # features.FRAME_INDEX_METRICS / FRAME_DURATION_METRICS 가 선언한다.
        "seconds": seconds,
    }


def build_subject(pose: "PoseResult | None", frame_count: int) -> dict:
    """결과 봉투의 `subject` 블록. 규칙은 `pose.subject_envelope`에 하나만 둔다.

    S3 워커(`scripts/analyze_s3.py`)도 같은 함수를 쓴다 — 두 벌로 두면
    한쪽에만 필드가 늘어나 경로에 따라 봉투가 달라진다.
    """
    from .pose import subject_envelope

    return subject_envelope(pose, frame_count)


def run_pipeline(
    keypoints: np.ndarray,
    source: str,
    objects: dict[str, np.ndarray] | None = None,
    rubric_key: str | None = None,
    pose: "PoseResult | None" = None,
    fps: float = 12.0,
    swing_side: str = "auto",
) -> dict:
    """pose — 오버레이용 프레임의 **출처**. 프레임 자체가 아니다.

    프레임은 미리보기에만 쓰이고 미리보기는 판정이 끝난 뒤에 만든다. 리스트로
    받으면 측정·판정이 끝날 때까지 4K 300장을 붙들고 있게 되므로, 필요한
    시점에 load_frames()로 다시 디코딩한다. 합성 경로는 None을 준다.
    """
    rubric = get_rubric(rubric_key)

    t0 = time.time()
    # 임팩트를 어느 사지의 어느 사건으로 정의할지는 루브릭이 선언한다.
    # 스윙이 어느 쪽인지는 루브릭이 알 수 없다 — 선수마다 다르므로 올리는
    # 사람이 지정하고, 지정이 없으면 이동량으로 판별한다(팔 종목에서 약하다).
    features = extract_features(
        keypoints, objects, rubric.impact_limb, rubric.impact_event, swing_side
    )
    verify_rubric_coverage(rubric, features)
    measure_s = time.time() - t0

    t0 = time.time()
    expected = [c.id for c in rubric.applicable_criteria(features)]
    judgments = get_judge().judge_all(rubric, features)
    # 기대 목록을 넘겨, 도구 미검출로 빠진 것과 판정이 실패해 빠진 것을 구분한다.
    result = aggregate(judgments, rubric, expected_ids=expected, features=features)
    judge_s = time.time() - t0

    by_id = {c.id: c for c in rubric.criteria}
    for item in result["breakdown"]:
        criterion = by_id[item["criterion_id"]]
        # title·band는 여기서 붙이지 않는다 — `aggregate`가 이미 실었다.
        # 근거 문장에서 등급 표기를 뺀 뒤로 **그 두 필드가 등급 맥락의 유일한
        # 출처**라서, 붙이는 자리를 둘로 두면 한쪽만 고쳐진다(미결 23번).
        # 등급 구간 안쪽 여유 — 화면이 장단점을 고르는 기준이다.
        # 경계에 걸친 값은 다음 클립에서 등급이 뒤집히므로 장단점으로 올리지 않는다.
        margin = criterion.band_margin(features)
        item["margin"] = round(margin, 3)
        item["confident"] = margin >= CONFIDENT_MARGIN

    # 프레임은 **여기서** 얻는다 — 판정까지 다 끝난 뒤라 메모리에 겹치지 않는다.
    # 두 미리보기가 같은 목록을 나눠 쓰므로 디코딩은 한 번뿐이다.
    frames = pose.load_frames() if pose is not None else None

    return {
        "source": source,
        "frames": int(keypoints.shape[0]),
        "features": features,
        # 프레임 단위 값이 어느 격자 위에 있는지와, 그것이 몇 초인지 (미결 7번 E-3).
        "timebase": build_timebase(features, int(keypoints.shape[0]), pose),
        # **누구를** 분석했는지와 어떻게 골랐는지 (미결 18번).
        "subject": build_subject(pose, int(keypoints.shape[0])),
        # **얼마나 잘 잡힌 키포인트로 낸 값인가** (미결 `jin` 27번 곁가지).
        # S3 리포트와 **같은 함수**를 쓴다 — 두 벌로 두면 경로에 따라 신뢰도가
        # 달라 보인다. 여기도 `features`의 형제 블록이다.
        "keypoint_quality": keypoint_quality_envelope(
            keypoints, rubric.impact_limb, swing_side
        ),
        # 정지화면은 영상의 poster로 쓴다 — 로딩 전에도 자세가 보인다.
        "preview": impact_preview(frames, keypoints, int(features["impact_frame"])),
        "preview_video": tracked_preview(
            frames, keypoints, int(features["impact_frame"]), fps
        ),
        "result": result,
        "timing": {"measure_s": round(measure_s, 2), "judge_s": round(judge_s, 1)},
        "rubric": {
            "key": rubric.key,
            "sport": rubric.sport,
            "motion": rubric.motion,
            "label": rubric.label,
            "version": rubric.version,
            "review_required": rubric.review_required,
            # 닫아 둔 동작을 키로 직접 돌린 결과인지 드러낸다.
            "status": rubric.status,
            "validated_on": rubric.validated_on,
            "impact_limb": rubric.impact_limb,
            "impact_event": rubric.impact_event,
            "swing_side": swing_side,
            "criteria": [
                {"id": c.id, "name": c.name, "weight": c.weight,
                 "measured_by": list(c.measured_by),
                 "grades": {str(k): v for k, v in c.grades.items()}}
                for c in rubric.criteria
            ],
        },
    }


@app.get("/api/rubrics")
def api_rubrics() -> JSONResponse:
    """열려 있는 루브릭 목록. UI의 종목 선택이 이걸 읽는다.

    status가 draft인 것은 빼고 내려준다 — 지금 여는 범위는 종목당 한 동작이고
    종목은 축구 하나다(인스텝 슈팅. 2026.09.11 단일 종목 전환). 닫아 둔 동작
    (인사이드 패스)도 키를 직접 주면 분석은 되므로, 검수·실측은 UI를 열지
    않고도 계속 돌릴 수 있다.
    """
    rubrics = discover_rubrics(RUBRIC_DIR)
    return JSONResponse({
        "default": DEFAULT_RUBRIC,
        "rubrics": [
            {"key": r.key, "sport": r.sport, "motion": r.motion,
             "label": r.label,
             "version": r.version, "review_required": r.review_required,
             # 실클립으로 확인된 루브릭인지. UI가 미검증 항목에 표시를 단다.
             "validated": bool(r.validated_on), "validated_on": r.validated_on,
             "criteria_count": len(r.criteria)}
            for r in rubrics.values() if r.is_active
        ],
    })


@app.get("/api/rubric")
def api_rubric(rubric: str | None = None) -> JSONResponse:
    r = get_rubric(rubric)
    return JSONResponse({
        "key": r.key,
        "sport": r.sport, "motion": r.motion, "version": r.version,
        "review_required": r.review_required,
        "criteria": [
            {"id": c.id, "name": c.name, "weight": c.weight,
             "measured_by": list(c.measured_by),
             "grades": {str(k): v for k, v in c.grades.items()},
             "rationale": c.rationale}
            for c in r.criteria
        ],
    })


@app.post("/api/analyze/synthetic")
def api_synthetic(rubric: str | None = None, side: str = "auto") -> JSONResponse:
    return JSONResponse(
        run_pipeline(
            synthetic_keypoints(), "synthetic", rubric_key=rubric, swing_side=side
        )
    )


def parse_subject(box: str | None, at_ms: float | None):
    """질의 인자를 SubjectRequest로. 규칙은 `pose.parse_subject_spec`가 갖고 있다.

    여기서 하는 일은 **오류를 HTTP 422로 옮기는 것뿐**이다 — 무엇이 올바른
    지정인가는 CLI와 같아야 한다.
    """
    from .pose import parse_subject_spec

    try:
        return parse_subject_spec(box, at_ms)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/analyze/video")
async def api_video(
    file: UploadFile,
    rubric: str | None = None,
    side: str = "auto",
    subject_box: str | None = None,
    subject_at_ms: float | None = None,
) -> JSONResponse:
    """subject_box — 분석할 사람의 **정규화 0~1** 박스 `"x,y,w,h"`.
    subject_at_ms — 그 박스를 그린 영상 시각(밀리초).

    둘 다 **선택**이다. 없으면 지금까지의 동작 그대로이고 결과가 한 비트도
    달라지지 않는다 — `side`와 같은 규칙이다. `side`와는 **직교한다**:
    `side`는 대상을 고른 뒤 그 사람의 어느 팔·발인지고(미결 6번), 이건
    **누구인지**다.
    """
    from .pose import extract_keypoints

    subject = parse_subject(subject_box, subject_at_ms)

    suffix = Path(file.filename or "clip.mp4").suffix or ".mp4"
    # copyfileobj로 청크 복사한다 — file.read()는 클립 전체를 한 번에 RAM에 올린다.
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp, 1024 * 1024)
        tmp_path = Path(tmp.name)

    try:
        # 입력 분포 관측은 extract_keypoints 안에서 일어난다(observe 기본 True).
        # 여기서 따로 기록하면 한 분석이 두 번 남는다.
        pose = extract_keypoints(tmp_path, rubric_key=rubric, subject=subject)
        # 미리보기 렌더링(= 프레임 재디코딩)이 이 try 안에서 끝나야 한다.
        # finally가 임시 파일을 지우므로 그 뒤에는 프레임을 얻을 수 없다.
        return JSONResponse(
            run_pipeline(
                pose.keypoints, file.filename or "video", pose.objects, rubric,
                pose=pose, fps=pose.sampled_fps, swing_side=side,
            )
        )
    except InsufficientQuality as exc:
        raise HTTPException(422, f"입력 품질 미달 — {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"{type(exc).__name__}: {exc}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return PAGE


PAGE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Super-Sub 자세 분석 에이전트</title>
<style>
:root{color-scheme:light dark;--bg:#fff;--fg:#1a1a1a;--mut:#666;--line:#e0e0e0;
      --acc:#2a6df4;--warn:#b45309;--warnbg:#fef3c7}
@media(prefers-color-scheme:dark){:root{--bg:#16181c;--fg:#e8e8e8;--mut:#9aa0a6;
      --line:#2e3238;--acc:#6ea8fe;--warn:#fbbf24;--warnbg:#3a2f10}}
*{box-sizing:border-box}
body{margin:0;padding:2rem 1rem;background:var(--bg);color:var(--fg);
     font:15px/1.65 system-ui,-apple-system,"Noto Sans KR",sans-serif}
main{max-width:860px;margin:0 auto}
h1{font-size:1.4rem;margin:0 0 .3rem}
.sub{color:var(--mut);font-size:.9rem;margin-bottom:1.5rem}
.warn{background:var(--warnbg);color:var(--warn);border-radius:8px;
      padding:.8rem 1rem;font-size:.88rem;margin-bottom:1.5rem}
.row{display:flex;gap:.7rem;flex-wrap:wrap;align-items:center;margin-bottom:1.2rem}
button{background:var(--acc);color:#fff;border:0;border-radius:7px;
       padding:.6rem 1.1rem;font-size:.92rem;cursor:pointer;font-family:inherit}
button:disabled{opacity:.45;cursor:default}
button.ghost{background:transparent;color:var(--acc);border:1px solid var(--acc)}
select{background:var(--bg);color:var(--fg);border:1px solid var(--line);
       border-radius:7px;padding:.55rem .7rem;font:inherit;font-size:.9rem}
.card{border:1px solid var(--line);border-radius:10px;padding:1.1rem;margin-bottom:1rem}
table{width:100%;border-collapse:collapse;font-size:.88rem}
td,th{padding:.45rem .5rem;border-bottom:1px solid var(--line);text-align:left;
      vertical-align:top}
th{color:var(--mut);font-weight:600}
code{font:.85em ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--mut)}
.g{display:inline-block;min-width:1.6rem;padding:.1rem .4rem;border-radius:5px;
   text-align:center;font-weight:700;font-size:.82rem}
.g2{background:#16a34a22;color:#16a34a}.g1{background:#ca8a0422;color:#ca8a04}
.g0{background:#dc262622;color:#dc2626}
.cmp{color:var(--mut);font-size:.84rem;margin-top:.25rem}
.err{color:#dc2626}
.mut{color:var(--mut);font-size:.86rem}
/* 장단점 — 선정 기준은 prosCons 참고 (등급 + 경계 여유 + 배점 상위 2개). */
.pc{display:grid;grid-template-columns:1fr 1fr;gap:1.4rem}
@media(max-width:640px){.pc{grid-template-columns:1fr}}
.pc section{min-width:0}
.pc h3{margin:0 0 .7rem;font-size:.92rem;display:flex;align-items:center;gap:.4rem}
.pc ul{margin:0;padding-left:1.1rem}
.pc li{margin-bottom:.7rem}
.pc li:last-child{margin-bottom:0}
.pro h3{color:#16a34a}.part h3{color:#ca8a04}.con h3{color:#dc2626}
.span2{grid-column:1/-1;border-top:1px solid var(--line);padding-top:1.1rem}
/* 칭호 — 선수 카드에 얹을 문구라 이 화면의 주인공으로 다룬다. */
.ttl{font-weight:700;font-size:1.06rem;letter-spacing:-.02em;line-height:1.35}
.pro .ttl{color:#16a34a}.part .ttl{color:#ca8a04}.con .ttl{color:#dc2626}
.crit{color:var(--fg);opacity:.75;font-weight:600;margin-right:.4rem}
.none{color:var(--mut);font-size:.86rem;font-style:italic}
/* 오버롤 — 영상 하나의 총점과 등급. 항목 등급의 가중합이라 레이더 축 점수의
   평균이 아니다. 그 구분을 화면에도 적어 둔다(ovr .note). */
.ovr{display:grid;grid-template-columns:minmax(0,13rem) minmax(0,1fr);gap:1.2rem;
     align-items:center}
@media(max-width:640px){.ovr{grid-template-columns:1fr}}
.ovr .num{display:flex;align-items:baseline;gap:.5rem}
.ovr .letter{font-size:3.4rem;font-weight:800;line-height:1;letter-spacing:-.04em}
.ovr .pts{font-size:1.5rem;font-weight:700}
.ovr .cap{color:var(--mut);font-size:.82rem;margin-top:.5rem}
.ovr .note{color:var(--mut);font-size:.78rem;margin-top:.5rem;line-height:1.5}
.prov{display:inline-block;background:var(--warnbg);color:var(--warn);
      border-radius:999px;padding:.1rem .55rem;font-size:.72rem;font-weight:700;
      vertical-align:middle}
/* 레이더 — 단일 계열이라 색은 하나. 값은 축마다 글자로 직접 붙인다
   (색만으로 읽게 두지 않는다). 표로도 볼 수 있게 상세의 표에 같은 열이 있다. */
.radar{width:100%;height:auto;display:block;overflow:visible}
.radar .grid{fill:none;stroke:var(--line);stroke-width:1}
.radar .spoke{stroke:var(--line);stroke-width:1}
.radar .area{fill:var(--acc);fill-opacity:.16;stroke:var(--acc);stroke-width:2;
             stroke-linejoin:round}
.radar .dot{fill:var(--acc);stroke:var(--bg);stroke-width:2}
.radar .lbl{fill:var(--mut);font-size:11px}
.radar .val{fill:var(--fg);font-size:12px;font-weight:700}
.radar .ring{fill:var(--mut);font-size:9px;opacity:.7}
/* 임팩트 순간 스켈레톤 — 추가 추론 없이 이미 가진 프레임으로 만든다. */
.shot{text-align:center}
.shot img,.shot video{max-width:100%;height:auto;border-radius:8px;
  display:block;margin:0 auto .6rem;background:#000}
/* 총점·배점·측정값은 선수에게 보여줄 것이 아니라 접어 둔다. */
.dev{margin-top:1.6rem}
.dev summary{cursor:pointer;color:var(--mut);font-size:.85rem;padding:.4rem 0;
             list-style:none;user-select:none}
.dev summary::-webkit-details-marker{display:none}
.dev summary::before{content:"▸  "}
.dev[open] summary::before{content:"▾  "}
.dev summary:hover{color:var(--acc)}
</style></head><body><main>
<h1>Super-Sub 자세 분석 에이전트</h1>
<div class="sub">EXAONE 4.0 1.2B · 로컬 임시 확인용</div>

<div class="warn">
<b>검증 상태</b><br>
· 측정 → 판정 → 합산: 동작 확인됨<br>
<span id="vnote"></span><br>
· 루브릭 임계값·가중치·칭호는 지도자 검수 전 임시값이라 점수는 <code>provisional</code>입니다.
</div>

<div class="row">
  <label class="mut" for="rubric">채점 기준</label>
  <select id="rubric"></select>
  <label class="mut" for="side">스윙 측</label>
  <select id="side">
    <option value="auto">자동 판별</option>
    <option value="left">왼쪽</option>
    <option value="right">오른쪽</option>
  </select>
  <button id="syn">합성 데이터로 실행</button>
  <button class="ghost" id="pick">영상 업로드해서 실행</button>
  <input type="file" id="file" accept="video/*" hidden>
  <span class="mut" id="status"></span>
</div>

<div id="out"></div>

<script>
const $=s=>document.querySelector(s), out=$('#out'), status=$('#status');
function busy(on,msg){[...document.querySelectorAll('button')].forEach(b=>b.disabled=on);
  status.textContent=msg||''}

async function call(url,opts){
  busy(true,'판정 중… 모델 최초 적재 시 15초 정도 걸립니다');
  out.innerHTML='';
  try{
    const r=await fetch(url,opts);
    const d=await r.json();
    if(!r.ok) throw new Error(d.detail||r.statusText);
    render(d);
  }catch(e){ out.innerHTML='<div class="card err">실패: '+e.message+'</div>' }
  finally{ busy(false) }
}

// 채점 기준 목록은 rubrics/ 디렉터리에서 온다 — 루브릭 추가는 파일 추가로 끝난다.
const sel=$('#rubric'), vnote=$('#vnote');
let RUBRICS={};
async function loadRubrics(){
  try{
    const d=await (await fetch('/api/rubrics')).json();
    d.rubrics.forEach(r=>RUBRICS[r.key]=r);
    sel.innerHTML=d.rubrics.map(r=>
      `<option value="${r.key}"${r.key===d.default?' selected':''}>${
        r.label} (${r.criteria_count}항목)${r.validated?'':' · 미검증'}</option>`).join('');
    showValidation();
  }catch(e){ sel.innerHTML='<option>목록을 불러오지 못했습니다</option>' }
}
// 검증 여부는 루브릭이 스스로 선언한다(validated_on). 화면에 고정 문구로 적어
// 두면 루브릭이 늘어날 때마다 어긋난다.
function showValidation(){
  const r=RUBRICS[sel.value];
  if(!r){ vnote.textContent=''; return }
  vnote.innerHTML = r.validated
    ? `· 영상 → 키포인트: <b>${r.label}</b>은 실클립으로 검증됨 — ${r.validated_on}`
    : `· 영상 → 키포인트: <b>${r.label}</b>은 <b>실클립 미검증</b>입니다.
       파이프라인이 이 동작에서 지표를 제대로 뽑는지 확인되지 않았습니다.`;
}
sel.onchange=showValidation;
loadRubrics();

// 스윙 측(던지는 팔·차는 발)은 사람이 지정할 수 있다. 자동 판별은 이동량으로
// 고르는데 팔 종목에서 약하다 — 야구 투구 실클립에서 글러브 팔을 집었다.
const q=()=>'?rubric='+encodeURIComponent(sel.value||'')
  +'&side='+encodeURIComponent($('#side').value||'auto');

$('#syn').onclick=()=>call('/api/analyze/synthetic'+q(),{method:'POST'});
$('#pick').onclick=()=>$('#file').click();
$('#file').onchange=e=>{
  const f=e.target.files[0]; if(!f)return;
  const fd=new FormData(); fd.append('file',f);
  call('/api/analyze/video'+q(),{method:'POST',body:fd});
  e.target.value='';   // 같은 파일을 다시 고를 수 있게
};

// 장단점 선정 기준. 등급만으로 가르지 않는다.
//
//   장점 = 2등급 + 경계에서 충분히 안쪽(confident) + 배점 상위 2개
//   단점 = 0등급 + 경계에서 충분히 안쪽 + 배점 상위 2개
//   나머지(1등급, 경계에 걸친 2·0등급) = 보완 필요
//
// 경계에 걸린 값을 장단점으로 올리지 않는 이유는 그 문구가 선수 카드에 남기
// 때문이다. 밴드 경계에서 1도 차이로 등급이 갈리는 값은 다음 클립에서 뒤집힌다.
// 개수를 2개로 끊는 이유는 단점 3개가 나열되면 카드가 아니라 진단서가 돼서다.
const MAX_POINTS=2;
function prosCons(r){
  const items=r.breakdown;
  // 배점이 큰 항목이 먼저 오게 한다 — 점수는 표기하지 않지만 순서로는 남긴다.
  const bucket=g=>items.filter(b=>b.grade===g).sort((a,b)=>b.weight-a.weight);
  const solid=g=>bucket(g).filter(b=>b.confident!==false);
  const pro=solid(2).slice(0,MAX_POINTS), con=solid(0).slice(0,MAX_POINTS);
  const shown=new Set([...pro,...con].map(b=>b.criterion_id));
  const part=items.filter(b=>!shown.has(b.criterion_id))
                  .sort((a,b)=>b.weight-a.weight);

  // 칭호가 먼저, 설명이 뒤. 칭호는 루브릭의 titles에서 온다.
  const li=b=>`<li><div class="ttl">${b.title||b.name}</div>
    <div class="cmp"><span class="crit">${b.name}</span>${b.evidence||''}</div></li>`;
  const list=arr=>arr.length
    ? '<ul>'+arr.map(li).join('')+'</ul>'
    : '<div class="none">해당 항목 없음</div>';

  return `<div class="card"><div class="pc">
    <section class="pro"><h3>장점 <span class="mut">${pro.length}개</span></h3>
      ${list(pro)}</section>
    <section class="con"><h3>단점 <span class="mut">${con.length}개</span></h3>
      ${list(con)}</section>
    ${part.length?`<section class="part span2"><h3>보완 필요 <span class="mut">${
      part.length}개</span></h3>${list(part)}</section>`:''}
    ${(r.skipped||[]).length?`<div class="span2 mut">측정하지 못해 제외된 항목:
      ${r.skipped.map(s=>s.name).join(', ')} — 도구가 검출되지 않아 판정에서
      빼고 남은 항목으로 채점했습니다(0점 처리가 아닙니다).</div>`:''}
  </div></div>`;
}

// 레이더 차트. 축은 **판정된 항목**이고 축 값은 항목 점수(breakdown[].stat)다.
//
// 🔴 등급(0/1/2)을 그대로 쓰면 꼭짓점이 중심·중간·끝 세 자리에만 찍혀 모양에서
// 읽을 것이 없다. 그래서 서버가 연속 점수를 함께 낸다 — 뜻은 "이상 구간에서
// 얼마나 떨어져 있는가"이고, 등급별 점수대가 겹치지 않아(2등급 85~100 ·
// 1등급 50~85 · 0등급 0~50) 리포트의 등급과 반대로 그려지지 않는다.
//
// 축 개수는 루브릭이 정한다 — 지금 4~6개다(점프슛·투구 5, 인스텝 슈팅 6,
// 레이업 4). 오각형으로 못 박지 않는 이유다.
const RINGS=[25,50,75,100];
function radar(items){
  const N=items.length;
  if(N<3) return '';                    // 삼각형이 안 되면 표로만 읽는다
  const W=480,H=340,cx=240,cy=170,R=104;
  const at=(i,rad)=>{const a=2*Math.PI*i/N-Math.PI/2;
    return [cx+rad*Math.cos(a), cy+rad*Math.sin(a)];};
  const poly=rad=>items.map((_,i)=>at(i,rad).map(n=>n.toFixed(1)).join(',')).join(' ');

  let g=RINGS.map(p=>`<polygon class="grid" points="${poly(R*p/100)}"/>`).join('');
  g+=items.map((_,i)=>{const [x,y]=at(i,R);
    return `<line class="spoke" x1="${cx}" y1="${cy}" x2="${x.toFixed(1)}" y2="${
      y.toFixed(1)}"/>`}).join('');
  // 🔴 눈금 숫자는 그림에 안 넣는다 — 어디에 놓아도 데이터 선이 가로지른다
  //     (위쪽 축에 넣었더니 「75」를 폴리곤 변이 관통했다). 눈금의 뜻은 캡션에
  //     한 줄로 적고, 정확한 값은 축마다 붙은 숫자가 이미 싣고 있다.

  const area=`<polygon class="area" points="${
    items.map((b,i)=>at(i,R*b.stat/100).map(n=>n.toFixed(1)).join(',')).join(' ')}"/>`;
  const dots=items.map((b,i)=>{const [x,y]=at(i,R*b.stat/100);
    return `<circle class="dot" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="4"/>`
  }).join('');

  // 이름은 길다(「골반이 어깨보다 먼저 열리기」). 띄어쓰기에서 두 줄까지 접는다.
  const wrap=s=>{const w=s.split(' ');if(w.length<2||s.length<8)return [s];
    let a='';const b=[];for(const t of w){
      if(a && (a+' '+t).length>8){b.push(t)}else if(b.length){b.push(t)}
      else{a=a?a+' '+t:t}}
    return [a,b.join(' ')].filter(Boolean)};
  const labels=items.map((b,i)=>{
    const a=2*Math.PI*i/N-Math.PI/2, [x,y]=at(i,R+15);
    const cos=Math.cos(a), sin=Math.sin(a);
    const anchor=Math.abs(cos)<0.15?'middle':(cos>0?'start':'end');
    const lines=[...wrap(b.name), String(Math.round(b.stat))];
    const h=lines.length*13;
    const top = sin<-0.5 ? y-h+11 : (sin>0.5 ? y+11 : y-h/2+11);
    return `<text text-anchor="${anchor}" x="${x.toFixed(1)}" y="${top.toFixed(1)}">`
      + lines.map((t,k)=>`<tspan class="${k===lines.length-1?'val':'lbl'}"
           x="${x.toFixed(1)}" dy="${k?13:0}">${t}</tspan>`).join('')
      + '</text>';
  }).join('');

  const alt=items.map(b=>`${b.name} ${Math.round(b.stat)}점`).join(', ');
  return `<svg class="radar" viewBox="0 0 ${W} ${H}" role="img"
     aria-label="항목별 점수 레이더 차트: ${alt}"><title>항목별 점수</title>
     ${g}${area}${dots}${labels}</svg>`;
}

// 오버롤 — **영상 하나에 하나**다. 선수 한 명의 통합 등급이 아니다(여러 편을
// 어떻게 합칠지는 정해진 바 없다). 값은 서버가 낸 result.score/grade 그대로이고
// 화면이 다시 계산하지 않는다.
function overall(d){
  const r=d.result;
  const axes=r.breakdown.filter(b=>typeof b.stat==='number');
  return `<div class="card"><div class="ovr">
    <div>
      <div class="num"><span class="letter">${r.grade}</span>
        <span class="pts">${r.score}<span class="mut" style="font-size:.9rem">점</span></span></div>
      <div class="cap">${d.rubric.label} 오버롤
        ${r.provisional?'<span class="prov">잠정</span>':''}</div>
      <div class="note">항목 등급의 가중합입니다. 임계값이 지도자 검수 전이라
        <b>등급도 잠정</b>입니다.${axes.length
          ? ' 오른쪽 점수는 항목별로 이상 구간에서 얼마나 떨어졌는지를 잰 것이라, 그 평균이 총점은 아닙니다.'
          : ''}</div>
    </div>
    <div>${radar(axes)}
      ${axes.length>=3?'<div class="cap" style="text-align:center">항목별 점수 ·'
        +' 바깥 테두리가 100점, 눈금 한 칸이 25점입니다</div>':''}</div>
  </div></div>`;
}

function render(d){
  const r=d.result;
  // 오버롤(총점·등급)과 항목별 점수는 **보인다.** 예전에는 접어 두었는데,
  // 임계값이 검수 전이라는 이유였다 — 그 사실은 없어지지 않았으므로 숨기는
  // 대신 「잠정」을 붙여 함께 낸다. 배점·측정값·판정 근거는 그대로 접어 둔다.
  let h='';
  // 🔴 프레임 번호만 보여주지 않는다 (미결 7번 E-3). "62프레임"은 사람이 읽을
  // 수 있는 값이 아니고, 어느 격자인지 모르면 되짚을 수도 없다. 격자를 모르는
  // 경로(합성)에서는 초를 **지어내지 않고** 프레임만 적는다.
  const impactAt = () => {
    const f = d.features.impact_frame;
    const s = d.timebase && d.timebase.known && d.timebase.seconds
      ? d.timebase.seconds.impact_frame : null;
    return s == null ? `${f}프레임` : `${s.toFixed(2)}초 · ${f}프레임`;
  };
  if(d.preview_video||d.preview){
    // 영상이 있으면 영상, 없으면 임팩트 정지화면으로 떨어진다.
    const media = d.preview_video
      ? `<video src="${d.preview_video}" ${d.preview?`poster="${d.preview}"`:''}
                autoplay loop muted playsinline controls></video>`
      : `<img src="${d.preview}" alt="임팩트 순간 스켈레톤">`;
    h+=`<div class="card shot">${media}
      <div class="mut">대상 선수를 따라가며 그린 골격입니다.
        빨간 테두리가 임팩트(${impactAt()}) —
        에이전트가 이 자세를 근거로 채점했습니다.</div>
    </div>`;
  }
  h+=overall(d);
  h+=prosCons(r);

  let dev=`<div class="card"><div class="mut">
      기준: ${d.rubric.key} v${d.rubric.version} ·
      입력: ${d.source} · ${d.frames}프레임 ·
      측정 ${d.timing.measure_s}초 · 판정 ${d.timing.judge_s}초</div>
  </div>`;

  // 구간(band)을 등급 옆에 찍는다. 근거 문장에서 등급·구간 표기를 뺐으므로
  // (미결 23번) 「이 값이 왜 이 등급인가」를 눈으로 확인할 곳이 여기뿐이다.
  // 「점수」 열은 레이더 차트를 표로 읽는 자리이기도 하다.
  dev+='<div class="card"><table><tr><th>항목</th><th>등급</th><th>점수</th>'
    +'<th>기여</th><th>근거</th></tr>';
  for(const b of r.breakdown){
    dev+=`<tr><td>${b.name}<div class="cmp">${b.title||''}</div></td>
        <td><span class="g g${b.grade}">${b.grade}</span>
            <div class="mut">${b.band||''}</div></td>
        <td>${b.stat==null?'<span class="mut">—</span>':b.stat}</td>
        <td>${b.contribution}점<div class="mut">×${b.weight}</div></td>
        <td><code>${b.metric_ref}</code><div class="cmp">${b.evidence}</div></td></tr>`;
  }
  dev+='</table></div>';

  dev+='<div class="card"><table><tr><th>측정값 (결정론적 계산)</th><th></th></tr>';
  for(const [k,v] of Object.entries(d.features))
    dev+=`<tr><td><code>${k}</code></td><td>${v}</td></tr>`;
  dev+='</table></div>';

  h+=`<details class="dev"><summary>개발 확인용 상세 (배점·등급 구간·측정값)</summary>
      ${dev}</details>`;

  out.innerHTML=h;
}
</script></main></body></html>
"""
