"""제안서 장(章) 안에 그림을 끼워 넣는 생성기 (2026-09-23 신설).

글 비중이 높은 장에 그림을 더한다(사용자 요청). 그림마다 **그 페이지의 표·본문을 원본으로
읽어** 그리므로, 표를 고친 뒤 이 스크립트를 다시 돌리면 그림이 따라온다. 표는 그대로 남아
그림의 「표로 보기」 역할을 한다.

| 그림 | 넣는 곳 | 원본 |
|---|---|---|
| 1-1 비전에서 목표까지 | 1장 「비전」 앞 | 1장 비전·미션·핵심 가치 표·프로젝트 목표 (2026-09-29) |
| 2-1 문제에서 해법까지 | 2장 「시사점」 끝 | 2장 문제 제목·시사점 + 3장 기능군 표. 선은 `PROBLEM_TASK`·`TASK_FEATURE` 상수 (2026-09-29) |
| 3-1 서비스 흐름 | 3장 1)절 끝 | 3장 1)·2)절 본문 — 원본 표가 없어 아래 `FLOW` 상수 |
| 3-2 측정과 판단의 분리 | 3장 「처리 흐름」 끝 | 그 절의 글자 그림(코드 블록) (2026-09-29) |
| 4-1 실력을 무엇으로 보여 주나 | 4장 비교표 위 | 비교표 — 근거 이름은 `EVIDENCE` 상수 (2026-09-29) |
| 5-1 요구사항 상태 | 5장 맨 앞 | 5장 요약표의 상태 기호(`gen_metrics.parse_reqs`) |
| 7-1 스프린트 로드맵 | 7장 「스프린트 로드맵」 | 7장 로드맵 표 |
| 8-1 · 8-2 검증 지표 목표치 · QA 단계 | 8장 표·목록 위 | 검증 지표 표 · QA 프로세스 목록 (2026-09-29) |
| 9-1 향후 계획 | 9장 「향후 계획」 | 단기·중기·장기 목록 (2026-09-29) |
| E-1 결정 타임라인 | 부록 E 「한눈에 보기」 | 부록 E 본문 결정의 「정한 날」 + 「09-05 이후 — 한 줄 색인」 표 |

- 🔴 그림은 페이지 안의 표시(`<!-- gen_figures:이름 …-->` ~ `<!-- /gen_figures:이름 -->`) 사이에만
  쓴다. 그 사이를 손으로 고치면 다음 실행 때 덮인다. 표시가 없으면 정해 둔 자리에 새로 넣는다.
- 작업 폴더의 파일을 읽고 쓴다(`gen_metrics.py` 처럼 HEAD 를 세지 않는다) — 원본 표와 그림이
  같은 파일 안에 있어 같은 커밋에서 함께 움직여야 하기 때문이다.
- 멱등: 원본이 그대로면 다시 돌려도 결과가 같다.
"""

import html
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.dont_write_bytecode = True  # 불러오면서 tools/pages/__pycache__ 를 만들지 않게(커밋 대상이 아니다)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_metrics as gm  # noqa: E402 — 그림 틀 · 글자 폭 · 요구사항 셈을 같이 쓴다

ROOT = Path(__file__).resolve().parents[2]
CH = ROOT / "jekyll/chapters"
INK, INK2, GRID, AXIS = gm.INK, gm.INK2, gm.GRID, gm.AXIS
BOX_FILL = "#f6f5f1"  # gen_system_design.py 의 상자 바탕과 같다
ACCENT = "#256abf"    # 결정 점 — 관리 지표 요구사항 그림의 파랑 단계 중 하나(검증 통과)
PEOPLE = {"박민호": "#2a78d6", "백성검": "#eb6834", "정어진": "#1baf7a", "정상호": "#4a3aa7"}  # gen_overview.py 와 같은 사람 색


def esc(s):
    return html.escape(re.sub(r"\*\*|`", "", s), quote=True)


def wrap(text, width, size=11, max_lines=4):
    """띄어쓰기에서 먼저 자르고, 한 낱말이 폭보다 길면 글자 단위로 자른다. 넘치면 「…」."""
    lines, cur = [], ""
    for word in text.split(" "):
        cand = f"{cur} {word}" if cur else word
        if gm._text_w(cand, size) <= width:
            cur = cand
            continue
        if cur:
            lines.append(cur)
        while gm._text_w(word, size) > width:
            k = len(word)
            while k > 1 and gm._text_w(word[:k], size) > width:
                k -= 1
            lines.append(word[:k])
            word = word[k:]
        cur = word
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        last = lines[max_lines - 1]
        while last and gm._text_w(last + "…", size) > width:
            last = last[:-1]
        lines = lines[:max_lines - 1] + [last + "…"]
    return lines


def inject(path, name, block, anchor, where):
    """표시 사이를 바꾼다. 표시가 없으면 anchor(정규식) 줄의 앞(before)이나 뒤(after)에 새로 넣는다."""
    s = path.read_text(encoding="utf-8")
    head = f"<!-- gen_figures:{name} — tools/pages/gen_figures.py 가 만든다. 이 사이를 손으로 고치면 다음 실행 때 덮인다 -->"
    tail = f"<!-- /gen_figures:{name} -->"
    new = f"{head}\n\n{block}\n\n{tail}"
    pat = re.compile(re.escape(f"<!-- gen_figures:{name} ") + r".*?" + re.escape(tail), re.S)
    if pat.search(s):
        s = pat.sub(lambda _: new, s, count=1)
    else:
        m = re.search(anchor, s, re.M)
        if not m:
            sys.exit(f"{path.name}: 그림 {name} 을 넣을 자리({anchor})를 못 찾았다")
        s = s[:m.start()] + new + "\n\n" + s[m.start():] if where == "before" else s[:m.end()] + "\n\n" + new + s[m.end():]
    # 🔴 표시 앞뒤에는 늘 빈 줄을 둔다. 제목 바로 아래 붙어 있던 표 앞에 끼우면 끝 표시 다음 줄의 표를 kramdown 이
    # 표로 읽지 못해 「| 지표 | 설명 |…」 날 글자로 나온다(2026-09-29, 8장 검증 지표 · 4장 비교표)
    s = re.sub(rf"(?<=[^\n])\n(?={re.escape(f'<!-- gen_figures:{name} ')})", "\n\n", s)
    s = re.sub(rf"(?<={re.escape(tail)})\n(?=[^\n])", "\n\n", s)
    path.write_text(s, encoding="utf-8", newline="\n")


def box(x, y, w, h, title, sub):
    cx = x + w / 2
    return (f'<g><title>{esc(title)} — {esc(sub)}</title>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{BOX_FILL}" stroke="{INK2}" stroke-width="1.5"/>'
            f'<text x="{cx}" y="{y + 23}" text-anchor="middle" font-size="13.5" font-weight="600" fill="{INK}">{esc(title)}</text>'
            f'<text x="{cx}" y="{y + 41}" text-anchor="middle" font-size="11" fill="{INK2}">{esc(sub)}</text></g>')


def path_arrow(d):
    return f'<path d="{d}" fill="none" stroke="{INK2}" stroke-width="1.5" marker-end="url(#fa)"/>'


def text(x, y, s, size=11, anchor="middle", color=INK2, weight=None):
    w = f' font-weight="{weight}"' if weight else ""
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" fill="{color}"{w}>{esc(s)}</text>'


DEFS = (f'<defs><marker id="fa" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{INK2}"/></marker></defs>')


# --- 3-1 서비스 흐름 -----------------------------------------------------------
# 3장 1)절 「매칭과 검증을 하나의 흐름으로 묶어 푼다」 · 2)절 네 기능군을 그대로 옮겼다.
FLOW = {
    "p1": ("영상 올리기", "본인이 찍은 경기 영상"),
    "p2": ("실력 분석", "코드가 재고 AI가 판정"),
    "p3": ("선수 카드·호칭", "판정 요약만 공개"),
    "t1": ("경기 등록", "필요한 포지션·인원을 적는다"),
    "m1": ("지원 · 선택", "용병 지원 · 팀 선택"),
    "m2": ("경기", "확정 · 참가"),
    "m3": ("상호 평가", "선택형, 제재 별도"),
}


def fig_flow():
    b = [DEFS]
    b.append(text(8, 72, "선수 — 검증", 12, "start", INK, "600"))
    b.append(text(8, 182, "팀 — 매칭", 12, "start", INK, "600"))
    b += [box(96, 40, 120, 56, *FLOW["p1"]), box(238, 40, 120, 56, *FLOW["p2"]), box(380, 40, 120, 56, *FLOW["p3"]),
          box(96, 150, 262, 56, *FLOW["t1"]),
          box(530, 95, 124, 56, *FLOW["m1"]), box(674, 95, 70, 56, *FLOW["m2"]), box(764, 95, 90, 56, *FLOW["m3"])]
    b += [path_arrow("M216,68 L236,68"), path_arrow("M358,68 L378,68"),
          path_arrow("M500,68 L515,68 L515,116 L528,116"), path_arrow("M358,178 L515,178 L515,132 L528,132"),
          path_arrow("M654,123 L672,123"), path_arrow("M744,123 L762,123")]
    # 고리 — 평가와 검증이 쌓여 다음 매칭의 근거가 된다(3장 1)절 끝 문단)
    b.append(path_arrow("M809,95 L809,22 L440,22 L440,38"))
    b.append(text(625, 16, "경기 후 평가가 카드의 신뢰로 쌓이고, 다음 매칭의 근거가 된다"))
    return gm.figure(
        "".join(b), 860, 214,
        "서비스 흐름: 선수는 영상을 올려 실력 분석을 받고 선수 카드를 갖는다. 팀은 필요한 포지션과 인원을 등록한다. "
        "둘은 지원과 선택에서 만나 경기를 치르고, 경기 후 상호 평가가 카드의 신뢰로 쌓여 다음 매칭의 근거가 된다.",
        "그림 3-1. 매칭과 검증이 하나의 흐름으로 묶인다. 윗줄은 선수가 실력을 검증받는 길, 아랫줄은 팀이 빈 자리를 "
        "여는 길이다. 둘은 지원·선택에서 만나고, 경기 후 평가가 카드로 돌아가 다음 매칭을 돕는다.",
    )


# --- 5-1 요구사항 상태 ----------------------------------------------------------
def fig_reqs(text_05):
    r = gm.parse_reqs(text_05)
    by_cat = " · ".join(f"{cat} {sum(len(v) for v in g.values())}" for cat, _, g in r["cats"])
    return gm.fig_reqs(r, (
        f"그림 5-1. 이 장의 요구사항 {r['total']}개({by_cat})를 분류마다 상태별로 쌓았다 — 아래 각 절 "
        "요약표의 상태 기호를 센 것이라, 표를 고치면 그림도 따라온다. 칸에 마우스를 올리면 요구사항 번호가 보인다."))


# --- 7-1 스프린트 로드맵 ------------------------------------------------------------
def parse_roadmap(text_07):
    lines = text_07.splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith("| Sprint |"))
    header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
    people = []
    for c in header[3:]:
        m = re.match(r"^(\S+?)\((.+)\)$", c)
        people.append((m.group(1), m.group(2)) if m else (c, ""))
    sprints = []
    for l in lines[i + 2:]:
        if not l.startswith("|"):
            break
        l = re.sub(r"\{\{.*?\}\}", "", l)  # 링크 안의 Liquid 에 「|」 가 있다
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        num = int(re.search(r"\d+", cells[0]).group())
        (m1, d1), (m2, d2) = re.findall(r"(\d{2})\.(\d{2})", cells[1])[:2]
        sprints.append({"num": num, "done": "](" in cells[0], "goal": cells[2], "tasks": cells[3:],
                        "start": date(2026, int(m1), int(d1)), "end": date(2026, int(m2), int(d2))})
    return people, sprints


def fig_roadmap(text_07):
    people, sprints = parse_roadmap(text_07)
    w, lx, x0, x1, top, rh, bh = 860, 8, 146, 856, 70, 76, 66
    days = (sprints[-1]["end"] - sprints[0]["start"]).days + 1
    X = lambda d: round(x0 + (d - sprints[0]["start"]).days * (x1 - x0) / days, 1)
    h = top + len(people) * rh + 4
    b = []
    for s in sprints:
        xa, xb = X(s["start"]), X(s["end"] + timedelta(1))
        b.append(f'<line x1="{xa}" y1="2" x2="{xa}" y2="{h - 2}" stroke="{GRID}" stroke-width="1"/>')
        mark = " ✓" if s["done"] else ""
        b.append(text(xa + 6, 16, f"스프린트 {s['num']}{mark}", 12, "start", INK, "600"))
        b.append(text(xa + 6, 31, f"{s['start']:%m.%d}~{s['end']:%m.%d}", 10.5, "start"))
        for k, ln in enumerate(wrap(s["goal"], xb - xa - 12, 10.5, 2)):
            b.append(text(xa + 6, 46 + k * 13, ln, 10.5, "start"))
    for r, (name, role) in enumerate(people):
        y = top + r * rh
        c = PEOPLE.get(name, INK2)
        b.append(f'<rect x="{lx}" y="{y + 16}" width="4" height="34" rx="2" fill="{c}"/>')
        b.append(text(lx + 12, y + 30, name, 12.5, "start", INK, "600"))
        for k, ln in enumerate(wrap(role, x0 - lx - 20, 10.5, 2)):
            b.append(text(lx + 12, y + 46 + k * 13, ln, 10.5, "start"))
        for s in sprints:
            xa, xb = X(s["start"]) + 3, X(s["end"] + timedelta(1)) - 3
            task = s["tasks"][r] if r < len(s["tasks"]) else ""
            lines = wrap(task, xb - xa - 12, 11, 4)
            b.append(f'<g><title>스프린트 {s["num"]} · {esc(name)} — {esc(task)}</title>'
                     f'<rect x="{xa}" y="{y + 5}" width="{round(xb - xa, 1)}" height="{bh}" rx="6" fill="{c}" '
                     f'fill-opacity="0.10" stroke="{c}" stroke-width="1.2"/>')
            ty = y + 5 + (bh - len(lines) * 14) / 2 + 11
            for k, ln in enumerate(lines):
                b.append(text(round((xa + xb) / 2, 1), round(ty + k * 14, 1), ln, 11, "middle", INK))
            b.append("</g>")
    return gm.figure(
        "".join(b), w, h,
        "스프린트 로드맵: 스프린트 다섯 개를 날짜 축에 놓고, 사람마다 스프린트별로 맡은 일을 칸으로 그렸다.",
        "그림 7-1. 스프린트 다섯 개와 사람마다 맡은 일 — 아래 표와 같은 내용이다. 색은 사람이다. 칸 글이 길면 "
        "줄여 보이고, 칸에 마우스를 올리면 전부 보인다. ✓ 는 스프린트 로그가 있는(끝난) 스프린트다.",
    )


# --- E-1 결정 타임라인 -------------------------------------------------------------
INDEX_HEAD = "## 09-05 이후 — 한 줄 색인"  # 이 절의 표는 본문 없이 한 줄씩 적은 결정이다(2026-09-23 방식 변경)


def parse_index(text_e, sections):
    """「한 줄 색인」 표의 줄 → 결정. 분야 칸(「분석·AI」 같은 줄임)을 본문 절 이름에 맞춘다."""
    out, inside = [], False
    for line in text_e.splitlines():
        if line.startswith("## "):
            inside = line.strip() == INDEX_HEAD
            continue
        m = inside and re.match(r"^\|\s*(\d+)\s*\|\s*(20\d\d-\d\d-\d\d)\s*\|\s*(.+?)\s*\|\s*([^|]+?)\s*\|", line)
        if not m:
            continue
        field = m.group(4).strip()
        sec = next((s for s in sections if s.startswith(field)), None)
        if sec is None:
            gm.warn(f"부록 E 색인 {m.group(1)}번: 분야 「{field}」가 본문 절 이름({sections})과 안 맞는다")
            continue
        title = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", m.group(3))  # 링크는 글자만
        out.append({"num": int(m.group(1)), "title": title, "sec": sec,
                    "date": date(*map(int, m.group(2).split("-"))), "index": True})
    return out


def parse_decisions(text_e):
    sections, decisions, cur, want_date = [], [], None, False
    for line in text_e.splitlines():
        m = re.match(r"^## \d+\. (.+)$", line)
        if m:
            sections.append(m.group(1).strip())
            continue
        m = re.match(r"^### (\d+)\) (.+)$", line)
        if m and sections:
            cur = {"num": int(m.group(1)), "title": m.group(2).strip(), "sec": sections[-1], "date": None}
            decisions.append(cur)
            want_date = False
            continue
        if cur and cur["date"] is None and ("정한 날" in line or want_date):
            d = re.search(r"(20\d\d)-(\d\d)-(\d\d)", line)
            if d:
                cur["date"] = date(*map(int, d.groups()))
            want_date = d is None and "정한 날" in line  # 날짜가 다음 줄로 넘어간 경우
    # 본문에 날짜 대신 「프로젝트 초기」처럼 적힌 결정은 「한눈에 보기」 표의 같은 결정에서 날짜를 빌린다
    key = lambda s: re.sub(r"[^0-9A-Za-z가-힣]", "", re.sub(r"\*\*|`", "", s))
    table = {key(m.group(2)): date(*map(int, m.group(1).split("-")))
             for m in re.finditer(r"(?m)^\|\s*(20\d\d-\d\d-\d\d)\s*\|\s*([^|]+?)\s*\|", text_e)}
    for d in decisions:
        if d["date"] is None:
            d["date"] = table.get(key(d["title"]))
    missing = [d["num"] for d in decisions if d["date"] is None]
    if missing:
        gm.warn(f"부록 E: 정한 날을 못 찾은 결정 {missing} — 본문에도 「한눈에 보기」 표에도 날짜가 없다")
    body = [dict(d, index=False) for d in decisions if d["date"]]
    index = parse_index(text_e, sections)
    clash = {d["num"] for d in body} & {d["num"] for d in index}
    if clash:
        gm.warn(f"부록 E: 본문과 색인에 같은 번호 {sorted(clash)}")
    return sections, body + index


def fig_decisions(text_e):
    sections, ds = parse_decisions(text_e)
    d0, d1 = min(d["date"] for d in ds), max(d["date"] for d in ds)
    n_days = (d1 - d0).days + 1
    w, lx, x0, x1, top, gap = 860, 8, 150, 790, 30, 6
    step = (x1 - x0) / max(n_days - 1, 1)
    X = lambda d: round(x0 + (d - d0).days * step, 1)
    stacks = {}
    for d in sorted(ds, key=lambda d: d["num"]):
        stacks.setdefault((d["sec"], d["date"]), []).append(d)
    lane_h = {s: max([len(v) for (sec, _), v in stacks.items() if sec == s] + [1]) * 13 + 20 for s in sections}
    ys, y = {}, top
    for s in sections:
        ys[s] = y
        y += lane_h[s] + gap
    h_axis = y + 22   # 날짜 눈금 줄
    h = h_axis + 22   # 그 아래 범례 한 줄
    b = []
    for s in sections:  # 분야 줄 — 옅은 바탕으로 줄을 가른다
        b.append(f'<rect x="{x0 - 14}" y="{ys[s]}" width="{x1 - x0 + 28}" height="{lane_h[s]}" rx="4" fill="{BOX_FILL}"/>')
        n = sum(1 for d in ds if d["sec"] == s)
        b.append(text(lx, ys[s] + lane_h[s] / 2 + 4, s, 12, "start", INK))
        b.append(text(x1 + 22, ys[s] + lane_h[s] / 2 + 4, f"{n}건", 11, "start"))
    # 날짜 눈금 — 칸이 넉넉하면 날마다. 좁으면 첫날·끝날·1일·월요일 순으로, 앞서 놓은 글자와
    # 겹치지 않는 것만(08-31 월요일과 09-01 처럼 붙은 날이 겹쳐 찍히지 않게)
    days = [d0 + timedelta(i) for i in range(n_days)]
    if step >= 36:
        ticks = days
    else:
        ticks = []
        for day in [d0, d1] + [d for d in days if d.day == 1] + [d for d in days if d.weekday() == 0]:
            if day not in ticks and all(abs(X(day) - X(t)) >= 34 for t in ticks):
                ticks.append(day)
    for day in sorted(ticks):
        b.append(text(X(day), h_axis - 6, f"{day:%m-%d}", 10.5))
    for num, s, _ in gm.SPRINTS:
        if d0 < s <= d1:
            b.append(f'<line x1="{X(s) - step / 2}" y1="{top - 10}" x2="{X(s) - step / 2}" y2="{h_axis - 18}" stroke="{AXIS}" stroke-width="1"/>')
            b.append(text(X(s) - step / 2 + 4, top - 14, f"스프린트 {num} 시작", 10.5, "start"))

    def dot(cx, cy, index):  # 채운 점 = 본문에 근거까지, 빈 점 = 한 줄 색인
        if index:
            return f'<circle cx="{cx}" cy="{cy}" r="4.5" fill="#fff" stroke="{ACCENT}" stroke-width="2"/>'
        return f'<circle cx="{cx}" cy="{cy}" r="5" fill="{ACCENT}" stroke="#fff" stroke-width="1.5"/>'

    for (s, day), group in stacks.items():
        for k, d in enumerate(group):
            cx, cy = X(day), ys[s] + lane_h[s] - 12 - k * 13
            tip = f"{d['num']}) {esc(d['title'])} — {day:%m-%d}"
            b.append(f'<g><title>{tip}</title><circle class="hit" cx="{cx}" cy="{cy}" r="11" fill="transparent"/>'
                     f'{dot(cx, cy, d["index"])}</g>')
    body = [d for d in ds if not d["index"]]
    index = [d for d in ds if d["index"]]
    legend = [(False, f"본문에 근거·대안까지 적은 결정 {len(body)}개"),
              (True, f"한 줄 색인의 결정 {len(index)}개 — 상세는 원문")]
    lx2 = x0 - 8
    for is_index, label in legend:
        if (is_index and not index) or (not is_index and not body):
            continue
        b.append(dot(lx2 + 5, h - 12, is_index))
        b.append(text(lx2 + 15, h - 8, label, 11, "start"))
        lx2 += 15 + gm._text_w(label, 11) + 24
    return gm.figure(
        "".join(b), w, h,
        f"결정 타임라인: 이 부록의 결정 {len(ds)}개를 정한 날과 분야로 점을 찍었다({d0:%m-%d}~{d1:%m-%d}). "
        f"채운 점 {len(body)}개는 본문에 근거까지, 빈 점 {len(index)}개는 한 줄 색인이다.",
        f"그림 E-1. 이 부록의 결정 {len(ds)}개를 정한 날(가로)과 분야(세로)로 놓았다. 채운 점은 아래 본문에 "
        f"근거·대안까지 적은 결정, 빈 점은 「09-05 이후 — 한 줄 색인」의 결정이다. 점에 마우스를 올리면 "
        f"결정 번호와 제목이 보인다({d1:%m-%d}까지).",
    )


# --- 공용: 절 읽기 · 여러 줄 상자 · 곡선 화살표 (2026-09-29) --------------------------------
FIG_BLOCK = re.compile(r"<!-- gen_figures:(\S+) .*?<!-- /gen_figures:\1 -->", re.S)


def plain(s):
    """마크다운 강조·코드·링크를 벗긴 글자."""
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    return re.sub(r"\*\*|\*|`", "", s).strip()


def section(text_md, heading):
    """「## <heading>」 아래 줄들(다음 「## 」 전까지). heading 은 정규식이다."""
    lines = text_md.splitlines()
    for i, line in enumerate(lines):
        if re.match(rf"^## {heading}\s*$", line):
            out = []
            for l in lines[i + 1:]:
                if l.startswith("## "):
                    break
                out.append(l)
            return out
    sys.exit(f"「## {heading}」 절을 못 찾았다 — 제목이 바뀌었으면 gen_figures.py 도 고친다")


def table_rows(lines):
    """줄들 안의 첫 마크다운 표 → (머리글 칸, 본문 줄마다의 칸)."""
    rows = []
    for l in lines:
        if l.startswith("|"):
            rows.append([c.strip() for c in l.strip().strip("|").split("|")])
        elif rows:
            break
    if len(rows) < 3:
        sys.exit(f"표를 못 찾았다: {lines[:3]}")
    return rows[0], rows[2:]


def card(x, y, w, h, title, body="", tip=None, emph=False, ts=13, bs=11, t_lines=2, b_lines=3):
    """제목(굵게)과 본문을 폭에 맞춰 접어 상자 안 세로 가운데에 놓는다. emph 면 강조 파랑 테두리.
    제목이 없으면 본문을 진한 글자로 쓴다. 마우스를 올리면 tip(없으면 제목 — 본문)이 뜬다."""
    stroke, sw = (ACCENT, 2) if emph else (INK2, 1.5)
    fill = f'fill="{ACCENT}" fill-opacity="0.10"' if emph else f'fill="{BOX_FILL}"'
    tl = wrap(title, w - 16, ts, t_lines) if title else []
    bl = wrap(body, w - 16, bs, b_lines) if body else []
    lines = [(t, ts, INK, "600") for t in tl] + [(t, bs, INK2 if tl else INK, None) for t in bl]
    gap = 4 if tl and bl else 0
    cy = y + (h - (sum(s + 4 for _, s, _, _ in lines) - 4 + gap)) / 2
    tip = tip or (f"{title} — {body}" if title and body else title or body)
    out = [f'<g><title>{esc(tip)}</title>'
           f'<rect x="{x}" y="{y}" width="{round(w, 1)}" height="{h}" rx="6" {fill} stroke="{stroke}" stroke-width="{sw}"/>']
    for k, (t, s, c, wt) in enumerate(lines):
        if k == len(tl) and gap:
            cy += gap
        out.append(text(round(x + w / 2, 1), round(cy + s * 0.82, 1), t, s, "middle", c, wt))
        cy += s + 4
    return "".join(out) + "</g>"


def curve(x1, y1, x2, y2):
    xm = round((x1 + x2) / 2, 1)
    return path_arrow(f"M{x1},{y1} C{xm},{y1} {xm},{y2} {x2},{y2}")


# --- 1-1 비전에서 목표까지 ------------------------------------------------------------
def parse_vision(t01):
    vision = plain(" ".join(l.strip() for l in section(t01, "비전") if l.strip()))
    mission = [plain(l[2:]) for l in section(t01, "미션") if l.startswith("- ")]
    values = [(plain(r[0]), plain(r[1])) for r in table_rows(section(t01, "핵심 가치.*"))[1]]
    goals = [plain(m.group(1)) for l in section(t01, "프로젝트 목표") if (m := re.match(r"^\d+\.\s+(.+)$", l))]
    return vision, mission, values, goals


def fig_vision(t01):
    vision, mission, values, goals = parse_vision(t01)
    w, lx, x0, x1, gap = 860, 8, 112, 852, 12
    cw = x1 - x0

    def row(items, y, h, make):
        n = len(items)
        bw = (cw - (n - 1) * gap) / n
        return [make(round(x0 + i * (bw + gap), 1), y, bw, h, it) for i, it in enumerate(items)]

    b, y = [], 8
    for label, h, parts in (
        ("비전", 50, None),
        ("미션", 64, row(mission, 0, 64, lambda x, yy, bw, h, m: card(x, yy, bw, h, "", m, bs=11.5)) if mission else []),
        ("핵심 가치", 70, row(values, 0, 70, lambda x, yy, bw, h, v: card(x, yy, bw, h, v[0], v[1]))),
        ("목표", 64, row(goals, 0, 64, lambda x, yy, bw, h, g: card(x, yy, bw, h, *(g.split(": ", 1) if ": " in g else (g, "")), ts=12.5))),
    ):
        b.append(text(lx, y + h / 2 + 4, label, 12.5, "start", INK, "600"))
        if parts is None:  # 비전은 한 줄이라 가운데에 좁게 — 위가 좁고 아래가 넓은 층
            vw = min(cw, gm._text_w(vision, 14) + 60)
            b.append(card(round(x0 + (cw - vw) / 2, 1), y, vw, h, vision, emph=True, ts=14, t_lines=2))
        else:
            b.append(f'<g transform="translate(0,{y})">' + "".join(parts) + "</g>")
        y += h + 14
    return gm.figure(
        "".join(b), w, y - 6,
        f"비전에서 목표까지: 비전 한 줄 아래에 미션 {len(mission)}개, 핵심 가치 {len(values)}개"
        f"({'·'.join(v for v, _ in values)}), 프로젝트 목표 {len(goals)}개를 층으로 놓았다.",
        "그림 1-1. 비전에서 목표까지 — 아래 절의 비전·미션·핵심 가치·프로젝트 목표를 한 장에 층으로 놓았다. "
        "상자에 마우스를 올리면 전문이 보인다.",
    )


# --- 2-1 문제에서 해법까지 ------------------------------------------------------------
# 선은 2장 문제 서술과 3장 1)절(매칭·검증)을 읽고 이은 것이다 — 원본 표가 없어 상수로 둔다.
# 키는 페이지 글자와 같아야 한다. 다르면 멈춘다(제목이 바뀌었으면 여기 선도 다시 판단한다).
PROBLEM_TASK = {
    "인원 부족으로 인한 경기 취소": ["신뢰 가능한 매칭"],
    "신뢰할 수 있는 용병 구인의 어려움": ["신뢰 가능한 매칭", "실력의 데이터화"],  # 실력·매너를 미리 확인할 길이 없다
    "실력에 대한 객관적 기준 부재": ["실력의 데이터화"],
}
TASK_FEATURE = {
    "신뢰 가능한 매칭": ["매칭", "상호 평가"],        # 상호 평가 — 매너·노쇼를 경기 뒤 기록으로 남긴다
    "실력의 데이터화": ["실력 분석", "선수 카드·호칭"],
}


def parse_problem(t02, t03):
    probs = []
    for l in section(t02, "문제 정의"):
        m = re.match(r"^### \d+\)\s*(.+)$", l)
        if m:
            probs.append({"title": plain(m.group(1)), "notes": []})
        elif probs and l.startswith("- "):
            probs[-1]["notes"].append(plain(l[2:]))
    line = next((l for l in section(t02, "시사점") if l.startswith("→")), "")
    tasks = re.findall(r'\*\*"([^"]+)"\*\*', line)
    feats = {plain(r[0]): plain(r[1]) for r in table_rows(section(t03, r"2\) 주요 기능"))[1]}
    got = ([p["title"] for p in probs], tasks, sorted(feats))
    want = (list(PROBLEM_TASK), list(TASK_FEATURE), sorted(f for fs in TASK_FEATURE.values() for f in fs))
    for what, g, x in zip(("2장 문제 제목", "2장 시사점의 과제", "3장 기능군"), got, want):
        if g != x:
            sys.exit(f"그림 2-1: {what}이 {g} 로 바뀌었다(선 상수는 {x}) — gen_figures.py 의 PROBLEM_TASK·TASK_FEATURE 를 고친다")
    return probs, tasks, feats, plain(line)


def fig_problem(t02, t03):
    probs, tasks, feats, line = parse_problem(t02, t03)
    w, (c1, c1w), (c2, c2w), (c3, c3w), top = 860, (8, 250), (332, 196), (606, 246), 34
    order = [f for tk in tasks for f in TASK_FEATURE[tk]]  # 과제별로 묶어 선이 엇갈리지 않게
    fh, fg, ph, pg, th = 44, 12, 52, 18, 60
    fy = {f: top + i * (fh + fg) for i, f in enumerate(order)}
    py = {p["title"]: top + 8 + i * (ph + pg) for i, p in enumerate(probs)}
    ty = {tk: round(sum(fy[f] + fh / 2 for f in TASK_FEATURE[tk]) / len(TASK_FEATURE[tk]) - th / 2, 1) for tk in tasks}
    b = [DEFS]
    for x, s in ((c1, "문제 — 2장"), (c2, "풀어야 할 과제 — 2장 시사점"), (c3, "기능군 — 3장")):
        b.append(text(x, 16, s, 12, "start", INK, "600"))
    incoming = {tk: [p for p in PROBLEM_TASK if tk in PROBLEM_TASK[p]] for tk in tasks}
    for p, tks in PROBLEM_TASK.items():  # 문제 → 과제. 한 과제로 여러 선이 들어오면 끝점을 벌린다
        for tk in tks:
            j, k = incoming[tk].index(p), len(incoming[tk])
            b.append(curve(c1 + c1w, py[p] + ph / 2, c2 - 2, round(ty[tk] + th * (j + 1) / (k + 1), 1)))
    for tk in tasks:  # 과제 → 기능
        fs = TASK_FEATURE[tk]
        for j, f in enumerate(fs):
            b.append(curve(c2 + c2w, round(ty[tk] + th * (j + 1) / (len(fs) + 1), 1), c3 - 2, fy[f] + fh / 2))
    for p in probs:
        b.append(card(c1, py[p["title"]], c1w, ph, p["title"], tip=f"{p['title']} — " + " / ".join(p["notes"]), ts=12.5))
    for tk in tasks:
        b.append(card(c2, ty[tk], c2w, th, tk, tip=line, emph=True, ts=13.5))
    for f in order:
        b.append(card(c3, fy[f], c3w, fh, f, tip=f"{f} — {feats[f]}"))
    h = max(max(fy.values()) + fh, max(py.values()) + ph) + 12
    return gm.figure(
        "".join(b), w, h,
        f"문제에서 해법까지: 2장의 문제 {len(probs)}개({', '.join(p['title'] for p in probs)})가 두 과제"
        f"({', '.join(tasks)})로 모이고, 3장의 기능군 {len(order)}개가 그 과제를 푼다.",
        "그림 2-1. 문제에서 해법까지 — 위 문제 정의가 시사점의 두 과제로 모이고, "
        f"<a href=\"{{{{ '/03-서비스제안/' | relative_url }}}}\">3장</a>의 기능군이 그 과제를 푼다. "
        "선은 이 장의 문제 서술과 3장 1)절의 매칭·검증 설명을 따라 이었다. 상자에 마우스를 올리면 본문이 보인다.",
    )


# --- 3-2 측정과 판단의 분리 ------------------------------------------------------------
def parse_pipeline(t03):
    lines = t03.splitlines()
    try:
        i = lines.index("### 처리 흐름")
        a = next(k for k in range(i, len(lines)) if lines[k].startswith("```"))
        z = next(k for k in range(a + 1, len(lines)) if lines[k].startswith("```"))
    except (ValueError, StopIteration):
        sys.exit("그림 3-2: 3장 「### 처리 흐름」 절의 글자 그림(코드 블록)을 못 찾았다")
    block = lines[a + 1:z]
    start = next(l.strip() for l in block if l.strip() and l.strip()[0] not in "│├└")
    steps = [m.groups() for l in block if (m := re.match(r"^\s*[├└]─\s*\(([A-Z])\)\s*(.+?)\s{2,}(.+?)\s*$", l))]
    rest = "\n".join(lines[z + 1:]).split("\n### ")[0]  # 글자 그림 다음부터 다음 소절 전까지
    m = re.search(r"\(([A-Z])\)만이 판단이 개입", rest)
    if not m:
        gm.warn("그림 3-2: 「(X)만이 판단이 개입」 문장을 못 찾아 강조 없이 그린다")
    return start, steps, m.group(1) if m else None, "프레임 번호를 함께 남긴다" in rest


def fig_pipeline(t03):
    start, steps, llm, keeps = parse_pipeline(t03)
    w, x0, gap, y, bh = 860, 110, 10, 40, 90
    bw = (850 - x0 - (len(steps) - 1) * gap) / len(steps)
    b = [DEFS]
    # 범례 — 두 가지 상자
    b.append(f'<rect x="{x0}" y="8" width="14" height="12" rx="3" fill="{BOX_FILL}" stroke="{INK2}" stroke-width="1.5"/>')
    b.append(text(x0 + 20, 18, "코드 — 같은 입력이면 언제나 같은 값", 11, "start"))
    lx = x0 + 20 + gm._text_w("코드 — 같은 입력이면 언제나 같은 값", 11) + 26
    if llm:
        b.append(f'<rect x="{lx}" y="8" width="14" height="12" rx="3" fill="{ACCENT}" fill-opacity="0.10" stroke="{ACCENT}" stroke-width="2"/>')
        b.append(text(lx + 20, 18, "언어 모델 — 측정값을 기준에 대조해 판정만 한다", 11, "start"))
    b.append(f'<g><title>{esc(start)}</title><rect x="8" y="{y + bh / 2 - 22}" width="86" height="44" rx="22" '
             f'fill="none" stroke="{INK2}" stroke-width="1.5"/>'
             f'{text(51, y + bh / 2 + 4.5, start, 12.5, "middle", INK, "600")}</g>')
    b.append(path_arrow(f"M94,{y + bh / 2} L{x0 - 2},{y + bh / 2}"))
    for i, (letter, name, out) in enumerate(steps):
        x = round(x0 + i * (bw + gap), 1)
        if i:
            b.append(path_arrow(f"M{round(x - gap, 1)},{y + bh / 2} L{x - 1},{y + bh / 2}"))
        b.append(card(x, y, bw, bh, f"({letter}) {name}", out, emph=letter == llm, ts=12.5, t_lines=1))
        if letter == llm and keeps:
            b.append(f'<line x1="{round(x + bw / 2, 1)}" y1="{y + bh}" x2="{round(x + bw / 2, 1)}" y2="{y + bh + 10}" stroke="{ACCENT}" stroke-width="1.5"/>')
            for k, ln in enumerate(wrap("근거가 된 측정값과 프레임 번호를 함께 남긴다", bw + 40, 10.5, 2)):
                b.append(text(round(x + bw / 2, 1), y + bh + 24 + k * 14, ln, 10.5))
    return gm.figure(
        "".join(b), w, y + bh + 50,
        f"처리 흐름: {start} 뒤 " + ", ".join(f"({l}) {n}" for l, n, _ in steps) + " 순서로 간다. "
        + (f"언어 모델이 끼는 단계는 ({llm}) 하나이고 나머지는 코드다." if llm else ""),
        f"그림 3-2. 처리 흐름 {len(steps)}단계 — 위 글자 그림을 옮겼다. "
        + (f"파란 상자가 언어 모델이 끼는 단계로 ({llm}) 하나뿐이고, 나머지는 같은 입력이면 언제나 같은 값을 내는 코드다. " if llm else "")
        + "상자에 마우스를 올리면 전문이 보인다.",
    )


# --- 4-1 실력을 무엇으로 보여 주나 ------------------------------------------------------
# 비교표에 「근거」 칸이 따로 없어 약점 칸이 말하는 근거를 상수로 옮겼다. 각 행 약점 칸에
# 그 말이 실제로 있는지 확인한다 — 표를 고쳐 말이 빠지면 여기서 멈춘다.
EVIDENCE = [  # (서비스 칸의 앞부분, 그림에 쓸 근거, 약점 칸에 있어야 할 말)
    ("오픈채팅", "확인할 근거 없음", "검증 불가"),
    ("매치업", "자기 신고", "자기 신고"),
    ("플랩풋볼", "참여 이력 · 매니저 평가", "매니저 평가"),
]
OURS = ("SUPERSUB", "경기 영상 분석", "영상")  # (이름, 근거, 「SUPERSUB과의 차이」 칸에 있어야 할 말)


def parse_evidence(t04):
    _, rows = table_rows(section(t04, r"경쟁 서비스 비교 \(국내 기준\)"))
    steps = []
    for key, level, must in EVIDENCE:
        r = next((r for r in rows if plain(r[0]).startswith(key)), None)
        if r is None or must not in r[2]:
            sys.exit(f"그림 4-1: 비교표의 「{key}」 행이 없거나 약점 칸에 「{must}」가 없다 — gen_figures.py 의 EVIDENCE 를 고친다")
        steps.append({"name": plain(r[0]), "level": level, "tip": f"{plain(r[0])} — 약점: {plain(r[2])}"})
    ours = [plain(r[3]) for r in rows if OURS[2] in r[3]]
    if not ours:
        sys.exit(f"그림 4-1: 비교표의 「SUPERSUB과의 차이」 칸에 「{OURS[2]}」가 없다")
    steps.append({"name": OURS[0], "level": OURS[1], "tip": f"{OURS[0]} — " + " / ".join(ours), "ours": True})
    left = [plain(r[0]) for r in rows if not any(plain(r[0]).startswith(k) for k, _, _ in EVIDENCE)]
    if left:
        gm.warn(f"그림 4-1: 그림에 없는 서비스 {left} — EVIDENCE 에 더한다")
    return steps


def fig_evidence(t04):
    steps = parse_evidence(t04)
    w, x0, sw, gap = 860, 16, 196, 16
    rise = [46 + i * 34 for i in range(len(steps))]
    names = [wrap(s["name"], sw - 8, 12.5, 2) for s in steps]
    base = max(r + len(n) * 16 + 12 for r, n in zip(rise, names)) + 2
    b = [DEFS]
    for i, s in enumerate(steps):
        x, top = x0 + i * (sw + gap), base - rise[i]
        ours = s.get("ours", False)
        fill = f'fill="{ACCENT}" fill-opacity="0.10"' if ours else f'fill="{BOX_FILL}"'
        stroke = f'stroke="{ACCENT}" stroke-width="2"' if ours else f'stroke="{INK2}" stroke-width="1.5"'
        b.append(f'<g><title>{esc(s["tip"])}</title><rect x="{x}" y="{top}" width="{sw}" height="{rise[i]}" rx="6" {fill} {stroke}/>')
        b.append(text(x + sw / 2, top + 26, s["level"], 12.5, "middle", INK, "600"))
        for k, ln in enumerate(names[i]):
            b.append(text(x + sw / 2, top - 10 - (len(names[i]) - 1 - k) * 16, ln, 12.5, "middle", INK, "600" if ours else None))
        b.append("</g>")
    x_end = x0 + len(steps) * (sw + gap) - gap
    b.append(path_arrow(f"M{x0},{base + 16} L{x_end},{base + 16}"))
    b.append(text(x0, base + 36, "실력을 무엇으로 보여 주나 — 오른쪽일수록 실제 경기 플레이에 가까운 근거", 11.5, "start"))
    return gm.figure(
        "".join(b), w, base + 46,
        "서비스마다 실력을 무엇으로 보여 주나: " + ", ".join(f"{s['name']}은 {s['level']}" for s in steps) + ".",
        "그림 4-1. 서비스마다 실력을 무엇으로 보여 주나 — 아래 비교표의 약점 칸을 근거의 단계로 놓았다(오른쪽일수록 "
        "실제 플레이에 가까운 근거). 칸에 마우스를 올리면 표의 약점 칸이 보인다.",
    )


# --- 8-1 검증 지표 목표 · 8-2 QA 네 단계 -------------------------------------------------
def parse_kpi(t08):
    out = []
    for r in table_rows(section(t08, r"검증 지표 \(KPI 예시\)"))[1]:
        name, desc, target = plain(r[0]), plain(r[1]), plain(r[2])
        m = re.search(r"\d+(?:\.\d+)?\s*(?:%|점|등급)\s*(?:이상|이하|이내)?", target)
        out.append({"name": name, "desc": desc, "group": "채점" if name.startswith("채점") else "서비스",
                    "value": m.group(0) if m else ("미정" if "TBD" in target else target),
                    "extra": (target[:m.start()] + target[m.end():]).strip() if m else ""})
    return out


def fig_kpi(t08):
    ks = parse_kpi(t08)

    def tile(k):
        note = f"{k['extra']} — {k['desc']}" if k["extra"] else k["desc"]
        return (f'<div class="stat-tile"><div class="stat-value">{esc(k["value"])}</div>'
                f'<div class="stat-label">{esc(k["name"])}</div><div class="stat-note">{esc(note)}</div></div>')

    groups = [g for g in ("서비스", "채점") if any(k["group"] == g for k in ks)]
    n = {g: sum(k["group"] == g for k in ks) for g in groups}
    return ('<figure class="doc-figure">'
            + "".join(f'<div class="stat-tiles">{"".join(tile(k) for k in ks if k["group"] == g)}</div>' for g in groups)
            + '<figcaption class="doc-figure-caption">그림 8-1. 검증 지표의 목표치 — 아래 표의 목표치 칸을 카드로 옮겼다. '
            + "잰 값이 아니라 목표(예시)다. "
            + (f"윗줄은 서비스 지표 {n['서비스']}개, 아랫줄은 채점 지표 {n['채점']}개다." if len(groups) == 2 else "")
            + "</figcaption></figure>")


def parse_qa(t08):
    sec = section(t08, "QA 프로세스")
    steps = [plain(m.group(1)) for l in sec if (m := re.match(r"^\d+\.\s+(.+)$", l))]
    body = "\n".join(sec)
    m = re.search(r"(\d)단계에서", body)
    return steps, int(m.group(1)) if m and "QA 체크리스트" in body else None


def fig_qa(t08):
    steps, doc_step = parse_qa(t08)
    w, x0, gap, y, bh = 860, 8, 26, 30, 60
    bw = (852 - x0 - (len(steps) - 1) * gap) / len(steps)
    X = [round(x0 + i * (bw + gap), 1) for i in range(len(steps))]
    b = [DEFS]
    for i, s in enumerate(steps):
        label = f"{i + 1}단계" + (" · QA 체크리스트로 확인" if doc_step == i + 1 else "")
        b.append(text(X[i], y - 10, label, 11, "start", INK if doc_step == i + 1 else INK2, "600" if doc_step == i + 1 else None))
        if i:
            b.append(path_arrow(f"M{round(X[i] - gap, 1)},{y + bh / 2} L{X[i] - 1},{y + bh / 2}"))
        b.append(card(X[i], y, bw, bh, s, ts=12.5))
    loop = len(steps) >= 3 and "재검증" in steps[-1]
    if loop:  # 마지막 단계의 재검증 — 2단계로 되돌아가는 화살표로 그린다
        xa, xb, yl = round(X[-1] + bw / 2, 1), round(X[1] + bw / 2, 1), y + bh + 22
        b.append(path_arrow(f"M{xa},{y + bh} L{xa},{yl} L{xb},{yl} L{xb},{y + bh + 2}"))
        b.append(text(round((xa + xb) / 2, 1), yl - 6, "재검증 — 고친 것을 다시 확인한다", 11))
    return gm.figure(
        "".join(b), w, y + bh + (34 if loop else 10),
        f"QA {len(steps)}단계: " + " → ".join(steps) + ". " + ("마지막 단계의 재검증은 2단계로 되돌아간다." if loop else ""),
        f"그림 8-2. QA {len(steps)}단계 — 아래 목록을 옮겼다. "
        + (f"{len(steps)}단계의 재검증은 2단계로 되돌아가는 화살표로 그렸다. " if loop else "")
        + (f"{doc_step}단계에서 쓰는 문서가 QA 체크리스트다." if doc_step else ""),
    )


# --- 9-1 향후 계획 -------------------------------------------------------------------
def parse_future(t09):
    phases = []
    for l in section(t09, r"향후 계획 \(로드맵\)"):
        m = re.match(r"^### (\S+)\s*\((.+)\)\s*$", l)
        if m:
            phases.append({"name": m.group(1), "span": m.group(2), "items": []})
        elif phases and l.startswith("- "):
            raw = plain(l[2:])
            short = re.sub(r",?\s*\[TBD[^\]]*\]", "", raw)  # 그림에서는 [TBD] 표시를 뺀다 — 원문은 칸의 <title>
            short = re.sub(r"\(\s*\)", "", short).replace(" )", ")").strip()
            if short:
                phases[-1]["items"].append((short, raw))
    return phases


def fig_future(t09):
    ph = parse_future(t09)
    w, x0, gap, top, hh, lh = 860, 8, 30, 8, 50, 16
    cw = (852 - x0 - (len(ph) - 1) * gap) / len(ph)
    wrapped = [[(wrap(s, cw - 36, 11.5, 3), raw) for s, raw in p["items"]] for p in ph]
    body_h = max(sum(len(ls) * lh + 8 for ls, _ in col) for col in wrapped) + 12
    b = [DEFS]
    for i, p in enumerate(ph):
        x = round(x0 + i * (cw + gap), 1)
        b.append(f'<rect x="{x}" y="{top}" width="{round(cw, 1)}" height="{hh + body_h}" rx="6" fill="{BOX_FILL}" stroke="{INK2}" stroke-width="1.5"/>')
        b.append(text(x + 14, top + 22, p["name"], 13.5, "start", INK, "600"))
        b.append(text(x + 14, top + 39, p["span"], 11, "start"))
        b.append(f'<line x1="{x}" y1="{top + hh}" x2="{round(x + cw, 1)}" y2="{top + hh}" stroke="{GRID}" stroke-width="1"/>')
        if i:
            b.append(path_arrow(f"M{round(x - gap + 4, 1)},{top + hh / 2} L{x - 2},{top + hh / 2}"))
        yy = top + hh + 12
        for ls, raw in wrapped[i]:
            b.append(f'<g><title>{esc(raw)}</title><circle cx="{x + 18}" cy="{yy + 7}" r="2.5" fill="{INK2}"/>')
            for k, ln in enumerate(ls):
                b.append(text(x + 28, yy + 11 + k * lh, ln, 11.5, "start", INK))
            b.append("</g>")
            yy += len(ls) * lh + 8
    tbd = any("TBD" in raw for p in ph for _, raw in p["items"])
    return gm.figure(
        "".join(b), w, top + hh + body_h + 8,
        "향후 계획: " + " → ".join(f"{p['name']}({p['span']}) {len(p['items'])}개" for p in ph) + ".",
        "그림 9-1. 향후 계획 — 아래 " + "·".join(p["name"] for p in ph) + " 목록을 옮겼다. "
        + ("그림에서는 [TBD] 표시를 뺐고, 항목에 마우스를 올리면 원문이 보인다." if tbd else "항목에 마우스를 올리면 원문이 보인다."),
    )


def main():
    p01, p02, p03, p04, p05, p07, p08, p09, pe = (CH / f for f in (
        "01-사업개요.markdown", "02-현황및문제정의.markdown", "03-서비스제안.markdown", "04-시장및수익모델.markdown",
        "05-요구사항분석.markdown", "07-개발구현계획.markdown", "08-테스트및검증계획.markdown",
        "09-산출물및향후계획.markdown", "부록E-결정기록.markdown"))
    # 🔴 파서에는 이 스크립트가 넣은 구간을 걷어낸 글만 준다 — 그림 안 글자를 원문으로 다시 읽으면 원문을 고쳐도
    # 옛 값에 머문다. 예: 8-2 설명의 「2단계에서」가 원문 문단보다 앞에 있어 `(\d)단계에서` 에 먼저 걸린다
    # (2026-09-29 에 걷어내기를 빼고 원문을 3단계로 바꿔 보니 그림이 2단계에 머물렀다).
    t = lambda p: FIG_BLOCK.sub("", p.read_text(encoding="utf-8"))
    inject(p01, "vision", fig_vision(t(p01)), r"^## 비전$", "before")
    inject(p02, "problem-solution", fig_problem(t(p02), t(p03)), r"^→ .*핵심 과제[ \t]*$", "after")
    inject(p03, "service-flow", fig_flow(), r"^## 2\) 주요 기능$", "before")
    inject(p03, "pipeline", fig_pipeline(t(p03)), r"^### 촬영 조건의 표준화$", "before")
    inject(p04, "evidence", fig_evidence(t(p04)), r"^## 경쟁 서비스 비교 \(국내 기준\)$", "after")
    inject(p05, "req-status", fig_reqs(t(p05)), r"^## 1\) 기능 요구사항$", "before")
    inject(p07, "roadmap", fig_roadmap(t(p07)), r"^### 스프린트 로드맵$", "after")
    inject(p08, "kpi-targets", fig_kpi(t(p08)), r"^## 검증 지표 \(KPI 예시\)$", "after")
    inject(p08, "qa-process", fig_qa(t(p08)), r"^## QA 프로세스$", "after")
    inject(p09, "future", fig_future(t(p09)), r"^## 향후 계획 \(로드맵\)$", "after")
    inject(pe, "decisions", fig_decisions(t(pe)), r"^## 한눈에 보기 \(시간순\)$", "after")
    print("ok")


if __name__ == "__main__":
    main()
