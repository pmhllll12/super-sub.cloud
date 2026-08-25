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

import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from .features import InsufficientQuality, extract_features, verify_rubric_coverage
from .judge import Judge
from .scoring import RubricError, aggregate, discover_rubrics

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


def run_pipeline(
    keypoints: np.ndarray,
    source: str,
    objects: dict[str, np.ndarray] | None = None,
    rubric_key: str | None = None,
    frames: list[np.ndarray] | None = None,
    fps: float = 12.0,
) -> dict:
    rubric = get_rubric(rubric_key)

    t0 = time.time()
    # 임팩트를 어느 사지의 어느 사건으로 정의할지는 루브릭이 선언한다.
    features = extract_features(
        keypoints, objects, rubric.impact_limb, rubric.impact_event
    )
    verify_rubric_coverage(rubric, features)
    measure_s = time.time() - t0

    t0 = time.time()
    expected = [c.id for c in rubric.applicable_criteria(features)]
    judgments = get_judge().judge_all(rubric, features)
    # 기대 목록을 넘겨, 도구 미검출로 빠진 것과 판정이 실패해 빠진 것을 구분한다.
    result = aggregate(judgments, rubric, expected_ids=expected)
    judge_s = time.time() - t0

    by_id = {c.id: c for c in rubric.criteria}
    for item in result["breakdown"]:
        item["title"] = by_id[item["criterion_id"]].title_for(item["grade"])

    return {
        "source": source,
        "frames": int(keypoints.shape[0]),
        "features": features,
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
            "validated_on": rubric.validated_on,
            "impact_limb": rubric.impact_limb,
            "impact_event": rubric.impact_event,
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
    """사용 가능한 루브릭 목록. UI의 종목 선택이 이걸 읽는다."""
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
            for r in rubrics.values()
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
def api_synthetic(rubric: str | None = None) -> JSONResponse:
    return JSONResponse(
        run_pipeline(synthetic_keypoints(), "synthetic", rubric_key=rubric)
    )


@app.post("/api/analyze/video")
async def api_video(file: UploadFile, rubric: str | None = None) -> JSONResponse:
    from .pose import extract_keypoints

    suffix = Path(file.filename or "clip.mp4").suffix or ".mp4"
    # copyfileobj로 청크 복사한다 — file.read()는 클립 전체를 한 번에 RAM에 올린다.
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp, 1024 * 1024)
        tmp_path = Path(tmp.name)

    try:
        pose = extract_keypoints(tmp_path)
        return JSONResponse(
            run_pipeline(
                pose.keypoints, file.filename or "video", pose.objects, rubric,
                frames=pose.frames, fps=pose.sampled_fps,
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
.score{font-size:2.6rem;font-weight:700;line-height:1}
.band{font-size:1.1rem;color:var(--mut);margin-left:.4rem}
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
/* 장단점 — 등급을 그대로 쓴다. 2=장점, 1=보완 필요, 0=단점. */
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

const q=()=>'?rubric='+encodeURIComponent(sel.value||'');

$('#syn').onclick=()=>call('/api/analyze/synthetic'+q(),{method:'POST'});
$('#pick').onclick=()=>$('#file').click();
$('#file').onchange=e=>{
  const f=e.target.files[0]; if(!f)return;
  const fd=new FormData(); fd.append('file',f);
  call('/api/analyze/video'+q(),{method:'POST',body:fd});
  e.target.value='';   // 같은 파일을 다시 고를 수 있게
};

// 등급을 장단점으로 옮긴다. 2=장점, 1=보완 필요, 0=단점 — 루브릭의 등급 정의
// 그대로이므로 별도 임계값을 두지 않는다. 1을 단점에 합치면 부분 득점한 항목이
// 실패로 보이므로 따로 둔다.
function prosCons(r){
  const items=r.breakdown;
  // 배점이 큰 항목이 먼저 오게 한다 — 점수는 표기하지 않지만 순서로는 남긴다.
  const bucket=g=>items.filter(b=>b.grade===g).sort((a,b)=>b.weight-a.weight);
  const pro=bucket(2), part=bucket(1), con=bucket(0);

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

function render(d){
  const r=d.result;
  // 화면에 보이는 것은 칭호와 장단점뿐이다. 총점·배점·판정 근거는
  // 선수에게 노출하지 않는다 — 루브릭이 지도자 검수 전이라 점수 자체가
  // provisional이고, 칭호가 선수 카드에 쓸 산출물이기 때문이다.
  // 개발 확인용으로 접어서 남겨 둔다.
  let h='';
  if(d.preview_video||d.preview){
    // 영상이 있으면 영상, 없으면 임팩트 정지화면으로 떨어진다.
    const media = d.preview_video
      ? `<video src="${d.preview_video}" ${d.preview?`poster="${d.preview}"`:''}
                autoplay loop muted playsinline controls></video>`
      : `<img src="${d.preview}" alt="임팩트 순간 스켈레톤">`;
    h+=`<div class="card shot">${media}
      <div class="mut">대상 선수를 따라가며 그린 골격입니다.
        빨간 테두리가 임팩트(${d.features.impact_frame}프레임) —
        에이전트가 이 자세를 근거로 채점했습니다.</div>
    </div>`;
  }
  h+=prosCons(r);

  let dev=`<div class="card">
    <div><span class="score">${r.score}</span><span class="band">점 · ${r.grade}</span>
    ${r.provisional?' <span class="mut">(provisional)</span>':''}</div>
    <div class="mut" style="margin-top:.5rem">
      기준: ${d.rubric.key} v${d.rubric.version} ·
      입력: ${d.source} · ${d.frames}프레임 ·
      측정 ${d.timing.measure_s}초 · 판정 ${d.timing.judge_s}초</div>
  </div>`;

  dev+='<div class="card"><table><tr><th>항목</th><th>등급</th><th>기여</th>'
    +'<th>근거</th></tr>';
  for(const b of r.breakdown){
    dev+=`<tr><td>${b.name}<div class="cmp">${b.title||''}</div></td>
        <td><span class="g g${b.grade}">${b.grade}</span></td>
        <td>${b.contribution}점<div class="mut">×${b.weight}</div></td>
        <td><code>${b.metric_ref}</code><div class="cmp">${b.evidence}</div></td></tr>`;
  }
  dev+='</table></div>';

  dev+='<div class="card"><table><tr><th>측정값 (결정론적 계산)</th><th></th></tr>';
  for(const [k,v] of Object.entries(d.features))
    dev+=`<tr><td><code>${k}</code></td><td>${v}</td></tr>`;
  dev+='</table></div>';

  h+=`<details class="dev"><summary>개발 확인용 상세 (총점·배점·측정값)</summary>
      ${dev}</details>`;

  out.innerHTML=h;
}
</script></main></body></html>
"""
