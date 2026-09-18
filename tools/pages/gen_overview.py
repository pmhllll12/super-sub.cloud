"""「프로젝트 전체 그림」·「진행 현황」 페이지 생성기 (2026-09-17 사이트 재편으로 둘로 나눔).

수치는 2026-09-17 저장소에서 확인한 값이다(페이지 하단에 다시 뽑는 명령을 둔다).
색은 dataviz 검증기를 --pairs all 로 통과한 네 색이다.
"""

from pathlib import Path

# 🔴 저장소 루트를 **이 파일 위치에서** 구한다(`tools/pages/x.py` → 두 단계 위).
#    절대경로를 박으면 만든 사람 PC 에서만 돌고, 남의 PC 에서는 오류도 없이
#    엉뚱한 곳에 쓰거나 안 쓴다.
ROOT = Path(__file__).resolve().parents[2]

INK = "#27262b"      # Just the Docs 제목 글자색
INK2 = "#5c5962"     # 본문 보조
GRID = "#d9d7d0"
PEOPLE = [  # 팀 CLAUDE.md 의 팀 구성 순서 = 고정 색 순서
    ("박민호", "PM", "#2a78d6"),
    ("백성검", "프론트·웹", "#eb6834"),
    ("정어진", "백엔드·파이프라인", "#1baf7a"),
    ("정상호", "AI 에이전트", "#4a3aa7"),
]
COLOR = {n: c for n, _, c in PEOPLE}

FONT = "font-family=\"-apple-system,BlinkMacSystemFont,'Segoe UI','Apple SD Gothic Neo','Noto Sans KR',sans-serif\""


def box(x, y, w, h, title, sub, owner, dashed=False):
    c = COLOR[owner]
    dash = ' stroke-dasharray="6 4"' if dashed else ""
    cx = x + w / 2
    return (
        f'<g><title>{title} — {sub} · 담당 {owner}</title>'
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{c}" fill-opacity="0.10" stroke="{c}" stroke-width="2"{dash}/>'
        f'<text x="{cx}" y="{y + 22}" text-anchor="middle" font-size="14" font-weight="600" fill="{INK}">{title}</text>'
        f'<text x="{cx}" y="{y + 39}" text-anchor="middle" font-size="11.5" fill="{INK2}">{sub}</text>'
        f'<text x="{cx}" y="{y + 54}" text-anchor="middle" font-size="11" fill="{INK2}">{owner}</text></g>'
    )


def arrow(x1, y1, x2, y2, both=False):
    start = ' marker-start="url(#ah-s)"' if both else ""
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{INK2}" stroke-width="1.5" marker-end="url(#ah)"{start}/>'
    )


def label(x, y, text, anchor="middle"):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="11" fill="{INK2}">{text}</text>'


DEFS = (
    f'<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
    f'<path d="M0,0 L10,5 L0,10 z" fill="{INK2}"/></marker>'
    f'<marker id="ah-s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
    f'<path d="M0,0 L10,5 L0,10 z" fill="{INK2}"/></marker></defs>'
)


def _text_w(t, size=12):
    w = 0.0
    for ch in t:
        if "\uac00" <= ch <= "\ud7a3":
            w += size * 0.95
        elif ch in " ·":
            w += size * 0.32
        else:
            w += size * 0.58
    return w


def legend(y, x0=20, extra=None, only=None):
    parts, x = [], x0
    for name, role, c in PEOPLE:
        if only and name not in only:
            continue
        label_t = f"{name} · {role}"
        parts.append(
            f'<rect x="{x}" y="{y - 10}" width="12" height="12" rx="3" fill="{c}"/>'
            f'<text x="{x + 18}" y="{y}" font-size="12" fill="{INK}">{label_t}</text>'
        )
        x += 18 + _text_w(label_t) + 26
    if extra:
        parts.append(extra(x))
    return "".join(parts)


def figure(svg_body, w, h, aria, caption):
    svg = (
        f'<svg viewBox="0 0 {w} {h}" width="{w}" role="img" aria-label="{aria}" {FONT} '
        f'style="max-width:100%;height:auto;display:block">{svg_body}</svg>'
    )
    return (
        '<figure class="doc-figure">'
        f"{svg}"
        f'<figcaption class="doc-figure-caption">{caption}</figcaption>'
        "</figure>"
    )


# --- 1) 구성도 ---------------------------------------------------------------
def fig_architecture():
    b = [DEFS]
    b.append(f'<g><title>사용자</title><rect x="20" y="167" width="90" height="46" rx="23" fill="none" stroke="{INK2}" stroke-width="1.5"/>'
             f'<text x="65" y="195" text-anchor="middle" font-size="14" font-weight="600" fill="{INK}">사용자</text></g>')
    b.append(box(345, 24, 140, 62, "객체 저장소", "AWS S3 · 원본·리포트", "정어진"))
    b.append(box(530, 24, 150, 62, "분석 워커", "GPU · 쓸 때만 켬", "정상호"))
    b.append(box(150, 112, 150, 62, "웹", "Next.js · Vercel", "백성검"))
    b.append(box(150, 206, 150, 62, "앱", "Flutter · 초기 단계", "백성검", dashed=True))
    b.append(box(345, 159, 140, 62, "앞단", "Cloudflare → nginx", "박민호"))
    b.append(box(530, 159, 150, 62, "API 서버", "FastAPI · k3s · 7개 도메인", "정어진"))
    b.append(box(720, 159, 120, 62, "Gemini", "용병 검색 임베딩", "박민호"))
    b.append(box(530, 290, 150, 62, "DB", "PostgreSQL + pgvector", "정어진"))
    b += [
        arrow(110, 182, 150, 150), arrow(110, 198, 150, 232),
        arrow(300, 150, 345, 182), arrow(300, 232, 345, 198), label(322, 195, "호출"),
        arrow(485, 190, 530, 190),
        arrow(605, 221, 605, 290), label(613, 262, "읽기·쓰기", "start"),
        arrow(680, 190, 720, 190), label(700, 182, "임베딩"),
        arrow(570, 86, 452, 159), label(532, 128, "작업 가져가기 · 완료 보고", "start"),
        arrow(530, 55, 485, 55, both=True), label(507, 16, "원본·리포트"),
        arrow(225, 112, 345, 70), label(262, 78, "원본 직접 업로드", "end"),
    ]
    b.append(legend(382, extra=lambda x: (
        f'<rect x="{x}" y="372" width="22" height="12" rx="3" fill="none" stroke="{INK2}" stroke-width="1.5" stroke-dasharray="5 3"/>'
        f'<text x="{x + 28}" y="382" font-size="12" fill="{INK}">점선 = 초기 단계</text>')))
    return figure(
        "".join(b), 860, 395,
        "전체 구성도: 사용자는 웹과 앱으로 들어오고, 요청은 앞단(Cloudflare, nginx)을 지나 API 서버로 간다. API 서버는 DB와 Gemini를 쓰고, 원본 영상은 객체 저장소로 직접 올라간다. GPU 분석 워커는 앞단을 거쳐 작업을 가져가고 결과를 저장소에 올린다.",
        "그림 1. 지금 실제로 돌아가는 구성(2026-09-17). 색은 그 부분을 만든 사람이다. "
        "원본 영상은 API 서버를 거치지 않고 저장소로 바로 가고, 무거운 분석은 GPU 워커가 따로 가져가 처리한다. "
        "워커도 API를 부를 때 앞단을 지난다 — 09-17의 장애가 바로 이 화살표에서 났다(4절).",
    )


# --- 2) 영상 한 편의 흐름 ----------------------------------------------------
def fig_flow():
    steps = [
        ("올린다", "웹·앱에서 촬영 영상", "백성검", "원본은 저장소로 직접"),
        ("검사한다", "길이·화질 규칙", "정어진", "반려돼도 기록은 남김"),
        ("줄 세운다", "분석 작업 대기열", "정어진", "같은 영상은 앞 결과 재사용"),
        ("분석한다", "자세 → 특징 → 채점", "정상호", "GPU · 루브릭 채점"),
        ("적재한다", "리포트를 DB로", "정어진", "봉투 규격을 계약으로 고정"),
        ("보여준다", "카드·등급·추천 판", "백성검", "남에게는 좁은 칸만"),
    ]
    arrows_txt = ["등록", "통과", "가져감", "리포트", "조회"]
    w, gap, x0, y = 122, 26, 12, 40
    b = [DEFS]
    for i, (t, sub, owner, note) in enumerate(steps):
        x = x0 + i * (w + gap)
        b.append(box(x, y, w, 62, t, sub, owner))
        b.append(f'<text x="{x + w / 2}" y="{y + 84}" text-anchor="middle" font-size="11" fill="{INK2}">{note}</text>')
        if i < len(steps) - 1:
            ax = x + w
            b.append(arrow(ax + 2, y + 31, ax + gap - 2, y + 31))
            b.append(label(ax + gap / 2, y - 8, arrows_txt[i]))
    b.append(legend(160, only={o for _, _, o, _ in steps}))
    return figure(
        "".join(b), 880, 172,
        "영상 한 편의 흐름: 올린다, 검사한다, 줄 세운다, 분석한다, 적재한다, 보여준다의 여섯 단계. 색은 그 단계를 만든 사람이다.",
        "그림 2. 영상 한 편이 추천 판의 카드가 되기까지. 여섯 단계 중 셋(검사·대기열·적재)이 백엔드이고, "
        "각 단계 아래 줄은 그 자리에서 내린 판단 하나다.",
    )


# --- 3) 진행 막대 + 전환점 --------------------------------------------------
MILESTONES = [  # (시작일로부터 일수, 날짜, 무엇, 누가)
    (4, "08-24", "저장소 시작 · 사람별 브랜치로 일하기로", "팀"),
    (5, "08-25", "측정과 판단을 나눔 — 영상을 언어 모델에 직접 넣지 않음", "정상호"),
    (6, "08-26", "역할 재배정 · 지원 종목 10종 → 3종", "팀"),
    (13, "09-02", "AWS 단일 서버에 첫 배포", "정어진"),
    (15, "09-04", "분석 워커가 작업을 직접 가져가는 방식 · 평가·신뢰 기능", "정어진·박민호"),
    (19, "09-08", "main 통합 · 과금 기능", "박민호"),
    (21, "09-10", "리포트 봉투를 계약으로 고정 · 용병 검색", "정상호·박민호"),
    (22, "09-11", "API 서버를 k3s로 전환 · 분석을 축구 한 종목으로", "박민호·정상호"),
    (27, "09-16", "호칭은 분석이 아니라 사람이 적기로", "백성검·정어진"),
    (28, "09-17", "지도자 검수 없이 진행 결정 · 앞단 무음 장애 발견", "정상호·정어진"),
]
TODAY = 28
TOTAL_DAYS = 69


def fig_timeline():
    x0, x1 = 20, 840
    sx = (x1 - x0) / TOTAL_DAYS
    X = lambda d: round(x0 + d * sx, 1)
    sprints = [(0, 12, "스프린트 1", "08-20"), (12, 26, "스프린트 2", "09-01"),
               (26, 40, "스프린트 3", "09-15"), (40, 54, "스프린트 4", "09-29"),
               (54, 69, "스프린트 5", "10-13")]
    b = []
    by, bh = 66, 30
    for s, e, name, date in sprints:
        cut = TODAY + 1  # 오늘 하루까지 지나온 기간에 넣는다
        left, right = X(s) + 1, X(e) - 1
        if s < cut:
            mid = min(X(min(e, cut)), right)
            b.append(f'<rect x="{left}" y="{by}" width="{round(mid - left, 1)}" height="{bh}" fill="#cfccc2"/>')
        if e > cut:
            ms = max(X(max(s, cut)), left)
            b.append(f'<rect x="{ms}" y="{by}" width="{round(right - ms, 1)}" height="{bh}" fill="#efede7"/>')
        b.append(f'<text x="{(X(s) + X(e)) / 2}" y="{by + 20}" text-anchor="middle" font-size="12" fill="{INK}">{name}</text>')
        b.append(f'<text x="{X(s) + 2}" y="{by + bh + 16}" font-size="10.5" fill="{INK2}">{date}</text>')
    b.append(f'<text x="{x1}" y="{by + bh + 16}" text-anchor="end" font-size="10.5" fill="{INK2}">10-27</text>')
    for i, (d, date, what, who) in enumerate(MILESTONES, start=1):
        x = X(d) + sx / 2
        b.append(f'<g><title>{i}. {date} — {what} ({who})</title>'
                 f'<line x1="{x}" y1="{44}" x2="{x}" y2="{by}" stroke="{INK2}" stroke-width="1"/>'
                 f'<circle cx="{x}" cy="{44}" r="4.5" fill="{INK}"/>'
                 f'<text x="{x}" y="{32}" text-anchor="middle" font-size="10.5" fill="{INK}">{i}</text></g>')
    tx = X(TODAY + 1)
    b.append(f'<line x1="{tx}" y1="{by - 6}" x2="{tx}" y2="{by + bh + 22}" stroke="{INK}" stroke-width="2"/>')
    b.append(f'<text x="{tx + 5}" y="{by + bh + 34}" font-size="11.5" font-weight="600" fill="{INK}">오늘 09-17 · 69일 중 29일째</text>')
    return figure(
        "".join(b), 860, 150,
        "개발 기간 69일을 스프린트 다섯으로 나눈 막대. 오늘(09-17)은 스프린트 3의 사흘째로 29일째다. 위의 번호 점 열 개는 아래 표의 전환점이다.",
        "그림 1. 전체 일정에서 지금 위치와 전환점. 진한 부분이 지나온 기간이다. 번호는 아래 표와 같고, 점에 마우스를 올리면 내용이 보인다.",
    )


# --- 4) 영역별 커밋 ----------------------------------------------------------
AREAS = [  # (영역, 폴더, {사람: 커밋})
    ("문서 사이트", "jekyll", {"박민호": 177, "백성검": 40, "정어진": 168, "정상호": 207}),
    ("웹", "www", {"박민호": 35, "백성검": 281, "정어진": 14, "정상호": 0}),
    ("AI 에이전트", "agent", {"박민호": 1, "백성검": 0, "정어진": 1, "정상호": 232}),
    ("백엔드", "fastapi", {"박민호": 13, "백성검": 0, "정어진": 147, "정상호": 1}),
    ("앱", "flutter", {"박민호": 3, "백성검": 6, "정어진": 0, "정상호": 0}),
]


def fig_commits():
    lx, bx, bw_max = 20, 150, 610
    vmax = max(sum(a[2].values()) for a in AREAS)
    scale = bw_max / vmax
    b = [legend(18)]
    row_h, gap, y0 = 24, 18, 44
    for r, (area, folder, counts) in enumerate(AREAS):
        y = y0 + r * (row_h + gap)
        total = sum(counts.values())
        b.append(f'<text x="{lx}" y="{y + 16}" font-size="12.5" fill="{INK}">{area}</text>')
        b.append(f'<text x="{bx - 10}" y="{y + 16}" text-anchor="end" font-size="10.5" fill="{INK2}">{folder}/</text>')
        x = bx
        segs = [(n, counts[n]) for n, _, _ in PEOPLE if counts[n] > 0]
        for i, (name, v) in enumerate(segs):
            w = v * scale
            last = i == len(segs) - 1
            draw_w = max(w - (0 if last else 2), 1)
            c = COLOR[name]
            tip = f"<title>{area} · {name} {v}커밋</title>"
            if last and draw_w >= 8:
                r4 = 4
                d = (f"M{x:.1f},{y} h{draw_w - r4:.1f} q{r4},0 {r4},{r4} v{row_h - 2 * r4} "
                     f"q0,{r4} -{r4},{r4} h-{draw_w - r4:.1f} z")
                b.append(f'<path d="{d}" fill="{c}">{tip}</path>')
            else:
                b.append(f'<rect x="{x:.1f}" y="{y}" width="{draw_w:.1f}" height="{row_h}" fill="{c}">{tip}</rect>')
            x += w
        b.append(f'<text x="{x + 8:.1f}" y="{y + 16}" font-size="12.5" font-weight="600" fill="{INK}">{total}</text>')
    h = y0 + len(AREAS) * (row_h + gap) - gap + 8
    return figure(
        "".join(b), 860, h,
        "영역 폴더별 커밋 수를 사람별로 쌓은 막대. 문서 사이트 592, 웹 330, AI 에이전트 234, 백엔드 161, 앱 9.",
        "그림 2. 영역마다 누가 커밋했나(2026-09-17). 막대에 마우스를 올리면 사람별 수가 보이고, 아래 「표로 보기」에 같은 값이 있다. "
        "<strong>커밋 수는 일의 양이 아니다</strong> — 한 커밋의 크기가 사람·영역마다 다르다. 누가 어디에 손을 댔는지를 보는 그림이다.",
    )


def commits_table():
    rows = ["| 영역 | 폴더 | 박민호 | 백성검 | 정어진 | 정상호 | 합계 |", "|---|---|---:|---:|---:|---:|---:|"]
    for area, folder, c in AREAS:
        rows.append(f"| {area} | `{folder}/` | {c['박민호']} | {c['백성검']} | {c['정어진']} | {c['정상호']} | {sum(c.values())} |")
    return "\n".join(rows)


def tiles():
    items = [
        ("1,398", "커밋", "08-24 저장소 시작부터"),
        ("4명", "기여자", "넷 모두 300커밋 이상"),
        ("29 / 69일", "진행", "스프린트 3 사흘째 · 42%"),
        ("98 / 152", "미결 항목 해소", "팀 요청·결정의 공통 입구"),
    ]
    cells = "".join(
        '<div class="stat-tile">'
        f'<div class="stat-value">{big}</div>'
        f'<div class="stat-label">{what}</div>'
        f'<div class="stat-note">{note}</div></div>'
        for big, what, note in items
    )
    return f'<div class="stat-tiles">{cells}</div>'


def milestones_table():
    rows = ["| # | 날짜 | 전환점 | 주도 |", "|---:|---|---|---|"]
    for i, (_, date, what, who) in enumerate(MILESTONES, start=1):
        rows.append(f"| {i} | {date} | {what} | {who} |")
    return "\n".join(rows)


PAGE = f"""---
layout: default
title: 프로젝트 전체 그림
permalink: /10-프로젝트전체그림/
nav_order: 1
---

# 프로젝트 전체 그림

> 2026-09-17 기준 · 스프린트 3 진행 중. **처음 보는 분을 위한 한 장**이다 — 무엇을 만들고,
> 지금 어떻게 돌아가고, 영상 한 편이 어떻게 흘러가는지. 구조의 상세는
> [시스템 설계]({{{{ "/06-시스템설계/" | relative_url }}}}) 1절에, 지나온 길과 처음 설계에서 달라진
> 것은 [진행 현황]({{{{ "/진행-현황/" | relative_url }}}})에 있다.

## 1) 무엇을 만들고 있나

**생활체육 경기 영상을 분석해 선수의 실력을 재고, 그 근거로 팀이 빈 자리에 맞는 용병을
찾게 하는 플랫폼**이다. 선수가 영상을 올리면 동작을 재서 등급과 카드가 생기고, 팀은
포지션·시간·지역이 맞는 후보를 추천받아 초대한다. 경기가 끝나면 서로 남긴 평가가
등급 옆에 신뢰로 쌓인다.

{tiles()}

## 2) 지금 실제로 돌아가는 구성

{fig_architecture()}

- **화면**은 웹이 중심이다. 앱은 뼈대만 있고, 사용자가 쓰는 기능은 웹으로 먼저 열었다.
- **API 서버 하나가 모든 화면의 창구**다. 안쪽은 사용자·카드·영상 분석·매칭·평가·과금·알림
  일곱 도메인으로 나뉘고, 도메인끼리 코드를 끌어다 쓰지 못하게 검사로 막아 두었다.
- **무거운 분석은 따로 돈다.** GPU 워커는 켜져 있을 때만 대기열에서 작업을 가져가므로,
  API 서버는 분석이 오래 걸려도 멈추지 않는다.

## 3) 영상 한 편이 추천 판에 오르기까지

{fig_flow()}

---

더 보기: [진행 현황 →]({{{{ "/진행-현황/" | relative_url }}}}) · [백엔드 · 파이프라인 →]({{{{ "/11-백엔드파이프라인/" | relative_url }}}})

<details markdown="block">
<summary>이 페이지의 수치를 다시 뽑는 명령</summary>

```bash
git rev-list --count HEAD                                   # 커밋 수
git log --format='%an' | sort | uniq -c                     # 기여자별
grep -c '^### ' jekyll/pages/pending.markdown               # 미결 항목 전체
grep -c '^### .*✅' jekyll/pages/pending.markdown           # 그중 해소
```

git 계정 이름과 사람: `pmhllll12` 박민호 · `백성검` 백성검 · `roqkf` 정어진 · `jsangho` 정상호.

</details>

[← 목차로](/toc/)
"""

PROGRESS = f"""---
layout: default
title: 진행 현황
permalink: /진행-현황/
parent: 프로젝트 관리
nav_order: 4
---

# 진행 현황

> 2026-09-17 기준 · 스프린트 3 진행 중. **실제로 지나온 길**이다 — 일정 계획과 현재 스프린트
> 칸반은 [개발 구현 계획]({{{{ "/07-개발구현계획/" | relative_url }}}}) 4절에, 지금 돌아가는 구성은
> [프로젝트 전체 그림]({{{{ "/10-프로젝트전체그림/" | relative_url }}}})에 있다.

## 1) 우리가 지나온 길

{fig_timeline()}

{milestones_table()}

처음 2주(스프린트 1)는 **구조를 정하는 결정**이 몰렸다 — 분석을 「측정」과 「판단」으로
가르고, 백엔드를 도메인 단위로 나누고, 종목을 줄였다. 스프린트 2는 **기능을 한 줄로
잇는 기간**이었다 — 배포, 분석 워커, 평가·과금, 첫 통합. 스프린트 3에 들어서며
**운영에서 드러난 것을 바로잡는 결정**(k3s 전환, 호칭을 사람이 적기로, 검수 없이 가기로)이
늘었다.

## 2) 처음 설계에서 실물로 — 무엇이 달라졌나

| 처음 설계에서는 (시스템 설계 09-10판) | 실제로는 (09-17) | 계기 |
|---|---|---|
| 모바일 앱 + 정적 호스팅 웹 | **웹이 중심**(Next.js · Vercel), 앱은 초기 단계 | 화면 작업이 웹으로 모였다(웹 330커밋 · 앱 9커밋) |
| 백엔드 도메인 6개 | **7개** — 알림이 따로 섰다 | 팀 초대·경기 신청·지인 요청이 모두 알림을 필요로 했다 |
| 리포트 적재·조회는 스프린트 3에서 | **구현됨** — 등급·카드 불릿·추천 판까지 이어짐 | 리포트 봉투를 계약으로 고정했다(09-10) |
| API 서버는 systemd, k3s 전환 진행 중 | **k3s로 전환 완료** | 09-11 트래픽 전환 |
| 앞단은 적혀 있지 않음 | **Cloudflare → nginx** | 09-17 분석 워커가 앞단에 막힌 장애로 드러났다 |
| 종목 10종(제안) | **3종 → 실제 분석은 축구 한 종목** | 08-26 축소, 09-11 에이전트를 축구로 정리 |
| 지도자 검수 뒤 확정 점수 | **검수 없이 진행, 결과에 「검수 전」 표시 유지** | 09-17 남은 기간을 보고 결정 |
| pgvector 로 성향 비교 | 용병 검색에는 쓰임, **선수 성향 벡터는 아직** | 채울 재료(누적 분석)가 먼저 필요하다 |

## 3) 누가 어디를 만들었나

{fig_commits()}

<details markdown="block">
<summary>표로 보기</summary>

{commits_table()}

</details>

역할 분담(박민호 PM · 백성검 프론트·웹 · 정어진 백엔드·파이프라인 · 정상호 AI 에이전트)이
코드 폴더에 그대로 나타난다. 문서 사이트만 넷이 고르게 쓰는데, **팀 사이 요청·결정이
미결 항목 페이지 한 곳으로 오가기 때문**이다.

---

[← 프로젝트 전체 그림]({{{{ "/10-프로젝트전체그림/" | relative_url }}}})

<details markdown="block">
<summary>이 페이지의 수치를 다시 뽑는 명령</summary>

```bash
for d in fastapi agent www flutter jekyll; do               # 영역·사람별 커밋
  echo "$d"; git log --format='%an' -- $d | sort | uniq -c
done
```

git 계정 이름과 사람: `pmhllll12` 박민호 · `백성검` 백성검 · `roqkf` 정어진 · `jsangho` 정상호.

</details>

[← 목차로](/toc/)
"""

(ROOT / "jekyll/progress").mkdir(exist_ok=True)
(ROOT / "jekyll/progress/10-프로젝트전체그림.markdown").write_text(PAGE, encoding="utf-8", newline="\n")
(ROOT / "jekyll/progress/12-진행현황.markdown").write_text(PROGRESS, encoding="utf-8", newline="\n")
print("ok")
