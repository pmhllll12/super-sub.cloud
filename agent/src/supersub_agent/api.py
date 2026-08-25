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
import time
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from .features import InsufficientQuality, extract_features, verify_rubric_coverage
from .judge import Judge
from .scoring import aggregate, load_rubric

ROOT = Path(__file__).resolve().parent.parent.parent
RUBRIC_PATH = ROOT / "rubrics" / "football_instep_shot.yaml"

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


def run_pipeline(keypoints: np.ndarray, source: str) -> dict:
    rubric = load_rubric(RUBRIC_PATH)

    t0 = time.time()
    features = extract_features(keypoints)
    verify_rubric_coverage(rubric, features)
    measure_s = time.time() - t0

    t0 = time.time()
    judgments = get_judge().judge_all(rubric, features)
    result = aggregate(judgments, rubric)
    judge_s = time.time() - t0

    by_id = {c.id: c for c in rubric.criteria}
    for item in result["breakdown"]:
        item["title"] = by_id[item["criterion_id"]].title_for(item["grade"])

    return {
        "source": source,
        "frames": int(keypoints.shape[0]),
        "features": features,
        "result": result,
        "timing": {"measure_s": round(measure_s, 2), "judge_s": round(judge_s, 1)},
        "rubric": {
            "sport": rubric.sport,
            "motion": rubric.motion,
            "version": rubric.version,
            "review_required": rubric.review_required,
            "criteria": [
                {"id": c.id, "name": c.name, "weight": c.weight,
                 "measured_by": list(c.measured_by),
                 "grades": {str(k): v for k, v in c.grades.items()}}
                for c in rubric.criteria
            ],
        },
    }


@app.get("/api/rubric")
def api_rubric() -> JSONResponse:
    r = load_rubric(RUBRIC_PATH)
    return JSONResponse({
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
def api_synthetic() -> JSONResponse:
    return JSONResponse(run_pipeline(synthetic_keypoints(), "synthetic"))


@app.post("/api/analyze/video")
async def api_video(file: UploadFile) -> JSONResponse:
    from .pose import extract_keypoints

    suffix = Path(file.filename or "clip.mp4").suffix or ".mp4"
    # copyfileobj로 청크 복사한다 — file.read()는 클립 전체를 한 번에 RAM에 올린다.
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp, 1024 * 1024)
        tmp_path = Path(tmp.name)

    try:
        pose = extract_keypoints(tmp_path)
        return JSONResponse(run_pipeline(pose.keypoints, file.filename or "video"))
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
<div class="sub">축구 인스텝 슈팅 · EXAONE 4.0 1.2B · 로컬 임시 확인용</div>

<div class="warn">
<b>검증 상태</b><br>
· 측정 → 판정 → 합산: 동작 확인됨<br>
· 영상 → 키포인트: <b>실제 클립으로 검증되지 않음</b>. 업로드하면 그 구간이 처음 실행됩니다.<br>
· 루브릭 각도 임계값은 지도자 검수 전 임시값이라 점수는 <code>provisional</code>입니다.
</div>

<div class="row">
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

$('#syn').onclick=()=>call('/api/analyze/synthetic',{method:'POST'});
$('#pick').onclick=()=>$('#file').click();
$('#file').onchange=e=>{
  const f=e.target.files[0]; if(!f)return;
  const fd=new FormData(); fd.append('file',f);
  call('/api/analyze/video',{method:'POST',body:fd});
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
  </div></div>`;
}

function render(d){
  const r=d.result;
  // 화면에 보이는 것은 칭호와 장단점뿐이다. 총점·배점·판정 근거는
  // 선수에게 노출하지 않는다 — 루브릭이 지도자 검수 전이라 점수 자체가
  // provisional이고, 칭호가 선수 카드에 쓸 산출물이기 때문이다.
  // 개발 확인용으로 접어서 남겨 둔다.
  let h=prosCons(r);

  let dev=`<div class="card">
    <div><span class="score">${r.score}</span><span class="band">점 · ${r.grade}</span>
    ${r.provisional?' <span class="mut">(provisional)</span>':''}</div>
    <div class="mut" style="margin-top:.5rem">
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
