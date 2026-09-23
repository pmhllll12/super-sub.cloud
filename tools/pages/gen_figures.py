"""제안서 장(章) 안에 그림을 끼워 넣는 생성기 (2026-09-23 신설).

글 비중이 높은 장에 그림을 더한다(사용자 요청). 그림마다 **그 페이지의 표·본문을 원본으로
읽어** 그리므로, 표를 고친 뒤 이 스크립트를 다시 돌리면 그림이 따라온다. 표는 그대로 남아
그림의 「표로 보기」 역할을 한다.

| 그림 | 넣는 곳 | 원본 |
|---|---|---|
| 3-1 서비스 흐름 | 3장 1)절 끝 | 3장 1)·2)절 본문 — 원본 표가 없어 아래 `FLOW` 상수 |
| 5-1 요구사항 상태 | 5장 맨 앞 | 5장 요약표의 상태 기호(`gen_metrics.parse_reqs`) |
| 7-1 스프린트 로드맵 | 7장 「스프린트 로드맵」 | 7장 로드맵 표 |
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


def main():
    p03, p05, p07, pe = (CH / "03-서비스제안.markdown", CH / "05-요구사항분석.markdown",
                         CH / "07-개발구현계획.markdown", CH / "부록E-결정기록.markdown")
    inject(p03, "service-flow", fig_flow(), r"^## 2\) 주요 기능$", "before")
    inject(p05, "req-status", fig_reqs(p05.read_text(encoding="utf-8")), r"^## 1\) 기능 요구사항$", "before")
    inject(p07, "roadmap", fig_roadmap(p07.read_text(encoding="utf-8")), r"^### 스프린트 로드맵$", "after")
    inject(pe, "decisions", fig_decisions(pe.read_text(encoding="utf-8")), r"^## 한눈에 보기 \(시간순\)$", "after")
    print("ok")


if __name__ == "__main__":
    main()
