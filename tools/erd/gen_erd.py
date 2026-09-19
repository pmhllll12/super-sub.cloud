"""부록 D 의 ERD 그림을 **실제 스키마에서** 만든다.

입력: dump_schema.py 가 fastapi/.venv 로 뽑은 schema.json (ORM 메타데이터).
출력: assets/erd/ 의 도메인별 SVG 7장 + 한눈에 보기 + 삭제 연쇄.

그림은 손으로 고치지 않는다 — 스키마가 바뀌면 두 스크립트를 다시 돌린다.
"""

import collections
import json
import sys
from pathlib import Path

# 🔴 저장소 루트는 이 파일 위치에서 구한다 — 절대경로를 박지 않는다(`tools/README.md`).
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets/erd"
schema = json.load(open(sys.argv[1], encoding="utf-8"))

INK, INK2, LINE, HEAD, BG = "#27262b", "#5c5962", "#8f8a7e", "#ebe8df", "#ffffff"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'D2Coding',monospace"

DOMAINS = {  # 컨텍스트 → (번호, 이름, 파일)
    "user": ("①", "사용자·팀", "domain1-user-team.svg"),
    "analysis": ("②", "영상·분석", "domain2-video-analysis.svg"),
    "card": ("③", "카드·호칭", "domain3-card-title.svg"),
    "match": ("④", "매칭", "domain4-matching.svg"),
    "review": ("⑤", "평가·신뢰", "domain5-review-trust.svg"),
    "billing": ("⑥", "과금", "domain6-billing.svg"),
    "notification": ("⑦", "알림", "domain7-notification.svg"),
}

FS, CW = 12, 7.3          # 컬럼 글자 크기 · 고정폭 글자 폭(넉넉히)
HEAD_H, ROW_H = 28, 20
COL_GAP, ROW_GAP = 96, 24


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def txt_w(s, size):
    w = 0.0
    for ch in s:
        if "가" <= ch <= "힣" or ch in "①②③④⑤⑥⑦":
            w += size * 1.0
        else:
            w += size * 0.62
    return w


class Box:
    def __init__(self, name, stub=False):
        self.name, self.stub = name, stub
        t = schema[name]
        if stub:
            num, dname, _ = DOMAINS[t["context"]]
            self.title = name
            self.sub = f"{num} {dname}"
            self.rows = []
            self.w = max(txt_w(name, 13) + 28, txt_w(self.sub, 11) + 28, 150)
            self.h = HEAD_H + 18
        else:
            uniq_single = {u[0] for u in t["uniques"] if len(u) == 1}
            self.rows = []
            for c in t["columns"]:
                mark = []
                if c["pk"]:
                    mark.append("PK")
                if c["fk"]:
                    mark.append("FK")
                if c["name"] in uniq_single and not c["pk"]:
                    mark.append("UQ")
                typ = c["type"] + ("?" if c["nullable"] and not c["pk"] else "")
                self.rows.append((" ".join(mark), c["name"], typ))
            mw = max((len(m) for m, _, _ in self.rows), default=0)
            nw = max(len(n) for _, n, _ in self.rows)
            tw = max(len(ty) for _, _, ty in self.rows)
            self.mark_w = max(mw, 2) * CW + 10
            self.name_w = nw * CW
            self.w = max(12 + self.mark_w + self.name_w + 22 + tw * CW + 12, txt_w(name, 13) + 30)
            self.h = HEAD_H + ROW_H * len(self.rows) + 6
        self.x = self.y = 0

    def row_y(self, col):
        if self.stub:
            return self.y + self.h / 2
        for i, (_, n, _) in enumerate(self.rows):
            if n == col:
                return self.y + HEAD_H + ROW_H * i + ROW_H / 2 + 3
        return self.y + HEAD_H / 2

    def svg(self):
        x, y, w, h = self.x, self.y, self.w, self.h
        if self.stub:
            return (
                f'<g><title>{self.name} — {self.sub} 도메인의 테이블(여기서는 참조만)</title>'
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="6" fill="{BG}" stroke="{LINE}" stroke-width="1.3" stroke-dasharray="5 4"/>'
                f'<text x="{x + w / 2:.1f}" y="{y + 20:.1f}" text-anchor="middle" font-family="{MONO}" font-size="13" font-weight="600" fill="{INK2}">{self.name}</text>'
                f'<text x="{x + w / 2:.1f}" y="{y + 37:.1f}" text-anchor="middle" font-family="{SANS}" font-size="11" fill="{INK2}">{self.sub}</text></g>'
            )
        out = [
            f'<g><title>{self.name} — 컬럼 {len(self.rows)}개</title>'
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="6" fill="{BG}" stroke="{INK2}" stroke-width="1.3"/>'
            f'<path d="M{x:.1f},{y + HEAD_H:.1f} v-{HEAD_H - 6} q0,-6 6,-6 h{w - 12:.1f} q6,0 6,6 v{HEAD_H - 6}z" fill="{HEAD}"/>'
            f'<line x1="{x:.1f}" y1="{y + HEAD_H:.1f}" x2="{x + w:.1f}" y2="{y + HEAD_H:.1f}" stroke="{INK2}" stroke-width="1"/>'
            f'<text x="{x + 12:.1f}" y="{y + 19:.1f}" font-family="{MONO}" font-size="13" font-weight="700" fill="{INK}">{self.name}</text>'
        ]
        for i, (mark, n, typ) in enumerate(self.rows):
            ry = y + HEAD_H + ROW_H * i + 16
            if i % 2 == 1:
                out.append(f'<rect x="{x + 1:.1f}" y="{ry - 14:.1f}" width="{w - 2:.1f}" height="{ROW_H}" fill="#f7f6f2"/>')
            if mark:
                out.append(f'<text x="{x + 12:.1f}" y="{ry:.1f}" font-family="{MONO}" font-size="10" font-weight="700" fill="{INK2}">{mark}</text>')
            weight = ' font-weight="600"' if "PK" in mark else ""
            out.append(f'<text x="{x + 12 + self.mark_w:.1f}" y="{ry:.1f}" font-family="{MONO}" font-size="{FS}" fill="{INK}"{weight}>{esc(n)}</text>')
            out.append(f'<text x="{x + w - 12:.1f}" y="{ry:.1f}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{INK2}">{esc(typ)}</text>')
        out.append("</g>")
        return "".join(out)


GEO = {}


def corridor_path(child, parent, x1, y1, x2, y2):
    """두 열 이상 건너는 선을 상자 사이 빈 통로로 돌린다 — 가운데 상자 뒤로 지나가면
    그 상자에서 나오는 관계처럼 보이기 때문이다."""
    cp, cc = GEO["col_of"][parent.name], GEO["col_of"][child.name]
    k = GEO["track"]
    GEO["track"] += 1
    off = ((k % 9) - 4) * 5
    xa = GEO["col_right"][cp] + COL_GAP / 2 + off
    xb = GEO["col_left"][cc] - COL_GAP / 2 + off
    free = [(40.0, GEO["height"] - 60.0)]
    for c in range(cp + 1, cc):
        spans, last = [], 40.0
        for b in sorted(GEO["col_boxes"][c], key=lambda b: b.y):
            spans.append((last, b.y - 8))
            last = b.y + b.h + 8
        spans.append((last, GEO["height"] - 60.0))
        free = [(max(a0, b0), min(a1, b1)) for a0, a1 in free for b0, b1 in spans if min(a1, b1) - max(a0, b0) > 4]
    target = (y1 + y2) / 2
    best = min(free, key=lambda sp: 0 if sp[0] <= target <= sp[1] else min(abs(target - sp[0]), abs(target - sp[1])))
    ym = min(max(target, best[0] + 3 + (k % 3) * 3), best[1] - 3)
    return f"M{x2 + 18:.1f},{y2:.1f} H{xa:.1f} V{ym:.1f} H{xb:.1f} V{y1:.1f} H{x1 - 14:.1f}"


def crow_edges(child, fk, parent, boxes):
    """자식 쪽 = 많음(유일하면 하나) · 0 이상 / 부모 쪽 = 정확히 하나(NULL 허용이면 0 또는 하나)."""
    t = schema[child.name]
    col = fk["cols"][0]
    nullable = any(c["nullable"] for c in t["columns"] if c["name"] in fk["cols"])
    unique = any(sorted(u) == sorted(fk["cols"]) for u in t["uniques"])
    x1, y1 = child.x, child.row_y(col)
    target_col = fk["target_cols"][0]
    same = parent is child
    if same:
        x1 = child.x + child.w
        x2, y2 = child.x + child.w, child.row_y(target_col)
        path = f"M{x1 + 14:.1f},{y1:.1f} C{x1 + 60:.1f},{y1:.1f} {x2 + 60:.1f},{y2:.1f} {x2 + 18:.1f},{y2:.1f}"
        cx_dir = 1
    else:
        x2, y2 = parent.x + parent.w, parent.row_y(target_col)
        if GEO["col_of"][child.name] - GEO["col_of"][parent.name] > 1:
            path = corridor_path(child, parent, x1, y1, x2, y2)
        else:
            path = f"M{x1 - 14:.1f},{y1:.1f} C{x1 - 60:.1f},{y1:.1f} {x2 + 60:.1f},{y2:.1f} {x2 + 18:.1f},{y2:.1f}"
        cx_dir = -1
    g = [f'<g><title>{child.name}.{", ".join(fk["cols"])} → {parent.name} (ON DELETE {fk["ondelete"]})</title>',
         f'<path d="{path}" fill="none" stroke="transparent" stroke-width="10"/>',
         f'<path d="{path}" fill="none" stroke="{LINE}" stroke-width="1.2"/>']
    # 자식 쪽 표식
    d = cx_dir
    tip = x1 + d * 14
    if unique:
        g.append(f'<line x1="{x1 + d * 7:.1f}" y1="{y1 - 6:.1f}" x2="{x1 + d * 7:.1f}" y2="{y1 + 6:.1f}" stroke="{LINE}" stroke-width="1.2"/>')
    else:
        for dy in (-6, 0, 6):
            g.append(f'<line x1="{tip:.1f}" y1="{y1:.1f}" x2="{x1:.1f}" y2="{y1 + dy:.1f}" stroke="{LINE}" stroke-width="1.2"/>')
    g.append(f'<circle cx="{x1 + d * 18:.1f}" cy="{y1:.1f}" r="3.5" fill="{BG}" stroke="{LINE}" stroke-width="1.2"/>')
    # 부모 쪽 표식
    g.append(f'<line x1="{x2 + 7:.1f}" y1="{y2 - 6:.1f}" x2="{x2 + 7:.1f}" y2="{y2 + 6:.1f}" stroke="{LINE}" stroke-width="1.2"/>')
    if nullable:
        g.append(f'<circle cx="{x2 + 14:.1f}" cy="{y2:.1f}" r="3.5" fill="{BG}" stroke="{LINE}" stroke-width="1.2"/>')
    else:
        g.append(f'<line x1="{x2 + 12:.1f}" y1="{y2 - 6:.1f}" x2="{x2 + 12:.1f}" y2="{y2 + 6:.1f}" stroke="{LINE}" stroke-width="1.2"/>')
    g.append("</g>")
    return "".join(g)


LEG1 = "PK 기본키 · FK 외래키 · UQ 유일 · 타입 끝 ? = NULL 허용 · 점선 상자 = 다른 도메인(참조만)"
LEG2 = "선: 까마귀발 쪽 = 여럿 · 두 줄 = 반드시 하나 · 원 = 없을 수도 있음 · 선에 마우스를 올리면 삭제 규칙"


def legend(y, x=24):
    return (f'<text x="{x}" y="{y - 18}" font-family="{SANS}" font-size="12" fill="{INK}">{LEG1}</text>'
            f'<text x="{x}" y="{y}" font-family="{SANS}" font-size="12" fill="{INK}">{LEG2}</text>')


def domain_svg(ctx):
    owned = sorted(t for t, v in schema.items() if v["context"] == ctx)
    stubs = sorted({f["target"] for t in owned for f in schema[t]["fks"] if schema[f["target"]]["context"] != ctx})
    boxes = {t: Box(t) for t in owned}
    boxes.update({t: Box(t, stub=True) for t in stubs})

    parents = collections.defaultdict(set)
    for t in owned:
        for f in schema[t]["fks"]:
            if f["target"] != t:
                parents[t].add(f["target"])
    base = 1 if stubs else 0
    memo = {}

    def lv(t, seen=()):
        if t in stubs:
            return 0
        if t in memo:
            return memo[t]
        ps = [p for p in parents[t] if p in owned and p not in seen]
        memo[t] = base if not ps else 1 + max(lv(p, seen + (t,)) for p in ps)
        return memo[t]

    level = {s: 0 for s in stubs}
    level.update({t: lv(t) for t in owned})

    cols = collections.defaultdict(list)
    for t, lv in level.items():
        cols[lv].append(t)
    ordered_cols = sorted(cols)
    ypos = {}
    GEO.clear()
    GEO["track"] = 0
    x = 24
    col_x = {}
    for lv in ordered_cols:
        names = cols[lv]
        if lv == ordered_cols[0]:
            names.sort(key=lambda n: (-sum(1 for t in owned for f in schema[t]["fks"] if f["target"] == n), n))
        else:
            def bary(n):
                ys = [ypos[p] for p in parents[n] if p in ypos]
                return (sum(ys) / len(ys)) if ys else 1e9
            names.sort(key=lambda n: (bary(n), n))
        y = 64
        cw = max(boxes[n].w for n in names)
        for n in names:
            b = boxes[n]
            b.x, b.y = x, y
            ypos[n] = y + b.h / 2
            y += b.h + ROW_GAP
        col_x[lv] = x
        GEO.setdefault("col_left", {})[lv] = x
        GEO.setdefault("col_right", {})[lv] = x + cw
        GEO.setdefault("col_boxes", {})[lv] = [boxes[n] for n in names]
        for n in names:
            GEO.setdefault("col_of", {})[n] = lv
        x += cw + COL_GAP
    width = x - COL_GAP + 60
    height = max(b.y + b.h for b in boxes.values()) + 56
    GEO["height"] = height

    num, dname, _ = DOMAINS[ctx]
    height += 18
    width = max(width, 24 + max(txt_w(LEG1, 12), txt_w(LEG2, 12)) + 24)
    body = [f'<rect x="0" y="0" width="{width:.0f}" height="{height:.0f}" fill="{BG}"/>',
            f'<text x="24" y="34" font-family="{SANS}" font-size="17" font-weight="700" fill="{INK}">{num} {dname}</text>',
            f'<text x="{24 + txt_w(num + " " + dname, 17) + 14:.0f}" y="34" font-family="{SANS}" font-size="12" fill="{INK2}">테이블 {len(owned)}개 · 실제 스키마에서 생성</text>']
    for t in owned:
        for f in schema[t]["fks"]:
            body.append(crow_edges(boxes[t], f, boxes[f["target"]], boxes))
    for b in boxes.values():
        body.append(b.svg())
    body.append(legend(height - 22))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {height:.0f}" width="{width:.0f}" height="{height:.0f}" '
           f'role="img" aria-label="{num} {dname} 도메인 ERD — 테이블 {len(owned)}개">' + "".join(body) + "</svg>")
    (OUT / DOMAINS[ctx][2]).write_text(svg, encoding="utf-8", newline="\n")
    return int(width), int(height), len(owned), stubs


# --- 한눈에 보기 --------------------------------------------------------------
def overview_svg():
    pos = {"user": (300, 170), "analysis": (40, 40), "billing": (40, 170), "notification": (40, 300),
           "card": (560, 40), "review": (560, 170), "match": (560, 300)}
    W, H = 140, 62
    pair = collections.Counter()
    for t, v in schema.items():
        for f in v["fks"]:
            a, b = v["context"], schema[f["target"]]["context"]
            if a != b:
                pair[(a, b)] += 1
    counts = collections.Counter(v["context"] for v in schema.values())
    body = [f'<rect x="0" y="0" width="740" height="420" fill="{BG}"/>',
            f'<defs><marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{INK2}"/></marker></defs>']

    def anchor(ctx, toward):
        x, y = pos[ctx]
        tx, ty = pos[toward]
        cx, cy = x + W / 2, y + H / 2
        tcx, tcy = tx + W / 2, ty + H / 2
        if abs(tcx - cx) > abs(tcy - cy) * 2:
            return (x + W if tcx > cx else x, cy)
        return (cx, y + H if tcy > cy else y)

    for (a, b), n in sorted(pair.items()):
        x1, y1 = anchor(a, b)
        x2, y2 = anchor(b, a)
        if (a, b) == ("review", "match"):
            x1, y1, x2, y2 = 630, 232, 630, 298
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        body.append(f'<g><title>{DOMAINS[a][1]} → {DOMAINS[b][1]}: 외래키 {n}개</title>'
                    f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{INK2}" stroke-width="1.4" marker-end="url(#ar)"/>'
                    f'<rect x="{mx - 13:.1f}" y="{my - 10:.1f}" width="26" height="18" rx="9" fill="{BG}" stroke="{LINE}" stroke-width="1"/>'
                    f'<text x="{mx:.1f}" y="{my + 4:.1f}" text-anchor="middle" font-family="{SANS}" font-size="11.5" font-weight="600" fill="{INK}">{n}</text></g>')
    for ctx, (x, y) in pos.items():
        num, dname, _ = DOMAINS[ctx]
        body.append(f'<g><title>{num} {dname} — 테이블 {counts[ctx]}개</title>'
                    f'<rect x="{x}" y="{y}" width="{W}" height="{H}" rx="8" fill="{HEAD if ctx == "user" else "#f6f5f1"}" stroke="{INK2}" stroke-width="1.5"/>'
                    f'<text x="{x + W / 2}" y="{y + 27}" text-anchor="middle" font-family="{SANS}" font-size="14" font-weight="700" fill="{INK}">{num} {dname}</text>'
                    f'<text x="{x + W / 2}" y="{y + 46}" text-anchor="middle" font-family="{SANS}" font-size="12" fill="{INK2}">테이블 {counts[ctx]}개</text></g>')
    total = sum(pair.values())
    to_user = sum(n for (a, b), n in pair.items() if b == "user")
    body.append(f'<text x="24" y="392" font-family="{SANS}" font-size="12" fill="{INK}">화살표 = 외래키가 가리키는 방향(참조하는 도메인 → 참조되는 도메인) · 숫자 = 외래키 개수</text>')
    body.append(f'<text x="24" y="410" font-family="{SANS}" font-size="12" fill="{INK}">도메인을 넘는 외래키 {total}개 중 {to_user}개가 ① 사용자·팀을 향한다</text>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 740 420" width="740" height="420" role="img" '
           f'aria-label="도메인 7개와 도메인을 넘는 외래키. 대부분이 사용자·팀 도메인을 향한다.">' + "".join(body) + "</svg>")
    (OUT / "d1-overview.svg").write_text(svg, encoding="utf-8", newline="\n")
    return total, to_user, pair


# --- 삭제 연쇄 ----------------------------------------------------------------
def cascade_svg():
    kids = collections.defaultdict(list)
    for t, v in schema.items():
        for f in v["fks"]:
            if f["ondelete"] == "CASCADE":
                kids[f["target"]].append(t)
    rows = []

    def walk(n, depth, seen):
        rows.append((n, depth))
        for c in sorted(kids[n]):
            if c not in seen:
                seen.add(c)
                walk(c, depth + 1, seen)

    walk("user", 0, {"user"})
    tree = {n for n, _ in rows}
    setnull, block = [], collections.defaultdict(list)
    for t, v in schema.items():
        for f in v["fks"]:
            if f["target"] not in tree:
                continue
            if f["ondelete"] == "SET NULL":
                setnull.append((t, f["cols"], f["target"]))
            elif f["ondelete"] in ("NO ACTION", "RESTRICT") and t not in tree:
                block[t].append(f"{', '.join(f['cols'])} → {f['target']}")
    y0, rh = 58, 24
    body = [f'<text x="24" y="32" font-family="{SANS}" font-size="15" font-weight="700" fill="{INK}">계정(user)을 지우면 함께 지워지는 것 — ON DELETE CASCADE</text>']
    video_rows = [i for i, (n, _) in enumerate(rows) if n == "video"]
    for i, (n, depth) in enumerate(rows):
        y = y0 + i * rh
        x = 36 + depth * 26
        if depth:
            body.append(f'<path d="M{x - 18},{y - rh + 8} V{y - 4} H{x - 4}" fill="none" stroke="{LINE}" stroke-width="1.2"/>')
        body.append(f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="12.5" fill="{INK}"{" font-weight=\"700\"" if n in ("user", "video") else ""}>{n}</text>')
    if video_rows:
        vi = video_rows[0]
        vdepth = rows[vi][1]
        end = vi
        while end + 1 < len(rows) and rows[end + 1][1] > vdepth:
            end += 1
        ya, yb = y0 + vi * rh - 14, y0 + end * rh + 6
        body.append(f'<rect x="{36 + vdepth * 26 - 10}" y="{ya}" width="330" height="{yb - ya}" rx="6" fill="none" stroke="{INK2}" stroke-width="1.2" stroke-dasharray="5 4"/>')
        body.append(f'<text x="{36 + vdepth * 26 + 330 - 16}" y="{ya + 16}" text-anchor="end" font-family="{SANS}" font-size="11.5" fill="{INK2}">영상 한 편을 지울 때도 이 가지(SEC-006)</text>')
    rx = 420
    yy = y0
    body.append(f'<text x="{rx}" y="{yy}" font-family="{SANS}" font-size="13" font-weight="700" fill="{INK}">지우지 않고 비우는 것 — SET NULL</text>')
    for t, c, tg in setnull:
        yy += 22
        body.append(f'<text x="{rx}" y="{yy}" font-family="{MONO}" font-size="12" fill="{INK}">{t}.{", ".join(c)} → {tg}</text>')
    yy += 40
    body.append(f'<text x="{rx}" y="{yy}" font-family="{SANS}" font-size="13" font-weight="700" fill="{INK}">계정 삭제를 막는 기록 — NO ACTION</text>')
    for t in sorted(block):
        yy += 22
        for item in block[t]:
            body.append(f'<text x="{rx}" y="{yy}" font-family="{MONO}" font-size="12" fill="{INK}">{t}.{item}</text>')
            yy += 20
        yy -= 20
    if block:
        yy += 26
        body.append(f'<text x="{rx}" y="{yy}" font-family="{SANS}" font-size="11.5" fill="{INK2}">이 기록이 남아 있으면 DB 가 계정 행 삭제를 거부한다(D.8)</text>')
    else:
        yy += 22
        body.append(f'<text x="{rx}" y="{yy}" font-family="{SANS}" font-size="12" fill="{INK2}">없음 — 2026-09-17 에 규칙을 정했다</text>')
    h = max(y0 + len(rows) * rh, yy) + 30
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 740 {h}" width="740" height="{h}" role="img" '
           f'aria-label="계정을 지우면 함께 지워지는 테이블의 나무, 비우는 외래키, 삭제를 막는 기록.">'
           f'<rect x="0" y="0" width="740" height="{h}" fill="{BG}"/>' + "".join(body) + "</svg>")
    (OUT / "d6-cascade.svg").write_text(svg, encoding="utf-8", newline="\n")
    return rows, setnull, dict(block)


if __name__ == "__main__":
    sizes = {ctx: domain_svg(ctx) for ctx in DOMAINS}
    for ctx, (w, h, n, stubs) in sizes.items():
        print(f"{DOMAINS[ctx][2]:30} {w}x{h} · 테이블 {n} · 참조 {stubs}")
    print("한눈에:", overview_svg()[:2])
    rows, setnull, block = cascade_svg()
    print("연쇄 행", len(rows), "· SET NULL", setnull, "· 막는 기록", block)
