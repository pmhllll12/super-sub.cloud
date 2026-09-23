"""「관리 지표」 페이지 생성기 (2026-09-23 신설).

`gen_overview.py` 는 수치를 상수로 박고 다시 뽑는 명령을 페이지에 둔다. 이 생성기는
반대로 **돌릴 때마다 저장소에서 센다** — 이 페이지가 보여 주려는 것이 「손으로 적은
숫자가 아니다」이기 때문이다.

- 세는 대상은 작업 폴더가 아니라 **HEAD 커밋**이다. 커밋하지 않은 수정은 세지 않고,
  같은 커밋에서 돌리면 같은 결과가 나온다(멱등). 기준 날짜도 「오늘」이 아니라 세는
  대상(`DATA_PATHS`)의 마지막 커밋 날짜다 — 이 페이지를 커밋해도 기준이 안 바뀐다.
- 상수로 두는 것은 `MEASURED` 하나뿐이다 — 다른 환경이 있어야 세는 값(pytest 가
  모으는 수)과 다른 영역이 잰 실측값. 잰 날짜와 근거를 함께 적는다.
- 색은 dataviz 검증기로 확인했다(2026-09-23, 바탕 #ffffff·#f4f3ef — 다크 화면에서는
  그림을 밝은 판 위에 둔다, `assets/main.scss`).
"""

import math
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# 🔴 저장소 루트를 **이 파일 위치에서** 구한다(`tools/pages/x.py` → 두 단계 위).
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "jekyll/progress/14-관리지표.markdown"
KST = timezone(timedelta(hours=9))

START, END = date(2026, 8, 20), date(2026, 10, 27)
SPRINTS = [  # 07-개발구현계획 4절 로드맵
    (1, date(2026, 8, 20), date(2026, 8, 31)),
    (2, date(2026, 9, 1), date(2026, 9, 14)),
    (3, date(2026, 9, 15), date(2026, 9, 28)),
    (4, date(2026, 9, 29), date(2026, 10, 12)),
    (5, date(2026, 10, 13), date(2026, 10, 27)),
]

PENDING = "jekyll/pages/pending.markdown"
ARCHIVE = "jekyll/pages/pending-archive.markdown"
REQS = "jekyll/chapters/05-요구사항분석.markdown"
# 이 경로들의 마지막 커밋이 페이지의 「기준」이다. 생성기·출력 페이지는 넣지 않는다.
DATA_PATHS = [PENDING, ARCHIVE, REQS, "fastapi", "agent", "www", "flutter",
              ".github/workflows", "_posts"]

PEOPLE = ["박민호", "백성검", "정어진", "정상호"]  # 팀 CLAUDE.md 의 팀 구성 순서
ZONE_OWNER = {"min": "박민호", "paik": "백성검", "jin": "정어진", "ho": "정상호"}

# 글자·격자는 gen_overview.py 와 같은 값
INK, INK2, GRID, AXIS = "#27262b", "#5c5962", "#d9d7d0", "#c3c2b7"
FONT = "font-family=\"-apple-system,BlinkMacSystemFont,'Segoe UI','Apple SD Gothic Neo','Noto Sans KR',sans-serif\""

# 미결 추이는 강조형이다 — 회색은 맥락(올라온 전체), 초록은 해소.
MUTED, DONE = "#898781", "#008300"
# 요구사항 상태는 순서형 한 색(파랑)의 진하기 + 미측정은 무채색. ✅🟡❌⚪ 는 5장 표의 기호.
STATUS = [("구현됨", "✅", "#104281"), ("부분", "🟡", "#256abf"),
          ("미구현", "❌", "#6da7ec"), ("미측정", "⚪", AXIS)]
ON_DARK = {"#104281", "#256abf"}  # 이 칸 안의 숫자는 흰 글씨

TEST_AREAS = [  # (이름, 폴더, 맡은 사람, 색 = 진행 현황의 사람 색, 경로, 테스트 선언 패턴)
    ("백엔드", "fastapi", "정어진", "#1baf7a",
     [":(glob)fastapi/tests/**/*.py"], r"^[[:space:]]*(async[[:space:]]+)?def[[:space:]]+test_"),
    ("AI 에이전트", "agent", "정상호", "#4a3aa7",
     [":(glob)agent/tests/**/*.py"], r"^[[:space:]]*(async[[:space:]]+)?def[[:space:]]+test_"),
    ("웹", "www", "백성검", "#eb6834",
     [":(glob)www/**/*.test.ts", ":(glob)www/**/*.test.tsx", ":(glob)www/**/*.spec.ts",
      ":(glob)www/**/*.spec.tsx"],
     r"^[[:space:]]*(it|test)(\.(each|skip|only|todo|concurrent))?[[:space:]]*\("),
    ("앱", "flutter", "백성검", "#eb6834",
     [":(glob)flutter/test/**/*_test.dart"], r"^[[:space:]]*(test|testWidgets)[[:space:]]*\("),
]

# 저장소에서 셀 수 없는 값 — 잰 날짜와 근거를 함께 둔다. 값이 바뀌면 여기를 고친다.
PYTEST_COLLECTED = ("1,153", "2026-09-23")  # cd fastapi && uv run pytest --collect-only -q
MEASURED = [  # (지표, 목표, 지금, 잰 날, (근거 글자, 주소))
    ("채점 재현성 — 같은 영상을 5번 넣은 총점의 표준편차", "3점 이내",
     "✅ 0.00 (4편 모두)", "2026-09-09", ("미결 항목 보관", "/pending-archive/")),
    ("분석 한 편에 걸리는 시간 — 개발 GPU(8GB)", "서비스 목표로 쓰지 않음",
     "72~125초 (100·300프레임)", "2026-09-15", ("시스템 설계 4절", "/06-시스템설계/")),
    ("추천 정확도 — Hit Rate · Recall@5", "90% (09-11 결정)",
     "⚪ 안 잼 — 측정 코드가 아직 없다", "스프린트 4 계획", ("개발 구현 계획", "/07-개발구현계획/")),
    ("조회 API 응답 P95 (요구사항 PER-003)", "500ms 이내",
     "⚪ 안 잼 — 서버가 지표를 내보내지만 모으는 곳이 없다", "—", ("요구사항 분석", "/05-요구사항분석/")),
    ("매칭 성사율 · 노쇼율 · 재사용률", "60% 이상 · 10% 이하 · 40% 이상",
     "⚪ 안 잼 — 실제 매칭이 쌓여야 잴 수 있다", "—", ("테스트 및 검증 계획", "/08-테스트및검증계획/")),
    ("채점 fps 불변성 — 프레임레이트만 바꿨을 때 등급 변동", "1등급 이내",
     "🟡 개선 중 (스프린트 3 과제, 정상호)", "—", ("개발 구현 계획", "/07-개발구현계획/")),
    ("채점 지표 타당성 — 코치급 평가와 일치율", "80% 이상",
     "⚪ 잴 수 없음 — 지도자 검수 없이 가기로 했다(09-17)", "—", ("진행 현황", "/진행-현황/")),
]


def warn(msg):
    print(f"경고: {msg}", file=sys.stderr)


def git(*args, ok=(0,)):
    r = subprocess.run(["git", "-C", str(ROOT), "-c", "core.quotepath=false", *args],
                       capture_output=True, encoding="utf-8")
    if r.returncode not in ok:
        sys.exit(f"git {' '.join(args)} 실패: {r.stderr.strip()}")
    return r.stdout


def show(path, rev="HEAD"):
    return git("show", f"{rev}:{path}")


def link(text, url):
    return "[" + text + ']({{ "' + url + '" | relative_url }})'


def kdate(iso):
    return datetime.fromisoformat(iso).astimezone(KST).date()


# --- 기준 --------------------------------------------------------------------
STAMP_HASH, STAMP_ISO = git("log", "-1", "--format=%h %cI", "HEAD", "--", *DATA_PATHS).split()
STAMP = kdate(STAMP_ISO)
DAYS = [START + timedelta(i) for i in range((STAMP - START).days + 1)]
SPRINT_NOW = next((n for n, s, e in SPRINTS if s <= STAMP <= e), None)
DAY_N, TOTAL_DAYS = (STAMP - START).days + 1, (END - START).days + 1


# --- 미결 항목 ----------------------------------------------------------------
def parse_zones(text):
    """`## <브랜치> (<이름>)` 구역 안의 `### ` 항목을 모은다. 코드 블록 안은 건너뛴다."""
    items, zone, cur, fenced = [], None, None, False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        if fenced or line.startswith("```"):
            if cur is not None:
                cur["body"].append(line)
            continue
        if line.startswith("## "):
            m = re.match(r"^## ([a-z]+) \(", line)
            zone, cur = (m.group(1) if m else None), None
            continue
        if zone and line.startswith("### "):
            cur = {"zone": zone, "title": line[4:].strip(), "body": []}
            items.append(cur)
        elif cur is not None:
            cur["body"].append(line)
    return items


def assignees(body):
    """담당 줄의 이름들. 줄은 있는데 이름이 없으면(「미정」「없음」) 빈 집합, 줄이 없으면 None."""
    for line in body:
        m = re.match(r"^- \*\*담당:?\*\*:?(.*)$", line)
        if m:
            seg = re.split(r"\*\*(?:제기|기한)", m.group(1))[0]
            return set(PEOPLE) if "전체" in seg else {p for p in PEOPLE if p in seg}
    return None


def item_key(title):
    """제목에서 번호와 ✅ 뒤(해소 표시)를 뗀 것 — 항목이 해소돼도 같은 열쇠가 된다."""
    t = re.sub(r"^\d+\.\s*", "", title.split("✅", 1)[0].strip())
    return re.sub(r"\s+", " ", t).strip()


def first_date(key, table):
    """제목 뒤에 말이 덧붙은 경우(예: 「— www」)도 같은 항목으로 본다."""
    best = table.get(key)
    for k, d in table.items():
        if k != key and len(k) >= 8 and (key.startswith(k) or k.startswith(key)):
            best = d if best is None or d < best else best
    return best


def pending_history():
    """항목 제목이 처음 생긴 날과 ✅ 가 처음 붙은 날 — 브랜치마다 기록 시점이 달라서
    날짜별 파일 사본이 아니라 커밋마다 **추가된 제목 줄**을 따라간다."""
    out = git("log", "-p", "--reverse", "--no-merges", "--no-color", "-U0",
              "--format=%x01%aI", "HEAD", "--", PENDING)
    seen, done, d = {}, {}, None
    for line in out.splitlines():
        if line.startswith("\x01"):
            d = kdate(line[1:])
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        m = re.match(r"^(?:### |## (?=\d+\.))(.+)$", line[1:])  # 구역제 이전은 `## 1.` 꼴
        if not m or not item_key(m.group(1)):
            continue
        k = item_key(m.group(1))
        seen.setdefault(k, d)
        if "✅" in m.group(1):
            done.setdefault(k, d)
    return seen, done


def pending_metrics():
    items = parse_zones(show(PENDING))
    archived = {(it["zone"], it["title"]): it for it in parse_zones(show(ARCHIVE))}
    by_title = {it["title"]: it for it in archived.values()}
    raw = git("show", f"HEAD:{PENDING}")
    if len(items) != len(re.findall(r"(?m)^### ", raw)):
        warn(f"구역 안 항목 {len(items)} ≠ `^### ` 줄 {len(re.findall(r'(?m)^### ', raw))} — 재는 명령과 어긋난다")

    zones = {z: {"n": 0, "done": 0} for z in ZONE_OWNER}
    matrix = {a: {b: 0 for b in PEOPLE} for a in PEOPLE}
    open_by = {p: 0 for p in PEOPLE}
    undecided = no_line = 0
    for it in items:
        resolved = "✅" in it["title"]
        zones[it["zone"]]["n"] += 1
        zones[it["zone"]]["done"] += resolved
        body = it["body"]
        if any(l.startswith("- **위치**: `pending-archive") for l in body):
            src = archived.get((it["zone"], it["title"])) or by_title.get(it["title"])
            body = src["body"] if src else []
        who = assignees(body)
        if not who:
            undecided += who is not None
            no_line += who is None
            continue
        for p in who:
            matrix[ZONE_OWNER[it["zone"]]][p] += 1
            if not resolved:
                open_by[p] += 1

    seen, done = pending_history()
    created_on, resolved_on, missing = [], [], 0
    for it in items:
        k = item_key(it["title"])
        c = first_date(k, seen)
        if c is None:
            missing += 1
            c = STAMP
        created_on.append(min(c, STAMP))
        if "✅" in it["title"]:
            r = first_date(k, done)
            if r is None:  # ✅ 가 병합 커밋에서만 붙었으면 제목의 날짜를 쓴다
                m = re.search(r"✅[^()]*\((\d{4})[.\-](\d{2})[.\-](\d{2})\)", it["title"])
                r = date(*map(int, m.groups())) if m else STAMP
            resolved_on.append(min(max(r, c), STAMP))
    if missing:
        warn(f"처음 생긴 날을 못 찾은 항목 {missing}개 — 기준일로 넣었다")
    created = [sum(c <= d for c in created_on) for d in DAYS]
    resolved = [sum(r <= d for r in resolved_on) for d in DAYS]
    return {"items": len(items), "done": sum(z["done"] for z in zones.values()),
            "zones": zones, "matrix": matrix, "open_by": open_by,
            "undecided": undecided, "no_line": no_line,
            "created": created, "resolved": resolved}


# --- 요구사항 ------------------------------------------------------------------
REQ_CATS = [("SFR", "기능"), ("SEC", "보안"), ("PER", "성능"), ("QUA", "품질")]


def req_metrics():
    icon = {i: name for name, i, _ in STATUS}
    status, other = {}, set()
    for line in show(REQS).splitlines():
        m = re.match(r"^\|\s*(([A-Z]{2,4})-\d{3})\s*\|", line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if m.group(2) in dict(REQ_CATS):
            if cells[-1] in icon:  # 요약표의 마지막 칸이 상태 기호
                status[m.group(1)] = icon[cells[-1]]
        else:
            other.add(m.group(1))
    ids = {m.group(1) for m in re.finditer(r"(?m)^\|\s*((?:SFR|SEC|PER|QUA)-\d{3})\s*\|", show(REQS))}
    if ids - set(status):
        warn(f"상태 기호를 못 찾은 요구사항: {sorted(ids - set(status))}")
    cats = []
    for code, name in REQ_CATS:
        mine = {k: v for k, v in status.items() if k.startswith(code + "-")}
        cats.append((name, code, {s: sorted(k for k, v in mine.items() if v == s) for s, _, _ in STATUS}))
    return {"cats": cats, "total": len(status),
            "count": {s: sum(len(c[2][s]) for c in cats) for s, _, _ in STATUS},
            "other": {p: len([o for o in other if o.startswith(p)]) for p in ("CON", "ASM")},
            "updated": git("log", "-1", "--format=%cs", "HEAD", "--", REQS).strip()}


# --- 테스트 ------------------------------------------------------------------
_count_cache = {}


def count_tests(rev, specs, pattern):
    key = (rev, tuple(specs))
    if key not in _count_cache:
        out = git("grep", "-c", "-E", pattern, rev, "--", *specs, ok=(0, 1))
        _count_cache[key] = sum(int(l.rsplit(":", 1)[1]) for l in out.splitlines() if l)
    return _count_cache[key]


def test_metrics():
    res = []
    for name, folder, owner, color, specs, pattern in TEST_AREAS:
        series = []
        for d in DAYS:
            rev = git("rev-list", "-1", f"--before={d + timedelta(1)} 00:00:00 +0900",
                      "HEAD", "--", *specs).strip()
            series.append(count_tests(rev, specs, pattern) if rev else 0)
        now = count_tests("HEAD", specs, pattern)
        if series[-1] != now:
            warn(f"{folder}: 마지막 날 {series[-1]} ≠ HEAD {now} — HEAD 값으로 맞춘다")
            series[-1] = now
        res.append({"name": name, "folder": folder, "owner": owner, "color": color,
                    "series": series, "now": now, "specs": specs, "pattern": pattern})
    return res


# --- 규모 --------------------------------------------------------------------
def scale_metrics():
    api = len(git("grep", "-h", "-o", "-E", r"@[a-z_]*router\.(get|post|put|patch|delete)\(",
                  "HEAD", "--", "fastapi/app", ok=(0, 1)).splitlines())
    m = re.search(r"CONTEXTS\s*=\s*\(([^)]*)\)", show("fastapi/tests/test_architecture.py"))
    contexts = re.findall(r"\"([a-z_]+)\"", m.group(1)) if m else []
    revs, downs, files = set(), set(), 0
    for line in git("grep", "-E", r"^(revision|down_revision)\b", "HEAD", "--",
                    "fastapi/alembic/versions", ok=(0, 1)).splitlines():
        text = line.split(":", 2)[2]
        ids = set(re.findall(r"['\"]([0-9A-Za-z_]+)['\"]", text.split("=", 1)[-1]))
        (downs if text.startswith("down_revision") else revs).update(ids)
    files = len([f for f in git("ls-tree", "-z", "--name-only", "HEAD", "fastapi/alembic/versions/").split("\0")
                 if f.endswith(".py")])
    if files != len(revs):
        warn(f"리비전 파일 {files} ≠ revision 선언 {len(revs)}")
    workflows = []  # (이름, 본문) — 이름은 파일의 `name:` 줄
    for f in sorted(git("ls-tree", "-z", "--name-only", "HEAD", ".github/workflows/").split("\0")):
        if f.endswith((".yml", ".yaml")):
            text = show(f)
            m = re.search(r"(?m)^name:\s*(.+)$", text)
            workflows.append((m.group(1).strip().strip("\"'") if m else Path(f).name, text))
    # 올릴 때마다 테스트가 도는 영역 — 이름에 「테스트」가 있고 그 폴더를 paths 로 지켜보는 워크플로
    ci = [a[0] for a in TEST_AREAS
          if any("테스트" in name and f'"{a[1]}/**"' in text for name, text in workflows)]
    posts = len([f for f in git("ls-tree", "-z", "--name-only", "HEAD", "_posts/").split("\0")
                 if f.endswith((".markdown", ".md"))])
    return {"api": api, "contexts": contexts, "revisions": files, "heads": len(revs - downs),
            "workflows": [n for n, _ in workflows], "ci": ci, "posts": posts}


# --- 그림 --------------------------------------------------------------------
def figure(svg_body, w, h, aria, caption):
    svg = (f'<svg viewBox="0 0 {w} {h}" width="{w}" role="img" aria-label="{aria}" {FONT} '
           f'style="max-width:100%;height:auto;display:block">{svg_body}</svg>')
    return ('<figure class="doc-figure">' f"{svg}"
            f'<figcaption class="doc-figure-caption">{caption}</figcaption></figure>')


def _text_w(t, size=12):
    """글자 폭 어림 — gen_overview.py 와 같은 방식에 그림 문자(✅ 등)를 더했다."""
    w = 0.0
    for ch in t:
        if "가" <= ch <= "힣":
            w += size * 0.95
        elif ord(ch) > 0x2000:
            w += size * 1.15
        elif ch in " ·":
            w += size * 0.32
        else:
            w += size * 0.58
    return w


def nice(vmax, n=4):
    """0부터 vmax 를 덮는 깔끔한 눈금(1·2·2.5·5 × 10ⁿ)."""
    raw = max(vmax, 1) / n
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    step = int(step) if step == int(step) else step
    return step * math.ceil(max(vmax, 1) / step), step


def md(d):
    return d.strftime("%m-%d")


def fig_pending(p):
    w, h, L, R, T, B = 860, 300, 52, 752, 58, 262
    n = len(DAYS)
    sx = (R - L) / max(n - 1, 1)
    top, step = nice(max(p["created"]))
    X = lambda i: round(L + i * sx, 1)
    Y = lambda v: round(B - v * (B - T) / top, 1)
    b = []
    # 범례 — 선 모양 열쇠
    for i, (label_t, c) in enumerate([("올라온 항목 (누적)", MUTED), ("해소된 항목 (누적)", DONE)]):
        x = 20 + i * 170
        b.append(f'<line x1="{x}" y1="14" x2="{x + 18}" y2="14" stroke="{c}" stroke-width="2" stroke-linecap="round"/>'
                 f'<text x="{x + 24}" y="18" font-size="12" fill="{INK}">{label_t}</text>')
    # 눈금 · 격자
    v = 0
    while v <= top:
        b.append(f'<line x1="{L}" y1="{Y(v)}" x2="{R}" y2="{Y(v)}" stroke="{AXIS if v == 0 else GRID}" stroke-width="1"/>'
                 f'<text x="{L - 8}" y="{Y(v) + 4}" text-anchor="end" font-size="10.5" fill="{INK2}">{v:,}</text>')
        v += step
    # 스프린트 경계
    xlabels = [(0, md(START))]
    for num, s, _ in SPRINTS:
        i = (s - START).days
        if 0 < i < n:
            b.append(f'<line x1="{X(i)}" y1="{T - 18}" x2="{X(i)}" y2="{B}" stroke="{GRID}" stroke-width="1"/>')
            xlabels.append((i, md(s)))
        if 0 <= i < n:
            b.append(f'<text x="{X(i) + 5}" y="{T - 8}" font-size="10.5" fill="{INK2}">스프린트 {num}</text>')
    if n - 1 - xlabels[-1][0] >= 3:
        xlabels.append((n - 1, md(STAMP)))
    for i, t in xlabels:
        anchor = "start" if i == 0 else "end" if i == n - 1 else "middle"
        b.append(f'<text x="{X(i)}" y="{B + 18}" text-anchor="{anchor}" font-size="10.5" fill="{INK2}">{t}</text>')
    # 선 · 끝점 · 끝값
    for series, c in [(p["created"], MUTED), (p["resolved"], DONE)]:
        pts = " ".join(f"{X(i)},{Y(v)}" for i, v in enumerate(series))
        b.append(f'<polyline points="{pts}" fill="none" stroke="{c}" stroke-width="2" '
                 f'stroke-linejoin="round" stroke-linecap="round"/>')
        b.append(f'<circle cx="{X(n - 1)}" cy="{Y(series[-1])}" r="4" fill="{c}" stroke="#fff" stroke-width="2"/>')
    c_end, r_end = p["created"][-1], p["resolved"][-1]
    b.append(f'<text x="{R + 10}" y="{Y(c_end) + 4}" font-size="12" font-weight="600" fill="{INK}">올라온 {c_end}</text>')
    b.append(f'<text x="{R + 10}" y="{Y(r_end) + 4}" font-size="12" font-weight="600" fill="{INK}">해소 {r_end}</text>')
    if Y(r_end) - Y(c_end) >= 36:
        b.append(f'<text x="{R + 10}" y="{(Y(c_end) + Y(r_end)) / 2 + 4}" font-size="11" fill="{INK2}">열림 {c_end - r_end}</text>')
    # 날짜 칸 — 올리면 그 날짜의 값이 뜬다
    for i, d in enumerate(DAYS):
        x0, x1 = max(L, X(i) - sx / 2), min(R, X(i) + sx / 2)
        c, r = p["created"][i], p["resolved"][i]
        b.append(f'<rect class="hit" x="{round(x0, 1)}" y="{T}" width="{round(x1 - x0, 1)}" height="{B - T}">'
                 f'<title>{md(d)} · 올라온 {c} · 해소 {r} · 열림 {c - r}</title></rect>')
    return figure(
        "".join(b), w, h,
        f"미결 항목 누적 추이. {md(START)}부터 {md(STAMP)}까지 올라온 항목은 {c_end}개, 그중 해소된 항목은 {r_end}개다.",
        f"그림 1. 날마다 올라온 항목과 해소된 항목의 누적(~{md(STAMP)}). 두 선 사이가 그날 열려 있던 항목이다. "
        "날짜에 마우스를 올리면 그날 값이 보이고, 아래 「표로 보기」에 같은 값이 있다. "
        "올라온 날은 제목이 처음 생긴 커밋, 해소된 날은 제목에 ✅ 가 처음 붙은 커밋의 날짜다.",
    )


def fig_reqs(r):
    w, lx, bx, unit, bh, gap, y0 = 860, 20, 130, 40, 22, 18, 44
    b = []
    x = lx
    for name, ic, c in STATUS:
        t = f"{ic} {name} {r['count'][name]}"
        b.append(f'<rect x="{x}" y="8" width="12" height="12" rx="3" fill="{c}"/>'
                 f'<text x="{x + 18}" y="18" font-size="12" fill="{INK}">{t}</text>')
        x += 18 + _text_w(t) + 24
    for row, (cat, code, groups) in enumerate(r["cats"]):
        y = y0 + row * (bh + gap)
        total = sum(len(v) for v in groups.values())
        b.append(f'<text x="{lx}" y="{y + 15}" font-size="12.5" fill="{INK}">{cat}</text>'
                 f'<text x="{bx - 12}" y="{y + 15}" text-anchor="end" font-size="10.5" fill="{INK2}">{code}</text>')
        segs = [(s, c, groups[s]) for s, _, c in STATUS if groups[s]]
        x = bx
        for i, (s, c, ids) in enumerate(segs):
            last = i == len(segs) - 1
            sw = len(ids) * unit - (0 if last else 2)  # 칸 사이 2px 는 바탕색 틈
            tip = f"<title>{cat} · {s} {len(ids)}개 — {', '.join(ids)}</title>"
            if last:
                d = (f"M{x},{y} h{sw - 4} q4,0 4,4 v{bh - 8} q0,4 -4,4 h-{sw - 4} z")
                b.append(f'<path d="{d}" fill="{c}">{tip}</path>')
            else:
                b.append(f'<rect x="{x}" y="{y}" width="{sw}" height="{bh}" fill="{c}">{tip}</rect>')
            fill = "#fff" if c in ON_DARK else INK
            b.append(f'<text x="{x + sw / 2}" y="{y + 15}" text-anchor="middle" font-size="11.5" '
                     f'font-weight="600" fill="{fill}" pointer-events="none">{len(ids)}</text>')
            x += len(ids) * unit
        b.append(f'<text x="{x + 8}" y="{y + 15}" font-size="12" fill="{INK2}">{total}개</text>')
    h = y0 + len(r["cats"]) * (bh + gap) - gap + 10
    c = r["count"]
    return figure(
        "".join(b), w, h,
        f"요구사항 {r['total']}개의 상태: 구현됨 {c['구현됨']}, 부분 {c['부분']}, 미구현 {c['미구현']}, 미측정 {c['미측정']}.",
        f"그림 2. 요구사항 분석(5장)의 요구사항 {r['total']}개를 분류마다 상태별로 쌓았다. "
        "칸에 마우스를 올리면 요구사항 번호가 보인다. "
        f"<strong>상태는 5장 표를 그대로 읽는다</strong> — 5장이 마지막으로 바뀐 날은 {r['updated']}이고, "
        "표가 낡으면 이 그림도 같이 낡는다.",
    )


def fig_tests(areas):
    cw, ch, gx, gy = 420, 150, 20, 20
    w, h = cw * 2 + gx, ch * 2 + gy
    n = len(DAYS)
    b = []
    for k, a in enumerate(areas):
        ox, oy = (k % 2) * (cw + gx), (k // 2) * (ch + gy)
        L, R, T, B = ox + 44, ox + cw - 66, oy + 48, oy + 122
        sx = (R - L) / max(n - 1, 1)
        top, _ = nice(max(a["series"]))  # 눈금은 0 과 위쪽 둘만 그린다
        X = lambda i: round(L + i * sx, 1)
        Y = lambda v: round(B - v * (B - T) / top, 1)
        b.append(f'<text x="{ox}" y="{oy + 14}" font-size="13" font-weight="600" fill="{INK}">{a["name"]}</text>'
                 f'<line x1="{ox}" y1="{oy + 29}" x2="{ox + 16}" y2="{oy + 29}" stroke="{a["color"]}" stroke-width="2" stroke-linecap="round"/>'
                 f'<text x="{ox + 22}" y="{oy + 33}" font-size="11" fill="{INK2}">{a["owner"]} · {a["folder"]}/</text>')
        for v in (0, top):
            b.append(f'<line x1="{L}" y1="{Y(v)}" x2="{R}" y2="{Y(v)}" stroke="{AXIS if v == 0 else GRID}" stroke-width="1"/>'
                     f'<text x="{L - 6}" y="{Y(v) + 4}" text-anchor="end" font-size="10" fill="{INK2}">{v:,}</text>')
        pts = " ".join(f"{X(i)},{Y(v)}" for i, v in enumerate(a["series"]))
        b.append(f'<polyline points="{pts}" fill="none" stroke="{a["color"]}" stroke-width="2" '
                 f'stroke-linejoin="round" stroke-linecap="round"/>'
                 f'<circle cx="{X(n - 1)}" cy="{Y(a["now"])}" r="4" fill="{a["color"]}" stroke="#fff" stroke-width="2"/>'
                 f'<text x="{R + 10}" y="{Y(a["now"]) + 4}" font-size="12" font-weight="600" fill="{INK}">{a["now"]:,}</text>')
        b.append(f'<text x="{L}" y="{B + 16}" font-size="10" fill="{INK2}">{md(START)}</text>'
                 f'<text x="{R}" y="{B + 16}" text-anchor="end" font-size="10" fill="{INK2}">{md(STAMP)}</text>')
        for i, d in enumerate(DAYS):
            x0, x1 = max(L, X(i) - sx / 2), min(R, X(i) + sx / 2)
            b.append(f'<rect class="hit" x="{round(x0, 1)}" y="{T}" width="{round(x1 - x0, 1)}" height="{B - T}">'
                     f'<title>{a["name"]} · {md(d)} · {a["series"][i]:,}개</title></rect>')
    summary = ", ".join(f"{a['name']} {a['now']:,}" for a in areas)
    return figure(
        "".join(b), w, h,
        f"영역별 테스트 수 추이(작은 그래프 네 개). {md(STAMP)} 기준 {summary}.",
        "그림 3. 영역마다 코드에 정의된 테스트 수의 추이. 색은 그 영역을 맡은 사람이다(진행 현황과 같은 색). "
        "<strong>칸마다 세로 눈금이 다르다</strong> — 영역 사이의 크기가 아니라 각 영역이 늘어 온 모양을 보는 그림이다. "
        "날짜에 마우스를 올리면 그날 값이 보인다.",
    )


# --- 표 ----------------------------------------------------------------------
def tiles(p, r, t, s):
    open_n = p["items"] - p["done"]
    c = r["count"]
    items = [
        (f"{SPRINT_NOW} / 5", "스프린트", f"개발 기간 {DAY_N}일째 · 전체 {TOTAL_DAYS}일"),
        (f"{p['done']} / {p['items']}", "미결 항목 해소", f"열린 항목 {open_n} · 해소율 {round(100 * p['done'] / p['items'])}%"),
        (f"{c['구현됨']} / {r['total']}", "요구사항 구현됨", f"부분 {c['부분']} · 미구현 {c['미구현']} · 미측정 {c['미측정']}"),
        (f"{sum(a['now'] for a in t):,}", "테스트", "코드에 정의된 수 · 영역 네 곳"),
        (f"{s['api']}", "API 엔드포인트", f"서버 단위 {len(s['contexts'])}개로 나눔"),
        (f"{s['revisions']}", "DB 스키마 변경", f"마이그레이션 이력 · 머리 {s['heads']}개"),
    ]
    cells = "".join('<div class="stat-tile">'
                    f'<div class="stat-value">{big}</div>'
                    f'<div class="stat-label">{what}</div>'
                    f'<div class="stat-note">{note}</div></div>' for big, what, note in items)
    return f'<div class="stat-tiles">{cells}</div>'


def zones_table(p):
    rows = ["| 구역 (올린 사람) | 올린 항목 | 해소 | 열림 | 해소율 |", "|---|---:|---:|---:|---:|"]
    for z, owner in ZONE_OWNER.items():
        v = p["zones"][z]
        rows.append(f"| `{z}` {owner} | {v['n']} | {v['done']} | {v['n'] - v['done']} | "
                    f"{round(100 * v['done'] / v['n']) if v['n'] else 0}% |")
    return "\n".join(rows)


def matrix_table(p):
    rows = ["| 올린 사람 ↓ · 맡은 사람 → | " + " | ".join(PEOPLE) + " |",
            "|---|" + "---:|" * len(PEOPLE)]
    for a in PEOPLE:
        rows.append(f"| {a} | " + " | ".join(
            f"**{p['matrix'][a][b]}**" if a == b else str(p["matrix"][a][b]) for b in PEOPLE) + " |")
    rows.append("| **맡은 항목 중 아직 열린 것** | " + " | ".join(str(p["open_by"][b]) for b in PEOPLE) + " |")
    return "\n".join(rows)


def unassigned_note(p):
    parts = []
    if p["undecided"]:
        parts.append(f"담당이 「미정」「없음」인 항목 {p['undecided']}개")
    if p["no_line"]:
        parts.append(f"담당 줄이 없는 항목 {p['no_line']}개")
    return f"\n{'와 '.join(parts)}는 이 표에서 뺐다.\n" if parts else ""


def changed_rows(series_list):
    """값이 바뀐 날과 첫날·마지막 날만 — 표가 날짜 수만큼 길어지지 않게."""
    keep = [0] + [i for i in range(1, len(DAYS))
                  if any(s[i] != s[i - 1] for s in series_list)]
    if keep[-1] != len(DAYS) - 1:
        keep.append(len(DAYS) - 1)
    return keep


def pending_rows(p):
    rows = ["| 날짜 | 올라온 (누적) | 해소 (누적) | 열림 |", "|---|---:|---:|---:|"]
    for i in changed_rows([p["created"], p["resolved"]]):
        c, r = p["created"][i], p["resolved"][i]
        rows.append(f"| {md(DAYS[i])} | {c} | {r} | {c - r} |")
    return "\n".join(rows)


def reqs_table(r):
    rows = ["| 분류 | " + " | ".join(f"{ic} {s}" for s, ic, _ in STATUS) + " | 합계 |",
            "|---|" + "---|" * len(STATUS) + "---:|"]
    for cat, code, g in r["cats"]:
        cells = [f"{len(g[s])}" + (f" ({', '.join(g[s])})" if g[s] else "") for s, _, _ in STATUS]
        rows.append(f"| {cat} `{code}` | " + " | ".join(cells) + f" | {sum(len(v) for v in g.values())} |")
    return "\n".join(rows)


def tests_rows(t):
    rows = ["| 날짜 | " + " | ".join(a["name"] for a in t) + " |", "|---|" + "---:|" * len(t)]
    for i in changed_rows([a["series"] for a in t]):
        rows.append(f"| {md(DAYS[i])} | " + " | ".join(f"{a['series'][i]:,}" for a in t) + " |")
    return "\n".join(rows)


def measured_table():
    rows = ["| 지표 | 목표 | 지금 | 잰 날 | 근거 |", "|---|---|---|---|---|"]
    for what, goal, now, when, (src, url) in MEASURED:
        rows.append(f"| {what} | {goal} | {now} | {when} | {link(src, url)} |")
    return "\n".join(rows)


def tests_commands(t):
    lines = []
    for a in t:
        specs = " ".join(f"'{s}'" for s in a["specs"])
        lines.append(f"git grep -c -E '{a['pattern']}' HEAD -- {specs} \\\n"
                     f"  | awk -F: '{{s+=$NF}} END{{print s}}'          # {a['name']}")
    return "\n".join(lines)


# --- 페이지 ------------------------------------------------------------------
P, Rq, Ts, Sc = pending_metrics(), req_metrics(), test_metrics(), scale_metrics()

PAGE = f"""---
layout: default
title: 관리 지표
permalink: /관리-지표/
parent: 프로젝트 관리
nav_order: 5
---

# 관리 지표

> {STAMP.isoformat()} 기준(세는 대상의 마지막 커밋 `{STAMP_HASH}`) · 스프린트 {SPRINT_NOW} 진행 중.
> **이 페이지의 숫자는 손으로 적지 않았다** — 생성기가 저장소 기록에서 센다. 절마다 「재는 법」을
> 펼치면 그 숫자를 뽑는 명령이 있다. 지나온 길은 {link("진행 현황", "/진행-현황/")}에, 일정 계획은
> {link("개발 구현 계획", "/07-개발구현계획/")} 4절에 있다.

{tiles(P, Rq, Ts, Sc)}

## 1) 요청과 결정 — 미결 항목

팀원 사이의 요청과 결정은 {link("미결 항목", "/pending/")} 한 곳으로 오간다. 올린 사람이 자기 구역에
적고, 담당과 기한을 달고, 처리하면 제목에 ✅ 를 단다. 닫힌 항목도 지우지 않는다.

{fig_pending(P)}

**누가 올리고 누가 맡았나.** 구역은 올린 사람의 것이다. 굵은 칸(대각선)은 자기 할 일로 올린 것이고,
나머지는 다른 사람에게 요청한 것이다. 한 항목에 담당이 여럿이면 칸마다 하나씩 센다.

{zones_table(P)}

{matrix_table(P)}
{unassigned_note(P)}
<details markdown="block">
<summary>표로 보기 — 날짜별 누적 (값이 바뀐 날만)</summary>

{pending_rows(P)}

</details>

<details markdown="block">
<summary>재는 법</summary>

```bash
grep -c '^### ' jekyll/pages/pending.markdown              # 올라온 항목
grep -c '^### .*✅' jekyll/pages/pending.markdown          # 그중 해소(제목에 ✅)
awk '/^## [a-z]+ \\(/{{z=$2}} /^### /{{n[z]++; if(/✅/) d[z]++}}
     END{{for(k in n) print k, n[k], d[k]+0}}' jekyll/pages/pending.markdown   # 구역별
```

날짜별 추이는 git 이력에서 항목 제목이 **처음 생긴 커밋**과 제목에 ✅ 가 **처음 붙은 커밋**을 찾아
센다(`python3 tools/pages/gen_metrics.py`). 날짜별 파일 사본으로 세지 않는 것은, 사람마다 자기
브랜치에서 일해서 같은 날의 사본이 브랜치마다 다르기 때문이다. 아카이브로 옮긴 항목은 원래
자리에 제목이 남아 있어 함께 센다.

</details>

## 2) 요구사항 — 약속한 것과 된 것

{fig_reqs(Rq)}

요구사항과 별도로 제약 {Rq["other"]["CON"]}개와 전제 {Rq["other"]["ASM"]}개를 5장에서 관리한다(상태 없음).

<details markdown="block">
<summary>표로 보기</summary>

{reqs_table(Rq)}

</details>

<details markdown="block">
<summary>재는 법</summary>

```bash
grep -E '^\\| *(SFR|SEC|PER|QUA)-[0-9]{{3}} .*\\| *(✅|🟡|❌|⚪) *\\|$' \\
  jekyll/chapters/05-요구사항분석.markdown | awk -F'|' '{{s=$(NF-1); gsub(/ /,"",s); print s}}' | sort | uniq -c
```

5장은 분류마다 요약표(상태 기호)와 상세표(확인 방법)를 둔다. 요약표만 센다 — 둘 다 세면 두 번 센다.

</details>

## 3) 테스트 — 영역마다 지키고 있는 것

{fig_tests(Ts)}

코드에 정의된 테스트를 센다. 러너가 매개변수로 늘리는 수는 넣지 않는다 — 백엔드는 pytest 가
{PYTEST_COLLECTED[0]}건을 모은다({PYTEST_COLLECTED[1]}). 올릴 때마다 GitHub Actions 가 돌리는 테스트는
{" · ".join(Sc["ci"])} {len(Sc["ci"])}곳이고, {" · ".join(a["name"] for a in Ts if a["name"] not in Sc["ci"])} 테스트는
아직 워크플로가 없다.

<details markdown="block">
<summary>표로 보기 — 날짜별 (값이 바뀐 날만)</summary>

{tests_rows(Ts)}

</details>

<details markdown="block">
<summary>재는 법</summary>

```bash
{tests_commands(Ts)}
cd fastapi && uv run pytest --collect-only -q | tail -1     # pytest 가 모으는 수
```

날짜별 추이는 그날까지의 마지막 커밋에서 같은 명령으로 센다.

</details>

## 4) 규모

| 무엇 | 지금 |
|---|---|
| API 엔드포인트 | {Sc["api"]} |
| 서버를 나눈 단위 (서로의 코드를 가져다 쓰지 못하게 검사로 막음) | {len(Sc["contexts"])} — {" · ".join(Sc["contexts"])} |
| DB 스키마 변경 (마이그레이션) | {Sc["revisions"]} · 머리 {Sc["heads"]}개 |
| 자동 워크플로 | {len(Sc["workflows"])} — {" · ".join(Sc["workflows"])} |
| 개발 로그 | {Sc["posts"]}편 |

<details markdown="block">
<summary>재는 법</summary>

```bash
grep -rhoE '@[a-z_]*router\\.(get|post|put|patch|delete)\\(' fastapi/app | wc -l   # API 엔드포인트
grep -m1 '^CONTEXTS' fastapi/tests/test_architecture.py                          # 서버 단위
ls fastapi/alembic/versions/*.py | wc -l                                         # 스키마 변경
cd fastapi && uv run alembic heads                                               # 머리
grep -h '^name:' .github/workflows/*.yml                                         # 자동 워크플로
ls _posts/ | wc -l                                                               # 개발 로그
```

</details>

## 5) 목표 대비 — 잰 것과 아직 안 잰 것

**잰 적 없는 숫자는 쓰지 않는다.** 안 잰 것은 안 쟀다고 적고, 언제 잴지를 함께 둔다.

{measured_table()}

---

[← 진행 현황]({{{{ "/진행-현황/" | relative_url }}}}) · 이 페이지는 `tools/pages/gen_metrics.py` 가 만든다 — 손으로 고치면 다음 실행 때 덮인다.

[← 목차로](/toc/)
"""

OUT.write_text(PAGE, encoding="utf-8", newline="\n")
print(f"ok — 기준 {STAMP} ({STAMP_HASH})")
