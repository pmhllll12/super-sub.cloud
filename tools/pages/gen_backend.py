"""「백엔드 · 파이프라인」 장 생성기.

수치는 2026-09-17 저장소에서 확인한 값이다. 그림 좌표는 이 수치에서 계산한다 —
값을 바꿀 때는 페이지를 손으로 고치지 말고 여기를 고쳐 다시 만든다.
사이트 본문 폭(약 740px)에 맞춰 viewBox 폭을 740 으로 그린다.
"""

from pathlib import Path

# 🔴 저장소 루트는 이 파일 위치에서 구한다 — 절대경로를 박지 않는다(`tools/README.md`).
ROOT = Path(__file__).resolve().parents[2]
INK, INK2, GRID = "#27262b", "#5c5962", "#e3e1da"
BLUE, ORANGE = "#2a78d6", "#eb6834"      # 검증기 통과(흰 바탕, 두 색)
CRITICAL = "#d03b3b"                    # 상태 색 — 아이콘·글자와 함께만 쓴다
FONT = "font-family=\"-apple-system,BlinkMacSystemFont,'Segoe UI','Apple SD Gothic Neo','Noto Sans KR',sans-serif\""


def figure(body, w, h, aria, caption):
    return (
        '<figure class="doc-figure">'
        f'<svg viewBox="0 0 {w} {h}" width="{w}" role="img" aria-label="{aria}" {FONT} '
        f'style="max-width:100%;height:auto;display:block">{body}</svg>'
        f'<figcaption class="doc-figure-caption">{caption}</figcaption>'
        "</figure>"
    )


def defs(extra_id="", extra_color=None):
    m = (f'<marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
         f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{INK2}"/></marker>')
    if extra_id:
        m += (f'<marker id="{extra_id}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
              f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{extra_color}"/></marker>')
    return f"<defs>{m}</defs>"


def text(x, y, t, size=11, anchor="middle", color=INK2, weight=None):
    w = f' font-weight="{weight}"' if weight else ""
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}" fill="{color}"{w}>{t}</text>'


# --- 그림 1. 도메인 지도 ------------------------------------------------------
DOMAINS = {  # 키: (x, y, 이름, 테이블 수)
    "match": (300, 16, "매칭", 9),
    "analysis": (40, 120, "영상 분석", 9),
    "review": (560, 120, "평가·신뢰", 5),
    "user": (300, 196, "사용자·팀", 10),
    "card": (40, 276, "카드·스쿼드", 6),
    "notification": (560, 276, "알림", 1),
    "billing": (300, 360, "과금", 3),
}
BW, BH = 140, 58
# 읽는 쪽 → 주인 : 직접 읽는 테이블 수 (2026-09-17, table() 선언에서 뽑음)
READS = {
    ("analysis", "card"): 1, ("analysis", "review"): 2, ("analysis", "user"): 2,
    ("billing", "user"): 2, ("card", "user"): 4,
    ("match", "analysis"): 4, ("match", "card"): 3, ("match", "notification"): 1,
    ("match", "review"): 2, ("match", "user"): 6,
    ("review", "match"): 2, ("review", "user"): 2,
    ("user", "card"): 2, ("user", "match"): 2, ("user", "notification"): 1,
}
NAME = {k: v[2] for k, v in DOMAINS.items()}


def fig_domains():
    b = [defs()]
    for key, (x, y, name, n) in DOMAINS.items():
        b.append(
            f'<g><title>{name} — 테이블 {n}개</title>'
            f'<rect x="{x}" y="{y}" width="{BW}" height="{BH}" rx="6" fill="#f6f5f1" stroke="{INK2}" stroke-width="1.5"/>'
            + text(x + BW / 2, y + 25, name, 14, color=INK, weight="600")
            + text(x + BW / 2, y + 44, f"테이블 {n}개", 11.5)
            + "</g>"
        )

    def tip(a, c):
        parts = []
        if (a, c) in READS:
            parts.append(f"{NAME[a]} → {NAME[c]}: 테이블 {READS[(a, c)]}개를 직접 읽음")
        if (c, a) in READS:
            parts.append(f"{NAME[c]} → {NAME[a]}: 테이블 {READS[(c, a)]}개를 직접 읽음")
        return " / ".join(parts)

    def edge(a, c, d, both=False):
        start = ' marker-start="url(#a)"' if both else ""
        return (
            f'<g><title>{tip(a, c)}</title>'
            f'<path d="{d}" fill="none" stroke="transparent" stroke-width="12"/>'
            f'<path d="{d}" fill="none" stroke="{INK2}" stroke-width="1.5" marker-end="url(#a)"{start}/></g>'
        )

    b += [
        edge("match", "analysis", "M300,55 L182,124"),
        edge("match", "review", "M440,55 L558,124", both=True),
        edge("match", "user", "M370,74 L370,194", both=True),
        edge("match", "card", "M300,30 L22,30 L22,305 L38,305"),
        edge("match", "notification", "M440,30 L718,30 L718,305 L702,305"),
        edge("analysis", "user", "M180,165 L298,212"),
        edge("analysis", "card", "M110,178 L110,274"),
        edge("analysis", "review", "M180,140 L558,140"),
        edge("review", "user", "M560,165 L442,212"),
        edge("card", "user", "M180,290 L298,238", both=True),
        edge("user", "notification", "M440,238 L558,290"),
        edge("billing", "user", "M370,360 L370,256"),
    ]
    b.append(text(20, 440, "화살표 = 읽는 도메인 → 테이블 주인 · 양쪽 화살표 = 서로 읽음 · 선에 마우스를 올리면 테이블 수", 11.5, "start", INK))
    return figure(
        "".join(b), 740, 452,
        "백엔드 도메인 일곱과, 서로의 테이블을 직접 읽는 관계 15쌍. 사용자·팀 도메인이 가장 많이 읽히고, 매칭 도메인이 가장 많이 읽어 간다.",
        "그림 1. 도메인 지도(2026-09-17). 도메인끼리 <strong>코드는 서로 가져다 쓰지 않는다</strong> — 검사가 막는다. "
        "대신 필요한 값은 다른 도메인의 테이블을 직접 읽는데, 그런 관계가 15쌍(45곳)이다. "
        "사용자·팀은 다섯 도메인이 읽어 가고, 추천 판을 만드는 매칭은 다섯 도메인을 읽는다(4절 D).",
    )


# --- 그림 2. 분석 작업의 상태 흐름 ---------------------------------------------
def fig_states():
    b = [defs("x", CRITICAL)]

    def node(x, y, name, sub):
        return (
            f'<g><title>{name} — {sub}</title>'
            f'<rect x="{x}" y="{y}" width="120" height="52" rx="26" fill="#f6f5f1" stroke="{INK}" stroke-width="1.5"/>'
            + text(x + 60, y + 23, name, 14, color=INK, weight="600")
            + text(x + 60, y + 40, sub, 11)
            + "</g>"
        )

    b += [
        node(30, 130, "대기", "queued"),
        node(300, 130, "실행", "running"),
        node(590, 50, "성공", "succeeded"),
        node(590, 210, "실패", "failed"),
    ]

    def path(d, color=INK2, dash=False, marker="a"):
        da = ' stroke-dasharray="6 4"' if dash else ""
        return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.5"{da} marker-end="url(#{marker})"/>'

    b += [
        path("M150,156 L298,156"), text(224, 147, "워커가 가져감"),
        path("M420,146 L588,84"), text(470, 100, "완료 보고"),
        path("M420,166 L588,228"), text(548, 198, "실패 보고"),
        path("M360,182 C360,268 90,268 90,184"),
        text(225, 280, "보고 없이 30분 멈춤 · 첫 번째 → 다시 대기열"),
        path("M400,182 C430,280 540,290 588,250"),
        text(510, 300, "두 번째 멈춤 → 실패로 끝냄"),
        # 금지 경로
        path("M90,130 C90,30 400,20 588,66", CRITICAL, dash=True, marker="x"),
        text(330, 20, "✕ 대기에서 바로 끝내기 — 금지 (C의 1차안이 이 길이었다)", 11.5, color=CRITICAL, weight="600"),
    ]
    # 재업로드 줄
    b.append(f'<line x1="20" y1="318" x2="720" y2="318" stroke="{GRID}" stroke-width="1"/>')
    b.append(text(20, 338, "같은 영상을 다시 올리면(C)", 11.5, "start", INK, "600"))

    def note(x, w, t):
        return (f'<rect x="{x}" y="348" width="{w}" height="34" rx="6" fill="none" stroke="{INK2}" stroke-width="1.2"/>'
                + text(x + w / 2, 370, t, 11.5, color=INK))

    b += [
        note(20, 160, "같은 사람 · 같은 내용"),
        path("M182,365 L238,365"),
        note(240, 230, "작업을 만들지 않고 앞 영상을 가리킴"),
        path("M472,365 L528,365"),
        note(530, 190, "앞 결과를 등록 응답에 싣기"),
    ]
    return figure(
        "".join(b), 740, 392,
        "분석 작업의 상태: 대기에서 워커가 가져가면 실행, 완료 보고로 성공 또는 실패. 보고 없이 30분 멈추면 첫 번째는 다시 대기로, 두 번째는 실패로 끝난다. 대기에서 바로 성공이나 실패로 가는 길은 금지다. 같은 영상을 다시 올리면 작업을 만들지 않고 앞 영상을 가리킨다.",
        "그림 2. 분석 작업 하나가 거치는 상태. 이 규칙은 <strong>코드 한 곳에만</strong> 있고 DB 제약으로 걸지 않았다 — 단계가 늘 때 "
        "마이그레이션 없이 넣으려는 것이다. 회수를 한 번으로 제한한 이유는, 무한히 되돌리면 워커를 죽이는 영상이 대기열을 영원히 돌기 때문이다.",
    )


# --- 선 그래프 공통 -----------------------------------------------------------
def line_chart(series, x_days, x_ticks, y_max, y_step, h=280, ref=None, legend=True, point_title=None, x1=690):
    x0, y0, y1 = 60, 44, h - 40
    X = lambda d: round(x0 + d * (x1 - x0) / x_days, 1)
    Y = lambda v: round(y1 - v * (y1 - y0) / y_max, 1)
    b = []
    v = 0
    while v <= y_max:
        b.append(f'<line x1="{x0}" y1="{Y(v)}" x2="{x1}" y2="{Y(v)}" stroke="{GRID}" stroke-width="1"/>')
        b.append(text(x0 - 8, Y(v) + 4, f"{v:,}", 11, "end"))
        v += y_step
    for d, lab in x_ticks:
        b.append(text(X(d), y1 + 18, lab, 11))
    if ref:
        rv, rl = ref
        b.append(f'<line x1="{x0}" y1="{Y(rv)}" x2="{x1}" y2="{Y(rv)}" stroke="{INK2}" stroke-width="1.2" stroke-dasharray="5 4"/>')
        b.append(text(x0 + 6, Y(rv) - 6, rl, 11, "start", INK))
    lx = x0
    for name, color, pts, end_label in series:
        poly = " ".join(f"{X(d)},{Y(val)}" for d, _, val in pts)
        b.append(f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>')
        for d, date, val in pts:
            b.append(
                f'<g><title>{point_title(name, date, val)}</title>'
                f'<circle cx="{X(d)}" cy="{Y(val)}" r="10" fill="transparent"/>'
                f'<circle cx="{X(d)}" cy="{Y(val)}" r="4" fill="{color}" stroke="#fff" stroke-width="2"/></g>'
            )
        d, _, val = pts[-1]
        b.append(text(X(d) + 10, Y(val) + 4, end_label, 12, "start", INK, "600"))
        if legend:
            b.append(f'<rect x="{lx}" y="12" width="12" height="12" rx="3" fill="{color}"/>')
            b.append(text(lx + 18, 22, name, 12, "start", INK))
            lx += 150
    return "".join(b)


# 테스트 수 — 커밋 메시지의 `pytest N passed` · `전체 N passed` 날짜별 값(최대=마지막으로 대조함)
TESTS = [
    (0, "08-25", 70), (1, "08-26", 127), (3, "08-28", 165), (8, "09-02", 318),
    (9, "09-03", 439), (10, "09-04", 452), (14, "09-08", 633), (15, "09-09", 693),
    (16, "09-10", 697), (17, "09-11", 776), (21, "09-15", 887), (22, "09-16", 1023),
    (23, "09-17", 1068),
]


def fig_tests():
    body = line_chart(
        [("백엔드 테스트", BLUE, TESTS, "1,068")],
        x_days=23,
        x_ticks=[(0, "08-25"), (7, "09-01"), (14, "09-08"), (21, "09-15")],
        y_max=1100, y_step=250, legend=False,
        point_title=lambda n, d, v: f"{d} · 테스트 {v:,}건",
    )
    body += text(70, 214, "70", 12, "start", INK, "600")
    return figure(
        body, 740, 280,
        "백엔드 테스트 수 추이: 08-25에 70건에서 09-17에 1,068건. 한 번도 줄지 않았다.",
        "그림 3. 백엔드 테스트 수(pytest). 08-25 70건 → 09-17 1,068건, <strong>한 번도 줄지 않았다.</strong> "
        "값은 커밋 메시지에 남긴 전체 실행 결과이고, 적지 않은 날은 점이 없다. 기능마다 계약 검사와 실제 DB 검사를 함께 넣었다.",
    )


TABLES = [(2, "08-26", 8), (4, "08-28", 14), (8, "09-01", 16), (9, "09-02", 19), (10, "09-03", 27),
          (11, "09-04", 27), (15, "09-08", 30), (16, "09-09", 30), (17, "09-10", 31), (18, "09-11", 31),
          (22, "09-15", 41), (23, "09-16", 43), (24, "09-17", 43)]
MIGRATIONS = [(2, "08-26", 3), (4, "08-28", 6), (8, "09-01", 7), (9, "09-02", 9), (10, "09-03", 12),
              (11, "09-04", 14), (15, "09-08", 20), (16, "09-09", 25), (17, "09-10", 30), (18, "09-11", 32),
              (22, "09-15", 37), (23, "09-16", 44), (24, "09-17", 47)]


def fig_schema():
    body = line_chart(
        [("테이블(누적)", BLUE, TABLES, "테이블 43"), ("마이그레이션(누적)", ORANGE, MIGRATIONS, "마이그레이션 47")],
        x_days=24,
        x_ticks=[(0, "08-24"), (8, "09-01"), (15, "09-08"), (22, "09-15")],
        y_max=50, y_step=10, ref=(32, "처음 설계(ERD) 32개 · 08-24"), x1=600,
        point_title=lambda n, d, v: f"{d} · {n} {v}",
    )
    return figure(
        body, 740, 280,
        "스키마 증가: 테이블은 08-26에 8개에서 09-17에 43개, 마이그레이션은 3개에서 47개. 처음 설계는 32개 테이블이었다.",
        "그림 4. 테이블과 마이그레이션이 쌓인 흐름. 처음 설계(점선, 32개)를 09-15에 넘었다 — 설계에 없던 로그인 수단·알림·팀 초대·"
        "일정 매칭 같은 자리가 생기면서다. 마이그레이션이 테이블보다 빨리 는 것은 <strong>이미 있는 테이블에 칸을 더한 변경</strong>이 "
        "그만큼 많았다는 뜻이다(팀 해체 표시·부르는 자리·카드 불릿 등).",
    )


def tiles():
    items = [("1,068", "백엔드 테스트", "08-25 70건에서"), ("98", "API 경로", "도메인 7개에 나눠"),
             ("43", "테이블", "처음 설계 32개"), ("51건", "계약 변경", "화면 쪽에 넘긴 규격 변경")]
    cells = "".join(
        '<div class="stat-tile">'
        f'<div class="stat-value">{big}</div>'
        f'<div class="stat-label">{what}</div>'
        f'<div class="stat-note">{note}</div></div>'
        for big, what, note in items
    )
    return f'<div class="stat-tiles">{cells}</div>'


def table_rows(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(["---"] + ["---:"] * (len(header) - 1)) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


PAGE = f"""---
layout: default
title: 백엔드 · 파이프라인
permalink: /11-백엔드파이프라인/
parent: 기술
nav_order: 1
---

# 백엔드 · 파이프라인

> 2026-09-17 기준 · 담당 정어진. 전체 구성 속 위치는
> [프로젝트 전체 그림]({{{{ "/10-프로젝트전체그림/" | relative_url }}}})의 그림 1·2에 있다. 이 장은
> **무엇을 만들었고, 무엇에 막혔고, 어떻게 풀었나**를 다룬다.

## 1) 맡은 것 한눈에

API 서버와 데이터베이스, 그리고 분석 파이프라인의 **양 끝** — 들어오는 영상의 검사,
분석 작업 대기열, 돌아온 결과의 적재 — 를 맡았다. 분석 자체(자세 추출·채점)는 정상호,
배포 앞단과 k3s 전환은 박민호가 맡았다.

{tiles()}

## 2) 구조

### 도메인 지도

{fig_domains()}

### 분석 작업의 상태 흐름

{fig_states()}

## 3) 수치로 본 진행

{fig_tests()}

{fig_schema()}

<details markdown="block">
<summary>표로 보기</summary>

{table_rows(["날짜", "테스트"], [(d, f"{v:,}") for _, d, v in TESTS])}

{table_rows(["날짜", "테이블(누적)", "마이그레이션(누적)"], [(t[1], t[2], m[2]) for t, m in zip(TABLES, MIGRATIONS)])}

</details>

## 4) 어려운 문제와 해결

### A. 소리 없는 장애 — 하루 넘게 분석이 멈췄는데, 백엔드는 몰랐다

**상황.** 09-16 08:27부터 분석이 한 건도 돌지 않았다. 작업은 대기열에 쌓이는데 가져가는
워커가 없었고, **백엔드 로그에는 워커의 요청이 아예 찍히지 않았다.**

**막힌 점.** 백엔드에서 보이는 것은 "요청이 안 온다"뿐이라, 워커가 죽었는지·네트워크
문제인지·서버 문제인지 가를 단서가 없었다.

**어떻게 좁혔나.**

1. (정상호) 워커 기록에서 실패 응답을 찾았고, 그 응답을 보낸 것이 우리 서버가 아니라
   **앞단**이라는 흔적을 확인했다. 마지막 정상 처리는 08:11, 첫 실패는 08:27 — 워커는
   코드·설정·재시작 없이 **같은 프로세스 안에서** 갈렸다. 원인은 워커 밖에 있었다.
2. (정상호) 조건을 하나씩 바꿔 같은 경로를 불러 차단 기준을 특정했다. 이때 **작업을
   소비하는 호출은 쓰지 않고** 조회 방식으로만 시험했다 — 시험이 운영 데이터를 바꾸지
   않게.
3. (정상호) 워커가 요청마다 자기 이름을 밝히도록 고쳐 분석을 되살렸다.
4. (정어진) 서버에서 같은 시험을 재현하고, 앞단을 거치지 않은 직접 호출은 정상인 것을
   확인했다. 그런데 **배포 문서 어디에도 그 앞단이 없었다** — 문서는 nginx를 맨 앞으로
   적고 있었다.

**고른 것.** 워커 쪽 수정은 규칙을 피한 것이지 규칙이 우리를 안 막게 된 것이 아니라서,
문제를 닫지 않고 앞단 규칙을 맡은 박민호에게 근본 조치(워커 전용 경로를 차단 대상에서
빼기)를 넘겼다. 배포 문서에 앞단을 적고 「백엔드는 멀쩡한데 밖에서만 막히면 앞단부터
본다」를 남겼다.

**배운 것.** 설정을 확인하는 명령 하나가 서버 이관 뒤로 **아무것도 못 잡는 상태**였는데,
"안 걸린다"가 "문제가 없다"로 읽혀 왔다. 확인 명령은 **살아 있는지 판별되게** 고쳤다 —
결과가 비면 그 자체가 이상 신호가 되는 형태로.

### B. 지우지 않는 삭제 — 마지막 주장이 팀을 버릴 방법이 없었다

**상황.** 팀의 마지막 주장은 나갈 수 없게 막혀 있었다 — 주장이 없는 팀에는 아무도 사람을
넣을 수 없어서다. 그런데 팀을 없애는 길도, 다른 사람을 주장으로 세우는 길도 없었다.
오류 안내는 "다른 주장을 먼저 세우라"고 했지만 **세울 방법이 없었다.** 혼자 만든 팀은
영영 버릴 수 없었다.

**막힌 점.** 요청은 "팀 삭제"였다. 그런데 팀을 가리키는 외래키가 9개였고 그중 5개가
삭제를 막는다(경기·스쿼드·경기 신청·구성원). 설계 문서의 삭제 연쇄도 팀 삭제를 정해
두지 않았다.

| 선택지 | 얻는 것 | 잃는 것 |
|---|---|---|
| 진짜 삭제 + 삭제 연쇄를 새로 정의 | 요청 그대로 | 세 도메인에 걸친 규칙을 새로 만들어야 하고, 지난 경기·평가가 가리키던 팀이 사라진다 |
| **해체 표시** (행은 남김) | 이력 보존 · 스키마 변경은 칸 하나 | 새로 만드는 자리마다 해체 여부를 봐야 한다 |
| 그대로 둠 | 변경 없음 | 사용자가 계속 막힌다 |

**고른 것과 이유.** 해체 표시. 구성원 탈퇴도 이미 같은 이유로 행을 지우지 않고 탈퇴
시각만 남기고 있었다 — 팀에도 같은 원칙을 적용했다. 여럿인 팀의 주장이 나갈 수 있게
**주장 세우기**도 함께 냈다.

**구현하다 찾은 구멍.** 처음엔 "구성원을 전부 내보내면 되지 않나"였는데, **본인 가입은
누구나 할 수 있어서** 표시가 없으면 해체한 팀에 아무나 들어와 팀이 되살아난다. 그래서
표시 칸이 꼭 필요했고, 막는 범위는 가입·초대·수정(새로 만드는 자리)으로만 잡았다 —
읽기와 이력은 그대로다. 앞으로 있을 경기가 있으면 해체를 막았다(상대 팀에게는
약속이다). 경기 탐색이 다가오는 경기만 보여 주므로, 이 규칙 하나로 "없는 팀의 경기가
탐색에 뜨는" 문제가 구조적으로 생기지 않는다.

**결과.** 검사 21건(계약 15 · 실제 DB 6)을 더했고 전체 1,055건이 통과했다.

### C. 첫 설계를 스스로 버리다 — 같은 영상을 다시 올렸을 때

**상황.** 같은 사람이 같은 영상을 다시 올리면 GPU로 똑같은 분석을 또 돌렸다. 앞서 실패한
영상이면 같은 이유로 또 실패했다.

**1차안.** 새 분석 작업을 만들되 곧바로 "성공" 또는 "실패"로 끝내고 앞 결과를 복사한다.
기존 흐름(작업 → 결과)을 그대로 쓸 수 있어 간단해 보였다.

**버린 이유.** 코드로 옮기기 전에 상태 규칙을 다시 읽다가 발견했다 — **대기에서 바로 끝내기는
금지**다(그림 2의 빨간 점선). 워커가 가져가지 않은 작업이 끝난 것처럼 보이면, 시작·끝 시각의
차이로 재는 처리 시간 지표가 거짓이 된다. 게다가 결과를 복사하려면 리포트를 다시 적재하는
일까지 따라왔다.

**2차안(채택).** 새 작업을 **아예 만들지 않고**, 새 영상이 앞 영상을 가리키기만 한다. 등록
응답에 앞 결과(성공·실패와 사유)를 바로 싣는다. 재적재가 통째로 사라졌다.

**좁힌 조건 셋.** 내용이 같은지는 저장소가 이미 알려 주는 파일 지문으로 판단한다(다시 내려받지
않는다) · 본인 영상끼리만 · 분석 대상을 따로 지정한 영상은 제외한다(같은 영상이라도 누구를
봤는지가 다르면 결과가 다를 수 있다).

**구현하며 밟은 함정.** 두 JSON 칸은 "비어 있음"이 SQL의 NULL이 아니라 JSON의 `null` 값으로
저장돼서, 조건이 실제 데이터에 한 건도 걸리지 않았다. 실제 DB로 조회해 보는 통합 검사에서야
드러났다 — 가짜 저장소로만 검사했다면 통과했을 자리다.

### D. 경계를 말이 아니라 검사로 — 도메인 일곱이 섞이지 않게

**상황.** 백엔드를 도메인 일곱으로 나눴다(그림 1). 다른 팀원도 백엔드에 도메인을 붙이는
기간이 있었고(과금은 박민호가 만들었다), **규칙을 문서에만 적으면 반드시 무너진다.**

**고른 것.** 규칙을 검사로 바꿨다. 검사 12개가 도메인끼리 코드를 가져다 쓰는지, 계층이 거꾸로
의존하는지, 새 테이블이 마이그레이션 도구에 등록됐는지를 매번 확인하고, 어기면 CI가 막는다.

**치른 대가 둘.**

1. 다른 도메인의 값이 필요하면 그 도메인 코드를 부를 수 없어 **테이블을 직접 읽는다** — 15쌍,
   45곳이다. 그런데 저쪽 칸 이름이 바뀌면 파이썬이 잡아 주지 못한다. 그래서 그런 자리마다
   **실제 DB로 대조하는 통합 검사**를 두었고, DB가 없어 검사가 건너뛰어지면 CI가 실패하게 했다
   — "초록불인데 사실은 안 돌았다"를 막으려는 것이다.
2. 계산 규칙도 빌려 쓸 수 없다. 추천 판(매칭)이 등급(영상 분석)을 계산해야 해서 **등급 규칙을
   매칭 쪽에 복제**했다. 둘이 갈라지지 않게 지키는 일이 따라온다.

**또 하나의 판단.** 도메인들을 조율하는 별도 계층은 넣지 않았다. 지금 도메인 사이의 흐름은
전부 **읽기**라서, 도메인을 넘나드는 쓰기 흐름이 실제로 생기면 그 사례로 뽑아내기로 했다 —
상상한 흐름에 맞춰 미리 만들면 실제 코드가 왔을 때 다시 깎게 된다.

---

[← 프로젝트 전체 그림]({{{{ "/10-프로젝트전체그림/" | relative_url }}}})

<details markdown="block">
<summary>이 장의 수치를 다시 뽑는 명령</summary>

```bash
# 테스트 수 — 커밋 메시지의 전체 실행 결과(두 표기)를 날짜별로
git log --reverse --author=roqkf --format='@@%ad%n%B' --date=short \\
  | awk '/^@@/{{d=substr($0,3); next}}
         {{ l=$0; while (match(l, /(pytest|전체)[^0-9]{{0,20}}[0-9]+ passed/)) {{
             s=substr(l,RSTART,RLENGTH); gsub(/[^0-9]/," ",s); n=split(s,b," ");
             if (b[n]+0>m[d]) m[d]=b[n]+0; l=substr(l,RSTART+RLENGTH) }} }}
         END{{for(k in m) print k, m[k]}}' | sort

# 테이블·마이그레이션 — 마이그레이션 파일이 들어온 날짜별로
for f in fastapi/alembic/versions/*.py; do
  echo "$(git log --diff-filter=A --format=%ad --date=short -- "$f" | tail -1) $(grep -c 'op.create_table(' "$f")"
done | sort | awk '{{m[$1]++; t[$1]+=$2}} END{{for(k in m) print k, m[k], t[k]}}' | sort

# 계약 변경 항목 수 (번호 5~9는 처음부터 없다)
grep -cE '^## [0-9]+\\.' fastapi/docs/client-contract-changes.md
```

</details>

[← 목차로](/toc/)
"""

(ROOT / "jekyll/progress/11-백엔드파이프라인.markdown").write_text(PAGE, encoding="utf-8", newline="\n")
print("ok")
