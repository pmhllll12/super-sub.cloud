"""부록 D 본문을 실제 스키마(2026-09-17)에 맞춘다.

⚠️ **일회성이고 이미 적용됐다 — 다시 돌리면 `assert` 에서 멈춘다.**
바꿀 원문을 `assert old in s` 로 확인하고 치환하는 방식이라, 적용이 끝난
지금은 찾을 원문이 없다(쓰기는 맨 끝이라 저장소는 안 건드린다).
**도구가 아니라 기록으로 남긴다** — D.3·D.7 표를 `schema.json` 에서 어떻게
계산했는지가 여기 있다. 자세한 것은 `tools/README.md`.


- 그림 삽입부: 새로 생성한 SVG 를 원래 크기로 두고 옆으로 밀어 보게 한다
- D.3 외래키 표 · D.7 유일 제약 표: schema.json 에서 계산한다
- 나머지: 사실이 바뀐 문장만 바꾼다(assert 로 원문을 확인하고)
"""

import json
import re
import sys
from pathlib import Path

# 🔴 저장소 루트는 이 파일 위치에서 구한다 — 절대경로를 박지 않는다(`tools/README.md`).
ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "jekyll/chapters/부록D-데이터베이스ERD.markdown"
schema = json.load(open(sys.argv[1], encoding="utf-8"))
s = DOC.read_text(encoding="utf-8")
VER = "20260917"

ORDER = ["user", "analysis", "card", "match", "review", "billing", "notification"]
DNAME = {"user": "① 사용자·팀", "analysis": "② 영상·분석", "card": "③ 카드·호칭", "match": "④ 매칭",
         "review": "⑤ 평가·신뢰", "billing": "⑥ 과금", "notification": "⑦ 알림"}


def rep(old, new, count=1):
    global s
    assert old in s, "원문 없음: " + old[:70]
    s = s.replace(old, new, count)


def section(start_heading, next_heading):
    a = s.index(start_heading)
    b = s.index(next_heading, a + len(start_heading))
    return a, b


def size(fname):
    head = (ROOT / "assets/erd" / fname).read_text(encoding="utf-8")[:400]
    return int(re.search(r'width="(\d+)"', head).group(1)), int(re.search(r'height="(\d+)"', head).group(1))


def figure(fname, alt, fit=False):
    w, h = size(fname)
    url = f"{{{{ '/assets/erd/{fname}' | relative_url }}}}?v={VER}"
    img_style = "max-width:100%;height:auto" if fit else "max-width:none;height:auto"
    return (f'<div style="overflow-x:auto;margin:1.2rem 0;border:1px solid #e3e1da;border-radius:6px">'
            f'<a href="{url}" title="원본 크기로 열기"><img src="{url}" alt="{alt}" width="{w}" height="{h}" '
            f'style="{img_style};display:block"></a></div>')


# --- 머리말 ---------------------------------------------------------------------
rep("**44 테이블 · 6 도메인 · 1~3정규형 준수**",
    "**43 테이블 · 7 도메인 · 2026-09-17 실제 스키마 기준**")
rep("44개 테이블을 6개 도메인으로 나누어 정리한다.",
    "실제로 만들어진 43개 테이블을 7개 도메인으로 나누어 정리한다. 설계했지만 아직 구현하지 않은\n"
    "테이블 4개는 표에 **미구현**으로 남겨 둔다.\n\n"
    "**그림은 백엔드 코드(ORM)에서 자동으로 만든다** — 손으로 고치지 않고, 스키마가 바뀌면 다시\n"
    "생성한다. 그래서 그림과 실제 스키마가 어긋나지 않는다.")
rep("제1정규형부터 제3정규형까지 준수한다. 비원자 값(jsonb), 이행 종속 컬럼, 파생·집계 컬럼을 두지\n않는다. 정규화 근거와 그에 따른 조회 비용은 D.4에서 다룬다.",
    "제1정규형부터 제3정규형까지를 원칙으로 삼는다. 다만 구현하면서 **JSON·배열·벡터 칸 10개**와\n"
    "**알고 둔 중복 한 곳**이 생겼다 — 어디에 왜 두었는지는 D.4 「원칙의 예외」에 모았다. 정규화\n"
    "근거와 그에 따른 조회 비용도 D.4에서 다룬다.")

# --- D.1 --------------------------------------------------------------------------
rep("도메인 사이의 데이터 흐름이다. 영상이 지표가 되고, 그 지표가 카드(표시)와 매칭(판단) 두 갈래로\n쓰인다는 것이 이 모델의 골격이다.",
    "도메인을 넘는 외래키다. **34개 중 32개가 ① 사용자·팀을 향한다** — 사람과 팀이 거의 모든 기록의\n"
    "주인이기 때문이다.\n\n"
    "영상이 지표가 되고 그 지표가 카드(표시)와 매칭(판단) 두 갈래로 쓰인다는 것이 이 모델의 골격이지만,\n"
    "**그 흐름은 외래키가 아니라** 애플리케이션이 다른 도메인의 테이블을 읽는 길로 이어진다(도메인끼리\n"
    "코드를 가져다 쓰지 않는 구조라서다). 그 지도는\n"
    "[백엔드 · 파이프라인]({{ \"/11-백엔드파이프라인/\" | relative_url }}) 그림 1에 있다.")
rep('![D.1 도메인 간 데이터 흐름]({{ "/assets/erd/d1-overview.svg" | relative_url }}){: class="erd-diagram" }',
    figure("d1-overview.svg", "D.1 도메인을 넘는 외래키", fit=True))

# --- D.2 --------------------------------------------------------------------------
rep('컬럼 표에서 "키" 열의 화살표는 참조 대상 테이블이다. 다른 도메인의 테이블을 참조하는 경우는\nD.3에 별도로 모았다.',
    "그림은 테이블마다 **모든 컬럼**을 보여 준다. 그림이 넓으면 옆으로 밀어 보거나, 눌러서 원본 크기로\n"
    "연다. 다른 도메인의 테이블은 점선 상자로만 그리고, 도메인을 넘는 외래키는 D.3에 모았다.")

# 그림 삽입부 + 「표가 최신이다」 안내 제거
DOMAIN_FIG = [
    ("domain1-user-team.svg", "도메인 ① 사용자·팀 ERD"),
    ("domain2-video-analysis.svg", "도메인 ② 영상·분석 ERD"),
    ("domain3-card-title.svg", "도메인 ③ 카드·호칭 ERD"),
    ("domain4-matching.svg", "도메인 ④ 매칭 ERD"),
    ("domain5-review-trust.svg", "도메인 ⑤ 평가·신뢰 ERD"),
    ("domain6-billing.svg", "도메인 ⑥ 과금 ERD"),
]
for fname, alt in DOMAIN_FIG:
    old = f'![{alt}]({{{{ "/assets/erd/{fname}" | relative_url }}}}){{: class="erd-diagram" }}'
    rep(old, figure(fname, alt))
# 안내 인용 블록(「표가 최신이다」)을 전부 지운다 — 그림이 이제 최신이다
before = s.count("표가 최신이다")
s = re.sub(r"\n> 위 그림[^\n]*\n(?:>[^\n]*\n)*", "\n", s)
assert "표가 최신이다" not in s, "안내 블록이 남았다"
print("지운 안내 블록 속 「표가 최신이다」:", before)

# ① 표
rep("| user | 계정과 신원 (SEC-003). 닉네임은 유일하다 | 가입한 사람 1명 |",
    "| user | 계정과 신원 (SEC-003). 닉네임은 유일하다. 용병 검색용 프로필 칸(선호 포지션·가능 시간·지역·실력 요약과 그 임베딩)도 여기 있다 — ④의 개인 매칭 조건과 겹친다(D.4 「원칙의 예외」) | 가입한 사람 1명 |")
rep("| team | 동호회 | 등록된 팀 1개 |",
    "| team | 동호회. **해체해도 행은 지우지 않고** 해체 시각(`disbanded_at`)만 찍는다 — 지난 경기·평가가 팀을 가리키기 때문이다(2026.09.17) | 등록된 팀 1개 |")
rep("| sport | 축구·야구·농구 종목 코드 | 종목 1개 (현재 3행) |",
    "| sport | 축구·야구·농구 종목 코드. 새로 받는 종목인지는 `active` 로 가른다 — 지금은 축구만 받고, 나머지는 이미 쌓인 데이터가 참조해서 행을 남긴다(2026.09.16) | 종목 1개 (현재 3행) |")
notif_row = re.search(r"^\| notification \|.*\|\n", s, re.M).group()
s = s.replace(notif_row, "")
rep("| region | 지역 참조 데이터",
    "| team_invitation | 팀이 개인을 초대하는 자리. **받은 사람이 수락해야** 구성원이 된다 — 동의 없이 넣지 않는다. 초대할 때 부르는 자리(포지션)를 함께 적을 수 있다(2026.09.16~17) | 초대 1건 |\n| region | 지역 참조 데이터")

# ② 본문·표
rep("같은 물리량(예: `trunk_forward_lean_deg_at_impact`)이 축구·야구·농구\n루브릭에 함께 쓰인다.",
    "같은 물리량(예: `trunk_forward_lean_deg_at_impact`)이면 루브릭이 달라도\n같은 항목이다(지금 루브릭은 축구 두 동작뿐이다).")
rep("| video | 업로드한 클립의 저장 위치와 메타 (SFR-001) | 업로드된 클립 1개 |",
    "| video | 업로드한 클립의 저장 위치와 메타 (SFR-001). 공개 여부·**사람당 하나인 대표 영상**·화면 비율을 담고, 같은 사람이 같은 내용을 다시 올리면 새 분석 대신 앞 영상을 가리킨다(`duplicate_of_video_id`) | 업로드된 클립 1개 |")
rep("| analysis_report | 지표를 근거로 생성한 요약 문장 (SFR-003) | 지표 묶음 1개의 요약문 |",
    "| analysis_report | 지표를 근거로 생성한 요약 문장 (SFR-003). 총점 등급·검수 전 여부와 추천 카드의 불릿 한두 줄(`card_notes`)도 함께 담는다 | 지표 묶음 1개의 요약문 |")
rep("| player_vector | 성향 비교용 특징 벡터. pgvector로 색인한다 (SFR-005) | 지표 묶음 1개의 임베딩 |",
    "| player_vector | **미구현.** 성향 비교용 특징 벡터. pgvector로 색인한다 (SFR-005). 채울 누적 분석이 먼저 필요하다 | 지표 묶음 1개의 임베딩 |\n"
    "| reference_player | 「선수와 비교하기」가 쓰는 고정 본보기 선수 목록. 늘어날 때 코드 재배포 없이 행만 더하려고 참조 테이블로 둔다 | 본보기 선수 1명 |")

# ③ 본문·표
rep("호칭 기준도 종목·항목마다 다르므로 title_criteria에 조건 한 줄씩 나누어 담는다.",
    "호칭은 두 갈래다. 정해 둔 호칭 목록(title_definition)에서 부여하는 것(user_title)과, **사람이 직접\n"
    "적는 것**(user_custom_title)이다. 2026-09-16 에 「호칭은 분석이 주지 않고 사람이 적는다 — 신뢰는\n"
    "경기 후 평가가 떠받친다」로 정하면서 뒤쪽이 생겼다. 분석이 기준을 넘으면 호칭을 주는 설계\n"
    "(title_criteria)는 구현하지 않았다.")
rep("| title_criteria | 호칭별 절대 기준. 항목·비교연산자·임계값을 행으로 나눈다 | 호칭 1종의 판정 조건 1줄 |",
    "| title_criteria | **미구현.** 호칭별 절대 기준. 항목·비교연산자·임계값을 행으로 나눈다 | 호칭 1종의 판정 조건 1줄 |")
rep("| user_title | 호칭 부여 이력 | 한 사람이 받은 호칭 1개 |",
    "| user_title | 정해 둔 호칭의 부여 이력. 부여된 것만 행으로 존재한다 | 한 사람이 받은 호칭 1개 |\n"
    "| user_custom_title | **사람이 직접 적는 호칭**. 한 개 20자, 3개까지. 분류는 받지 않는다(2026.09.16) | 한 사람이 적은 호칭 1개 |")
rep("`user.nickname`(이름)·`user_title`(분석이 주는 호칭)과는 다른 값이다",
    "`user.nickname`(이름)·호칭(user_title·user_custom_title)과는 다른 값이다. 꾸미기 설정은 `style`(JSON)에 담는다")
rep("| squad_member | 스쿼드에 등재된 카드와 포지션 | 스쿼드 1개에 등재된 카드 1장 |",
    "| squad_member | 스쿼드에 등재된 카드와 포지션, 판 위 칸(`grid_col`·`grid_row`) | 스쿼드 1개에 등재된 카드 1장 |")
rep("| squad | 팀 단위 카드 묶음 | 한 팀의 스쿼드 1개 |",
    "| squad | 팀 단위 카드 묶음과 판 크기(`formation`) | 한 팀의 스쿼드 1개 |")

# ④ 표
rep("| fitness_score | 수준·역할·성향 3축 적합도 (SFR-006) | 지원 1건의 적합도 산출 결과 |",
    "| fitness_score | **미구현.** 수준·역할·성향 3축 적합도 (SFR-006) | 지원 1건의 적합도 산출 결과 |")
rep("| recommendation | 후보 추천 이력과 추천 사유 (SFR-007) | 경기 1건에 제시된 후보 1명 |",
    "| recommendation | **미구현.** 후보 추천 이력과 추천 사유 (SFR-007). 지금 추천 판은 이력을 저장하지 않고 요청마다 계산한다 | 경기 1건에 제시된 후보 1명 |")

# ⑥ 표
rep("| coach | 제휴 코치 | 제휴 코치 1명 |", "| coach | 제휴 코치와 그 종목 | 제휴 코치 1명 |")

# ⑦ 신설
rep("구인 측(팀)에 과금하는 경로는 아직 반영하지 않았다. 4.3 수익 모델이 확정되면 해당 과금 행위를\n기록할 테이블을 추가한다(D.8).",
    "구인 측(팀)에 과금하는 경로는 아직 반영하지 않았다. 4.3 수익 모델이 확정되면 해당 과금 행위를\n기록할 테이블을 추가한다(D.8).\n\n"
    "### ⑦ 알림\n\n"
    "처음 설계에는 없던 도메인이다. 지인 신청·팀 초대·팀 대 팀 경기 신청이 모두 「상대에게 알린다」를\n"
    "필요로 하면서 독립했다. 화면이 주기적으로 물어 가져간다(폴링).\n\n"
    + figure("domain7-notification.svg", "도메인 ⑦ 알림 ERD") + "\n\n"
    "| 테이블 | 용도 | 1행이 뜻하는 것 |\n|---|---|---|\n"
    "| notification | 알림. **문구는 저장하지 않는다** — `type`·일으킨 사람(`actor_user_id`)·대상(`subject_type`·`subject_id`)만 담고 화면이 문장을 만든다. 다른 도메인이 알림을 만들 때는 이 테이블에 직접 적재한다 | 알림 1건 |")

# --- D.3 외래키 표(계산) ---------------------------------------------------------
MEANING = {
    ("video", "user_id"): "업로더", ("video", "sport_code"): "종목",
    ("title_definition", "sport_code"): "종목별 호칭", ("user_title", "user_id"): "호칭 대상자",
    ("user_custom_title", "user_id"): "호칭을 적은 사람", ("player_card", "user_id"): "카드 소유자",
    ("squad", "team_id"): "소속 팀", ("squad_member", "position_id"): "포지션",
    ("match", "team_id"): "주최 팀", ("match", "opponent_team_id"): "상대 팀(팀 대 팀 확정 경기, 없으면 용병 모집)",
    ("team_match_request", "requester_team_id"): "신청 팀", ("team_match_request", "target_team_id"): "대상 팀",
    ("match_position_need", "position_id"): "필요 포지션", ("match_application", "user_id"): "지원자",
    ("member_match_position", "user_id"): "조건의 주인(개인)", ("member_match_position", "position_id"): "희망 포지션",
    ("member_match_region", "user_id"): "조건의 주인(개인)", ("member_match_region", "region_id"): "선호 지역",
    ("member_match_slot", "user_id"): "조건의 주인(개인)",
    ("team_match_region", "team_id"): "조건의 주인(팀)", ("team_match_region", "region_id"): "선호 지역",
    ("team_match_slot", "team_id"): "조건의 주인(팀)",
    ("review", "match_id"): "대상 경기", ("review", "reviewer_id"): "평가자", ("review", "reviewee_id"): "피평가자",
    ("report", "reporter_id"): "신고자", ("report", "target_user_id"): "신고 대상",
    ("no_show", "match_id"): "불참한 경기", ("no_show", "user_id"): "불참자",
    ("analysis_credit", "user_id"): "크레딧 소유자", ("coach", "sport_code"): "코치의 종목",
    ("coach_referral", "user_id"): "연결 요청자",
    ("notification", "recipient_user_id"): "받는 사람", ("notification", "actor_user_id"): "알림을 일으킨 사람(없을 수 있음)",
}
rows = []
for t in sorted(schema, key=lambda t: (ORDER.index(schema[t]["context"]), t)):
    v = schema[t]
    for f in sorted(v["fks"], key=lambda f: f["cols"]):
        tc = schema[f["target"]]["context"]
        if tc == v["context"]:
            continue
        col = ", ".join(f["cols"])
        meaning = MEANING.get((t, col))
        assert meaning, f"의미 없음: {t}.{col}"
        rows.append(f"| {DNAME[v['context']]} | {t} | {col} | {f['target']} | {f['ondelete']} | {meaning} |")
d3_table = ("| 출발 도메인 | 출발 테이블 | 컬럼 | 도착 | 삭제 시 | 의미 |\n|---|---|---|---|---|---|\n" + "\n".join(rows))
a, b = section("## D.3 도메인을 잇는 외래키", "## D.4 정규화")
s = s[:a] + f"""## D.3 도메인을 잇는 외래키

도메인 경계를 넘는 외래키를 한곳에 모았다(스키마에서 계산, {len(rows)}개). 대부분이 user·team을
향하며, 이것이 43개 테이블을 한 장에 그릴 수 없는 이유다. 「삭제 시」는 참조되는 행을 지울 때의
동작이다 — `NO ACTION` 은 참조하는 행이 있으면 **삭제를 거부**한다(D.6).

{d3_table}

설계에는 `user_title.source_metric_id → analysis_metric`(호칭 부여 근거)도 있었지만 **넣지 않았다.**
처음(2026.08.26)에는 분석 테이블이 아직 없어서 미뤘고, 그 뒤 호칭을 분석이 주지 않고 사람이 적기로
하면서(2026.09.16) 필요가 없어졌다. 설계에 있던 `title_criteria`·`recommendation` 의 외래키도
테이블이 미구현이라 없다.

""" + s[b:]

# --- D.4 --------------------------------------------------------------------------
rep("| 호칭 기준 | jsonb 대신 title_criteria에 조건 한 줄씩 담는다 |",
    "| 호칭 기준 | jsonb 대신 title_criteria에 조건 한 줄씩 담는 설계다(**미구현** — ③ 참고) |")
rep("fitness_score의 level_axis·role_axis·style_axis는 반복 그룹이 아니다.",
    "(**미구현**) fitness_score의 level_axis·role_axis·style_axis는 반복 그룹이 아니다.")
rep("### 제2정규형 — 부분 종속이 없다",
    """### 원칙의 예외 — 알고 둔 것 (2026-09-17)

구현하면서 원자값으로 풀지 않은 칸이 10개, 같은 개념을 두 곳에 담은 중복이 한 곳 생겼다. 공통점은
**DB 안에서 그 값의 속을 들여다보며 거르지 않는다**는 것이다(배열·벡터는 예외로, 그 자체가 검색 단위다).

| 칸 | 모양 | 왜 풀지 않았나 |
|---|---|---|
| analysis_job.subject_box · focus | JSON(좌표 목록 · 항목 id 목록) | 등록이 검사해 넣고 워커에 그대로 넘기는 입력값이다. 비어 있음이 「자동으로 고르기」·「전체」라는 정상 경로다 |
| analysis_job.detection_result | JSON | 사람 검출 결과를 워커 출력 그대로 담는다. 화면이 대상을 고를 때 읽는다 |
| analysis_report.previews · keypoint_quality | JSON | 분석 봉투의 메타(미리보기 위치·관절 품질)를 그대로 적재한다 |
| analysis_report.card_notes | JSON(문장 한두 개) | **개수가 값의 일부**다 — 두 줄을 지어내지 않는 규칙이라 한 줄뿐인 것이 정상이다. 칸 둘로 쪼개면 「없다」와 「빈 문자열」이 섞인다 |
| player_card.style | JSON | 모양은 화면이 정하고 서버는 형식만 검사한다. 설정마다 컬럼을 늘어놓지 않는다 |
| user.preferred_positions | 문자열 배열 | 용병 검색이 배열 포함 연산으로 거른다 |
| user.available_slots | JSON | 용병 검색 프로필의 가능 시간. 프로필 칸들과 함께 들어왔다(2026.09.10) |
| user.skill_embedding | vector(768) | 실력 요약 문장의 임베딩 — 벡터 자체가 유사도 검색 단위다 |

🔴 **알고 둔 중복**: user 의 용병 검색 칸(선호 포지션·가능 시간·지역)과 ④의 member_match_position·
member_match_slot·member_match_region 이 **같은 개념을 따로** 담는다. 앞쪽은 의미 유사도로 찾는
용병 검색이, 뒤쪽은 겹침으로 찾는 일정 매칭이 쓴다. 검색 방식이 달라 지금은 합치지 않았다 — 한쪽만
채운 사람은 다른 쪽 기능에서 안 보이는 대가가 있다(D.8).

### 제2정규형 — 부분 종속이 없다""")
rep("| 벡터 검색 (SFR-005) | 사용자로 좁히려면 player_vector → analysis_metric → analysis_job → video 4단 조인이 필요하다.",
    "| 벡터 검색 (SFR-005) | (player_vector **미구현**) 사용자로 좁히려면 player_vector → analysis_metric → analysis_job → video 4단 조인이 필요하다.")

# --- D.5 --------------------------------------------------------------------------
rep("| 호칭은 미부여 방식으로만 작동한다 | 3.5 | user_title은 부여된 행만 존재한다. 미달을 false로 저장하지 않는다. 그렇게 두면 조회 시 부정 표식이 된다 |",
    "| 호칭은 미부여 방식으로만 작동한다 | 3.5 | user_title은 부여된 행만 존재한다. 미달을 false로 저장하지 않는다. 그렇게 두면 조회 시 부정 표식이 된다. 사람이 적는 호칭(user_custom_title)도 적은 것만 행으로 있다 |")
rep("fitness_score는 경기 지원 건에 종속되며 단독 조회 대상이 아니다 |",
    "fitness_score(**미구현**)는 경기 지원 건에 종속되며 단독 조회 대상이 아니다 |")
rep("| 추천에는 근거를 함께 제시한다 | 3.3 | recommendation.reason을 NOT NULL로 둔다 |",
    "| 추천에는 근거를 함께 제시한다 | 3.3 | recommendation.reason을 NOT NULL로 두는 설계다(**미구현** — 지금 추천 판은 사실값 근거를 응답에 싣는다) |")

# --- D.6 --------------------------------------------------------------------------
a, b = section("## D.6 삭제 연쇄", "## D.7 주요 제약조건")
s = s[:a] + f"""## D.6 삭제 연쇄

SEC-006은 삭제 요청 시 원본과 파생물이 함께 삭제될 것을 요구한다. 아래 그림은 스키마의 삭제 규칙
(`ON DELETE`)에서 계산한 것이다 — **계정을 지우면** 왼쪽 나무가 함께 지워지고, 그 안의 점선 가지가
**영상 한 편을 지울 때** 함께 지워지는 범위다.

{figure("d6-cascade.svg", "D.6 계정·영상 삭제 연쇄와 삭제를 막는 기록", fit=True)}

계정 탈퇴는 사용자 행을 실제로 지우고, 딸린 것은 이 연쇄가 지운다 — 자격증명·외부 계정 연결·카드·
호칭·소속·영상 체인·알림·지인·받은 초대·개인 매칭 조건. 자격증명과 외부 계정 연결은 계정에 완전히
종속되며 단독으로 남을 이유가 없다. 특히 user_identity가 남으면 **같은 구글 계정으로 다시 가입할 때
사라진 사용자를 가리키게 된다.**

🔴 **정정 (2026-09-17)** — 앞서 이 자리에 「team_member는 left_at으로 소프트 삭제하므로 이 연쇄에
넣지 않는다」고 적었는데 **실제 스키마와 다르다.** 소프트 삭제는 **팀 탈퇴**(계정은 남음)일 때의
처리이고, **계정을 지우면 team_member 행도 연쇄로 함께 지워진다.** 같은 이유로 적었던 「user_title이
분석 지표를 근거로 참조해 이 연쇄에 들어간다」도 그 외래키를 넣지 않아 해당하지 않는다(D.3).

팀은 반대로 **해체해도 행을 지우지 않는다**(`team.disbanded_at`). 팀을 참조하는 외래키 다섯이
삭제를 거부하는 규칙이고, 지난 경기·평가가 팀 이름을 가리킨다.

🔴 **계정 삭제를 막는 기록이 있다.** 그림 오른쪽의 기록 — 경기 지원·평가(쓴 것·받은 것)·신고·
불참·크레딧·코치 연결·스쿼드 등재 — 이 남아 있으면 외래키가 `NO ACTION` 이라 **DB가 계정 행 삭제를
거부한다.** 2026-09-17 로컬 DB에서 경기 지원 기록이 있는 사람으로 재현했다. 이 기록들을 익명화할지,
함께 지울지, 탈퇴를 막고 안내할지는 정해지지 않았다(D.8).

""" + s[b:]

# --- D.7 유일 제약 표(계산) --------------------------------------------------------
REASON = {
    ("user", "email"): "계정 식별",
    ("user", "nickname"): "지인 검색이 닉네임으로 사람을 특정해야 한다(미결 `jin` 35번)",
    ("user_contact", "requester_user_id, target_user_id"): "같은 방향으로 중복 신청 방지",
    ("user_credential", "user_id"): "사용자당 자격증명 1건",
    ("user_identity", "provider, subject"): "한 외부 계정이 두 사용자에 붙는 것을 막는다",
    ("user_identity", "user_id, provider"): "한 사용자가 같은 제공자를 두 번 연결하지 못하게 한다",
    ("position", "sport_code, code"): "포지션 약칭이 종목 간 겹칠 수 있다",
    ("region", "city, district"): "지역 중복 등록 방지(`paik` 19번)",
    ("team_member", "team_id, user_id, joined_at"): "재가입 이력을 남기면서 중복 소속을 막는다",
    ("video", "user_id (is_featured 인 행만)"): "사람당 대표 영상 1개 — 부분 유일 인덱스(2026.09.09)",
    ("video_validation", "video_id"): "영상당 검사 결과 1건",
    ("analysis_metric", "analysis_job_id"): "작업당 지표 집합 1건",
    ("analysis_metric_value", "analysis_metric_id, metric_code"): "항목당 값 1건",
    ("analysis_metric_criterion", "analysis_metric_id, criterion_id"): "한 분석에서 같은 채점 항목 중복 방지",
    ("analysis_report", "analysis_metric_id"): "지표 집합당 요약 1건",
    ("player_card", "user_id"): "사용자당 카드 1건",
    ("player_card", "public_slug"): "슬러그 중복 방지",
    ("squad", "public_slug"): "슬러그 중복 방지",
    ("squad_member", "squad_id, player_card_id"): "스쿼드당 카드 1회 등재",
    ("user_title", "user_id, title_code"): "같은 호칭 중복 부여 방지",
    ("match_application", "match_id, user_id"): "경기당 1인 1회 지원",
    ("match_position_need", "match_id, position_id"): "경기당 포지션 1행",
    ("team_match_region", "team_id, region_id"): "같은 지역 중복 선호 방지",
    ("member_match_region", "user_id, region_id"): "같은 지역 중복 선호 방지",
    ("member_match_position", "user_id, position_id"): "같은 포지션 중복 등록 방지",
    ("review", "match_id, reviewer_id, reviewee_id"): "경기당 1회 평가",
    ("no_show", "match_id, user_id"): "경기당 1인 1건",
}
urows = []
for t in sorted(schema, key=lambda t: (ORDER.index(schema[t]["context"]), t)):
    seen = set()
    for u in schema[t]["uniques"]:
        key = tuple(u)
        if key in seen:
            continue
        seen.add(key)
        cols = ", ".join(c for c in u if c != "(부분)")
        if "(부분)" in u:
            cols += " (is_featured 인 행만)"
        reason = REASON.get((t, cols))
        assert reason, f"이유 없음: {t} ({cols})"
        shown = f"({cols})" if "," in cols else cols
        urows.append(f"| {t} | {shown} | {reason} |")
urows.append("| player_vector | analysis_metric_id | **미구현** — 지표 집합당 벡터 1건 |")
urows.append("| fitness_score | match_application_id | **미구현** — 지원 건당 적합도 1건 |")
a, b = section("## D.7 주요 제약조건", "## D.8 미확정 사항")
s = s[:a] + f"""## D.7 주요 제약조건

기본키 외에 유일 제약이 필요한 곳이다(스키마에서 계산, 구현 {len(urows) - 2}개 + 미구현 2개).

| 테이블 | 유일 제약 | 이유 |
|---|---|---|
""" + "\n".join(urows) + "\n\n" + s[b:]

# --- D.8 --------------------------------------------------------------------------
a, b = section("## D.8 미확정 사항", "---\n\nSuper-Sub / 슈퍼서브")
s = s[:a] + """## D.8 미확정 사항

| 항목 | 내용 |
|---|---|
| 🔴 탈퇴와 남는 기록 | 경기 지원·평가·신고·불참·크레딧·코치 연결·스쿼드 등재 기록이 있으면 DB가 계정 삭제를 거부한다(D.6). 익명화·함께 삭제·탈퇴 전 안내 중 무엇으로 할지 정해야 한다 |
| 용병 매칭 조건의 중복 | user 의 용병 검색 칸과 ④의 개인 매칭 조건이 같은 개념을 따로 담는다(D.4). 합칠지, 한쪽을 다른 쪽의 폴백으로 둘지 |
| 미구현 테이블 넷 | player_vector(선수 성향 벡터)·fitness_score(적합도)·recommendation(추천 이력)·title_criteria(분석 호칭 기준). 넣을 시점은 정해지지 않았다. title_criteria 는 호칭을 사람이 적기로 하면서(2026.09.16) 필요가 줄었다 |
| ~~지표 항목~~ | ✅ **확정됨** — 종목 무관 물리량으로 정하고(2026.09.08) 시드로 적재했다(2026.09.10) |
| ~~평가 선택지~~ | ✅ **확정됨** — review_option 시드와 노출 순서(`sort_order`)가 들어갔다(2026.09.03~04) |
| 과금 상세 | 4.3 수익 모델이 확정되지 않아 analysis_credit·coach·coach_referral은 최소 형태다. 구인 측 과금이 채택되면 테이블이 추가된다 |
| 평가·지표 대응 | review_option과 metric_definition의 대응 관계. 누적 보정(3.4) 도입 시 정의한다. 설정 데이터라 소급 적용이 가능하므로 지금 두지 않는다 |
| 브랜드 제휴 | 4.3의 확장 모델은 본 개발 기간 범위 밖이므로 테이블을 두지 않는다 |

""" + s[b:]
rep("지표 항목과 평가 선택지는 스프린트 1에서 확정한다. D.8 미확정 사항을 함께 확인한다.",
    "미확정 사항은 D.8에 모았다.")

DOC.write_text(s, encoding="utf-8", newline="\n")
print("ok · D.3", len(rows), "행 · D.7", len(urows), "행")
