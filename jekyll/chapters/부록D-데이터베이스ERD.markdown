---
layout: default
title: 데이터베이스 ERD
permalink: /부록D-데이터베이스ERD/
parent: 설계
nav_order: 2
---

Super-Sub 플랫폼의 데이터 모델이다. 3장 서비스 기능과 5장 요구사항에서 도출했다.
각자 담당 도메인부터 보면 된다.

**43 테이블 · 7 도메인 · 2026-09-17 실제 스키마 기준**

본 부록은 3장에서 정의한 서비스 기능과 5장 요구사항(SFR·SEC)에서 도출한 데이터 모델이다.
실제로 만들어진 43개 테이블을 7개 도메인으로 나누어 정리한다. 설계했지만 아직 구현하지 않은
테이블 4개는 표에 **미구현**으로 남겨 둔다.

**그림은 백엔드 코드(ORM)에서 자동으로 만든다** — 손으로 고치지 않고, 스키마가 바뀌면 다시
생성한다. 그래서 그림과 실제 스키마가 어긋나지 않는다.

제1정규형부터 제3정규형까지를 원칙으로 삼는다. 다만 구현하면서 **JSON·배열·벡터 칸 10개**와
**알고 둔 중복 한 곳**이 생겼다 — 어디에 왜 두었는지는 D.4 「원칙의 예외」에 모았다. 정규화
근거와 그에 따른 조회 비용도 D.4에서 다룬다.

user가 대부분의 테이블과 연결되는 허브이므로 전체를 한 장에 그리면 읽을 수 없다. 도메인별로
나누어 정리하고, 전체 외래키 목록은 D.3에 표로 정리한다.

## D.1 한눈에 보기

도메인을 넘는 외래키다. **34개 중 32개가 ① 사용자·팀을 향한다** — 사람과 팀이 거의 모든 기록의
주인이기 때문이다.

영상이 지표가 되고 그 지표가 카드(표시)와 매칭(판단) 두 갈래로 쓰인다는 것이 이 모델의 골격이지만,
**그 흐름은 외래키가 아니라** 애플리케이션이 다른 도메인의 테이블을 읽는 길로 이어진다(도메인끼리
코드를 가져다 쓰지 않는 구조라서다). 그 지도는
[백엔드 · 파이프라인]({{ "/11-백엔드파이프라인/" | relative_url }}) 그림 1에 있다.

<div style="overflow-x:auto;margin:1.2rem 0;border:1px solid #e3e1da;border-radius:6px"><a href="{{ '/assets/erd/d1-overview.svg' | relative_url }}?v=20260917" title="원본 크기로 열기"><img src="{{ '/assets/erd/d1-overview.svg' | relative_url }}?v=20260917" alt="D.1 도메인을 넘는 외래키" width="740" height="420" style="max-width:100%;height:auto;display:block"></a></div>

## D.2 도메인별 상세

그림은 테이블마다 **모든 컬럼**을 보여 준다. 그림이 넓으면 옆으로 밀어 보거나, 눌러서 원본 크기로
연다. 다른 도메인의 테이블은 점선 상자로만 그리고, 도메인을 넘는 외래키는 D.3에 모았다.

### ① 사용자·팀

<div style="overflow-x:auto;margin:1.2rem 0;border:1px solid #e3e1da;border-radius:6px"><a href="{{ '/assets/erd/domain1-user-team.svg' | relative_url }}?v=20260917" title="원본 크기로 열기"><img src="{{ '/assets/erd/domain1-user-team.svg' | relative_url }}?v=20260917" alt="도메인 ① 사용자·팀 ERD" width="1145" height="904" style="max-width:none;height:auto;display:block"></a></div>


| 테이블 | 용도 | 1행이 뜻하는 것 |
|---|---|---|
| user | 계정과 신원 (SEC-003). 닉네임은 유일하다. 용병 검색용 프로필 칸(선호 포지션·가능 시간·지역·실력 요약과 그 임베딩)도 여기 있다 — ④의 개인 매칭 조건과 겹친다(D.4 「원칙의 예외」) | 가입한 사람 1명 |
| user_credential | 로그인 자격증명. 비밀번호 해시를 user에 두지 않고 분리한다. 소셜 로그인을 추가할 때 user를 건드리지 않아도 되고, 자격증명 조회 경로를 따로 제한할 수 있다 | 한 사람의 자격증명 1건 |
| user_identity | 외부 제공자(구글 등) 계정과의 연결. provider가 준 고유 ID(subject)를 그대로 보관한다. **이메일로 사람을 식별하지 않는다** — 이메일은 바뀔 수 있고 재사용될 수도 있다 | 한 사람의 한 제공자 연결 1건 |
| team | 동호회. **해체해도 행은 지우지 않고** 해체 시각(`disbanded_at`)만 찍는다 — 지난 경기·평가가 팀을 가리키기 때문이다(2026.09.17) | 등록된 팀 1개 |
| team_member | 소속과 역할. 탈퇴 후에도 경기·평가 이력이 남아야 하므로 left_at으로 소프트 삭제한다. 재가입이 가능하므로 joined_at을 함께 둔다 | 한 사람의 한 팀 소속 구간 1건 |
| sport | 축구·야구·농구 종목 코드. 새로 받는 종목인지는 `active` 로 가른다 — 지금은 축구만 받고, 나머지는 이미 쌓인 데이터가 참조해서 행을 남긴다(2026.09.16) | 종목 1개 (현재 3행) |
| position | 종목별 포지션. 포지션 약칭이 종목 간 겹칠 수 있어 대리키를 두고 (sport_code, code)에 유일 제약을 건다 | 한 종목의 포지션 1개 |
| user_contact | 상호 지인 관계(미결 `jin` 35번). 한쪽이 신청하고(requester) 대상(target)이 수락하면 양쪽 다 서로를 지인으로 본다. 메모는 신청자만 본다 | 신청 1건(대기중) 또는 지인 관계 1건(수락됨) |
| team_invitation | 팀이 개인을 초대하는 자리. **받은 사람이 수락해야** 구성원이 된다 — 동의 없이 넣지 않는다. 초대할 때 부르는 자리(포지션)를 함께 적을 수 있다(2026.09.16~17) | 초대 1건 |
| region | 지역 참조 데이터(미결 `paik` 19번). `city`·`district`를 별도 컬럼으로 둬 계층 비교(같은 구/같은 시)를 문자열 파싱 없이 한다 — `team.region`(팀의 연고지, 자유 문자열)과는 다른 값이다 | 지역 1곳(예: 서울 강남구) |

### ② 영상·분석

업로드부터 지표 산출까지 한 줄로 이어지는 체인이다. 이 순서가 곧 SEC-006의 삭제 연쇄 경로가
된다(D.6).

지표 항목은 루브릭이 정의하고 계속 늘어나므로 컬럼으로 고정하지 않는다. metric_definition에
항목을 정의하고 analysis_metric_value에 항목당 한 행씩 적재한다. **지표는 물리량이라 종목에
속하지 않는다** — 같은 물리량(예: `trunk_forward_lean_deg_at_impact`)이면 루브릭이 달라도
같은 항목이다(지금 루브릭은 축구 두 동작뿐이다). 어느 종목에서 쓰는지는 metric_definition이 아니라 그 지표를 참조하는
루브릭·항목 쪽이 안다.

<div style="overflow-x:auto;margin:1.2rem 0;border:1px solid #e3e1da;border-radius:6px"><a href="{{ '/assets/erd/domain2-video-analysis.svg' | relative_url }}?v=20260917" title="원본 크기로 열기"><img src="{{ '/assets/erd/domain2-video-analysis.svg' | relative_url }}?v=20260917" alt="도메인 ② 영상·분석 ERD" width="1835" height="908" style="max-width:none;height:auto;display:block"></a></div>


| 테이블 | 용도 | 1행이 뜻하는 것 |
|---|---|---|
| video | 업로드한 클립의 저장 위치와 메타 (SFR-001). 공개 여부·**사람당 하나인 대표 영상**·화면 비율을 담고, 같은 사람이 같은 내용을 다시 올리면 새 분석 대신 앞 영상을 가리킨다(`duplicate_of_video_id`) | 업로드된 클립 1개 |
| video_validation | 규격 검사 결과와 반려 사유. 사유를 값으로 남겨야 검수 기준을 확인할 수 있다 | 클립 1개의 검사 결과 |
| analysis_job | 비동기 분석 작업의 상태와 소요 시간 (PER-001). `job_type`(`analyze`\|`detect`)으로 분석과 사람 검출을 같은 큐로 돌린다 — 검출 결과는 `detection_result`에 담는다(2026.09.15, 미결 `ho` 44번) | 분석 또는 검출 실행 1회 |
| analysis_metric | 분석 1회가 산출한 지표 집합. 산출 버전을 기록한다 (QUA-002) | 분석 실행 1회가 낸 지표 묶음 |
| metric_definition | 지표 항목의 정의와 단위. 물리량이라 종목에 속하지 않는다 — 어느 종목에서 쓰는지는 루브릭이 안다 | 지표 항목 1개 (예: 임팩트 시 무릎 각도) |
| analysis_metric_value | 지표 항목별 값 (SFR-002) | 지표 묶음 1개 안의 항목 1개 값 |
| analysis_metric_criterion | 리포트 항목별 등급의 맥락 — 칭호·구간·근거 문장 (SFR-003). analysis_metric_value가 항목의 **수치**를 담는다면 여기는 그 항목의 **맥락**이다 | 지표 묶음 1개 안의 채점 항목 1개 |
| analysis_report | 지표를 근거로 생성한 요약 문장 (SFR-003). 총점 등급·검수 전 여부와 추천 카드의 불릿 한두 줄(`card_notes`)도 함께 담는다 | 지표 묶음 1개의 요약문 |
| player_vector | **미구현.** 성향 비교용 특징 벡터. pgvector로 색인한다 (SFR-005). 채울 누적 분석이 먼저 필요하다 | 지표 묶음 1개의 임베딩 |
| reference_player | 「선수와 비교하기」가 쓰는 고정 본보기 선수 목록. 늘어날 때 코드 재배포 없이 행만 더하려고 참조 테이블로 둔다 | 본보기 선수 1명 |

### ③ 카드·호칭

호칭은 두 갈래다. 정해 둔 호칭 목록(title_definition)에서 부여하는 것(user_title)과, **사람이 직접
적는 것**(user_custom_title)이다. 2026-09-16 에 「호칭은 분석이 주지 않고 사람이 적는다 — 신뢰는
경기 후 평가가 떠받친다」로 정하면서 뒤쪽이 생겼다. 분석이 기준을 넘으면 호칭을 주는 설계
(title_criteria)는 구현하지 않았다.

<div style="overflow-x:auto;margin:1.2rem 0;border:1px solid #e3e1da;border-radius:6px"><a href="{{ '/assets/erd/domain3-card-title.svg' | relative_url }}?v=20260917b" title="원본 크기로 열기"><img src="{{ '/assets/erd/domain3-card-title.svg' | relative_url }}?v=20260917b" alt="도메인 ③ 카드·호칭 ERD" width="932" height="706" style="max-width:none;height:auto;display:block"></a></div>


| 테이블 | 용도 | 1행이 뜻하는 것 |
|---|---|---|
| title_definition | 호칭의 종류와 분류(강점·활동·용병) (SFR-004) | 호칭 1종 |
| title_criteria | **미구현.** 호칭별 절대 기준. 항목·비교연산자·임계값을 행으로 나눈다 | 호칭 1종의 판정 조건 1줄 |
| user_title | 정해 둔 호칭의 부여 이력. 부여된 것만 행으로 존재한다 | 한 사람이 받은 호칭 1개 |
| user_custom_title | **사람이 직접 적는 호칭**. 한 개 20자, 3개까지. 분류는 받지 않는다(2026.09.16) | 한 사람이 적은 호칭 1개 |
| player_card | 공개 카드와 공유용 슬러그 (SFR-009). `tagline`(문자 20, 선택)에 카드 별명을 담는다 — `user.nickname`(이름)·호칭(user_title·user_custom_title)과는 다른 값이다. 꾸미기 설정은 `style`(JSON)에 담는다 | 한 사람의 카드 1장 |
| squad | 팀 단위 카드 묶음과 판 크기(`formation`) | 한 팀의 스쿼드 1개 |
| squad_member | 스쿼드에 등재된 카드와 포지션, 판 위 칸(`grid_col`·`grid_row`) | 스쿼드 1개에 등재된 카드 1장 |

### ④ 매칭

<div style="overflow-x:auto;margin:1.2rem 0;border:1px solid #e3e1da;border-radius:6px"><a href="{{ '/assets/erd/domain4-matching.svg' | relative_url }}?v=20260917b" title="원본 크기로 열기"><img src="{{ '/assets/erd/domain4-matching.svg' | relative_url }}?v=20260917b" alt="도메인 ④ 매칭 ERD" width="991" height="942" style="max-width:none;height:auto;display:block"></a></div>


| 테이블 | 용도 | 1행이 뜻하는 것 |
|---|---|---|
| match | 경기 등록 (SFR-010). 종목은 team이 결정하므로 컬럼을 두지 않는다. `opponent_team_id`(선택)가 차 있으면 팀 대 팀으로 **확정된** 경기다 — `team_match_request` 수락으로만 채워지고, 이런 경기는 모집(`needs`)이 없다 | 등록된 경기 1건 |
| match_position_need | 경기별 필요 포지션과 인원. 포지션이 둘 이상일 수 있어 행으로 나눈다 | 경기 1건의 포지션 1종 필요분 |
| match_application | 지원과 제안. 양측 수락 시각을 각각 갖고, 둘 다 채워진 상태를 확정으로 본다 | 경기 1건에 대한 한 사람의 지원 1건 |
| team_match_request | 팀 대 팀 경기 신청(미결 `paik` 17번). 신청 팀이 항상 먼저 걸고 대상 팀만 답하는 비대칭 흐름이라 `match_application`과 달리 단일 `status` 문자열을 쓴다 | 팀 1개가 팀 1개에 건 신청 1건 |
| fitness_score | **미구현.** 수준·역할·성향 3축 적합도 (SFR-006) | 지원 1건의 적합도 산출 결과 |
| recommendation | **미구현.** 후보 추천 이력과 추천 사유 (SFR-007). 지금 추천 판은 이력을 저장하지 않고 요청마다 계산한다 | 경기 1건에 제시된 후보 1명 |
| team_match_region | 팀이 경기하고 싶은 지역(미결 `paik` 18번). 여러 개라 행으로 나눈다 | 팀 1개의 선호 지역 1곳 |
| team_match_slot | 팀이 경기 가능한 요일·시각. `start_time < end_time`을 애플리케이션이 막는다 | 팀 1개의 가능 시간대 1개 |
| member_match_region | 팀원 개인이 뛰고 싶은 지역. 팀 조건과 저장소가 분리돼 있다(같은 사람이 팀장이면서 팀원일 수 있어서) | 사용자 1명의 선호 지역 1곳 |
| member_match_slot | 팀원 개인이 뛸 수 있는 요일·시각 | 사용자 1명의 가능 시간대 1개 |
| member_match_position | 팀원 개인이 뛸 수 있는 포지션 | 사용자 1명의 희망 포지션 1개 |

### ⑤ 평가·신뢰

평가는 선택형이므로(3.4) 선택지를 review_option에 정의하고 선택 결과를 review_selection에
행으로 담는다.

<div style="overflow-x:auto;margin:1.2rem 0;border:1px solid #e3e1da;border-radius:6px"><a href="{{ '/assets/erd/domain5-review-trust.svg' | relative_url }}?v=20260917b" title="원본 크기로 열기"><img src="{{ '/assets/erd/domain5-review-trust.svg' | relative_url }}?v=20260917b" alt="도메인 ⑤ 평가·신뢰 ERD" width="932" height="706" style="max-width:none;height:auto;display:block"></a></div>


| 테이블 | 용도 | 1행이 뜻하는 것 |
|---|---|---|
| review | 경기 후 상호 평가의 제출 사실과 시점 (SFR-008) | 경기 1건에서 A가 B를 평가한 1건 |
| review_option | 평가 선택지 정의. `sort_order`(정수, 필수)로 화면 노출 순서를 고정한다 | 선택지 1개 |
| review_selection | 평가에서 선택된 항목 | 평가 1건에서 고른 선택지 1개 |
| report | 신고 접수 | 신고 1건 |
| no_show | 불참·지각 기록 | 경기 1건의 불참자 1명 |

report·no_show는 review와 직접 이어지지 않는다. 제재를 평가 점수가 아니라 별도 기록으로
처리한다는 3.5의 원칙을 스키마로 분리한 것이다.

평가자 신뢰도는 테이블로 두지 않는다. review와 review_selection을 집계하면 산출되는 파생값이라
저장하면 제3정규형에 어긋난다(D.4). 집계 뷰 또는 구체화 뷰로 만든다. 신뢰도 산출에 필요한
원자료 — 평가자·피평가자·시점·선택 결과 — 는 처음부터 적재한다. 소급 생성이 불가능한 것은
원자료뿐이고, 가중치는 언제든 다시 계산할 수 있다.

### ⑥ 과금

<div style="overflow-x:auto;margin:1.2rem 0;border:1px solid #e3e1da;border-radius:6px"><a href="{{ '/assets/erd/domain6-billing.svg' | relative_url }}?v=20260917b" title="원본 크기로 열기"><img src="{{ '/assets/erd/domain6-billing.svg' | relative_url }}?v=20260917b" alt="도메인 ⑥ 과금 ERD" width="903" height="410" style="max-width:none;height:auto;display:block"></a></div>

| 테이블 | 용도 | 1행이 뜻하는 것 |
|---|---|---|
| analysis_credit | 분석 크레딧의 증감 이력. 잔량은 delta의 합으로 구한다 | 크레딧 증감 1건 (지급 또는 차감) |
| coach | 제휴 코치와 그 종목 | 제휴 코치 1명 |
| coach_referral | 레슨·코치 연결과 수수료 | 코치 연결 1건 |

무료 한도는 크레딧 지급(delta 양수)으로 표현하고, 분석 1건마다 차감(delta 음수)한다. 따라서
무료 한도를 두든 건당 과금을 하든 테이블 구조는 같다. 과금 방식이 확정되어도 analysis_credit은
그대로 쓴다.

구인 측(팀)에 과금하는 경로는 아직 반영하지 않았다. 4.3 수익 모델이 확정되면 해당 과금 행위를
기록할 테이블을 추가한다(D.8).

### ⑦ 알림

처음 설계에는 없던 도메인이다. 지인 신청·팀 초대·팀 대 팀 경기 신청이 모두 「상대에게 알린다」를
필요로 하면서 독립했다. 화면이 주기적으로 물어 가져간다(폴링).

<div style="overflow-x:auto;margin:1.2rem 0;border:1px solid #e3e1da;border-radius:6px"><a href="{{ '/assets/erd/domain7-notification.svg' | relative_url }}?v=20260917" title="원본 크기로 열기"><img src="{{ '/assets/erd/domain7-notification.svg' | relative_url }}?v=20260917" alt="도메인 ⑦ 알림 ERD" width="684" height="332" style="max-width:none;height:auto;display:block"></a></div>

| 테이블 | 용도 | 1행이 뜻하는 것 |
|---|---|---|
| notification | 알림. **문구는 저장하지 않는다** — `type`·일으킨 사람(`actor_user_id`)·대상(`subject_type`·`subject_id`)만 담고 화면이 문장을 만든다. 다른 도메인이 알림을 만들 때는 이 테이블에 직접 적재한다 | 알림 1건 |

## D.3 도메인을 잇는 외래키

도메인 경계를 넘는 외래키를 한곳에 모았다(스키마에서 계산, 34개). 대부분이 user·team을
향하며, 이것이 43개 테이블을 한 장에 그릴 수 없는 이유다. 「삭제 시」는 참조되는 행을 지울 때의
동작이다 — `NO ACTION` 은 참조하는 행이 있으면 **삭제를 거부**한다(D.6).

| 출발 도메인 | 출발 테이블 | 컬럼 | 도착 | 삭제 시 | 의미 |
|---|---|---|---|---|---|
| ② 영상·분석 | video | sport_code | sport | NO ACTION | 종목 |
| ② 영상·분석 | video | user_id | user | CASCADE | 업로더 |
| ③ 카드·호칭 | player_card | user_id | user | CASCADE | 카드 소유자 |
| ③ 카드·호칭 | squad | team_id | team | NO ACTION | 소속 팀 |
| ③ 카드·호칭 | squad_member | position_id | position | NO ACTION | 포지션 |
| ③ 카드·호칭 | title_definition | sport_code | sport | NO ACTION | 종목별 호칭 |
| ③ 카드·호칭 | user_custom_title | user_id | user | CASCADE | 호칭을 적은 사람 |
| ③ 카드·호칭 | user_title | user_id | user | CASCADE | 호칭 대상자 |
| ④ 매칭 | match | opponent_team_id | team | NO ACTION | 상대 팀(팀 대 팀 확정 경기, 없으면 용병 모집) |
| ④ 매칭 | match | team_id | team | NO ACTION | 주최 팀 |
| ④ 매칭 | match_application | user_id | user | CASCADE | 지원자 |
| ④ 매칭 | match_position_need | position_id | position | NO ACTION | 필요 포지션 |
| ④ 매칭 | member_match_position | position_id | position | NO ACTION | 희망 포지션 |
| ④ 매칭 | member_match_position | user_id | user | CASCADE | 조건의 주인(개인) |
| ④ 매칭 | member_match_region | region_id | region | NO ACTION | 선호 지역 |
| ④ 매칭 | member_match_region | user_id | user | CASCADE | 조건의 주인(개인) |
| ④ 매칭 | member_match_slot | user_id | user | CASCADE | 조건의 주인(개인) |
| ④ 매칭 | team_match_region | region_id | region | NO ACTION | 선호 지역 |
| ④ 매칭 | team_match_region | team_id | team | CASCADE | 조건의 주인(팀) |
| ④ 매칭 | team_match_request | requester_team_id | team | NO ACTION | 신청 팀 |
| ④ 매칭 | team_match_request | target_team_id | team | NO ACTION | 대상 팀 |
| ④ 매칭 | team_match_slot | team_id | team | CASCADE | 조건의 주인(팀) |
| ⑤ 평가·신뢰 | no_show | match_id | match | NO ACTION | 불참한 경기 |
| ⑤ 평가·신뢰 | no_show | user_id | user | CASCADE | 불참자 |
| ⑤ 평가·신뢰 | report | reporter_id | user | SET NULL | 신고자(탈퇴하면 비운다) |
| ⑤ 평가·신뢰 | report | target_user_id | user | CASCADE | 신고 대상 |
| ⑤ 평가·신뢰 | review | match_id | match | NO ACTION | 대상 경기 |
| ⑤ 평가·신뢰 | review | reviewee_id | user | CASCADE | 피평가자 |
| ⑤ 평가·신뢰 | review | reviewer_id | user | SET NULL | 평가자(탈퇴하면 비운다) |
| ⑥ 과금 | analysis_credit | user_id | user | CASCADE | 크레딧 소유자 |
| ⑥ 과금 | coach | sport_code | sport | NO ACTION | 코치의 종목 |
| ⑥ 과금 | coach_referral | user_id | user | CASCADE | 연결 요청자 |
| ⑦ 알림 | notification | actor_user_id | user | SET NULL | 알림을 일으킨 사람(없을 수 있음) |
| ⑦ 알림 | notification | recipient_user_id | user | CASCADE | 받는 사람 |

설계에는 `user_title.source_metric_id → analysis_metric`(호칭 부여 근거)도 있었지만 **넣지 않았다.**
처음(2026.08.26)에는 분석 테이블이 아직 없어서 미뤘고, 그 뒤 호칭을 분석이 주지 않고 사람이 적기로
하면서(2026.09.16) 필요가 없어졌다. 설계에 있던 `title_criteria`·`recommendation` 의 외래키도
테이블이 미구현이라 없다.

## D.4 정규화

### 제1정규형 — 모든 컬럼이 원자값이다

| 대상 | 처리 |
|---|---|
| 지표값 | jsonb 대신 metric_definition + analysis_metric_value로 전개했다. 지표 항목은 루브릭이 정의하고 계속 늘어나므로 컬럼 고정이 불가능해 항목을 데이터로 둔다 |
| 호칭 기준 | jsonb 대신 title_criteria에 조건 한 줄씩 담는 설계다(**미구현** — ③ 참고) |
| 필요 포지션 | 문자열 한 컬럼 대신 match_position_need로 분리했다. 포지션이 둘 이상일 수 있다 |
| 평가 선택 결과 | review_selection으로 분리했다 |

(**미구현**) fitness_score의 level_axis·role_axis·style_axis는 반복 그룹이 아니다. 수준·역할·성향 세 개의
서로 다른 속성이며, 축별로 개별 반환하는 것이 SFR-006의 검수 기준이다.

### 원칙의 예외 — 알고 둔 것 (2026-09-17)

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

### 제2정규형 — 부분 종속이 없다

모든 테이블이 단일 컬럼 기본키를 쓴다. 복합키는 review_selection 하나뿐이며 비키 속성이 없다.
따라서 부분 함수 종속이 성립할 수 없다.

### 제3정규형 — 이행 종속과 파생 값이 없다

이전 초안에서 아래 네 가지를 제거했다.

| 제거한 것 | 이유 |
|---|---|
| match.sport_code | match → team → sport_code로 결정된다. 중복이자 모순 가능성 |
| player_vector.user_id | analysis_metric → analysis_job → video → user_id로 결정된다 |
| analysis_credit.balance | delta의 누적합이다 |
| reviewer_credibility 테이블 | review 집계 결과다. 테이블 전체가 파생값 |

### 정규화의 대가

정규형을 지키면 조회 비용이 올라간다. 성능 문제가 실제로 확인되면 6.2에서 아래 대응을
검토한다. 지금 미리 비정규화하지 않는다.

| 영향 | 내용 | 대응 후보 |
|---|---|---|
| 벡터 검색 (SFR-005) | (player_vector **미구현**) 사용자로 좁히려면 player_vector → analysis_metric → analysis_job → video 4단 조인이 필요하다. PER-003의 P95 500ms에 가장 위험한 지점 | 조인 결과 뷰, 또는 부분 인덱스 |
| 지표 조회 | 지표 1건이 여러 행이라 조회 시 피벗이 필요하다 | 지표 집합 단위 조회 후 애플리케이션에서 조립 |
| 크레딧 잔량 | 매번 SUM(delta) | 사용자별 인덱스, 필요 시 구체화 뷰 |
| 평가자 신뢰도 | 매 산출 시 집계 | 구체화 뷰와 주기적 갱신 |

## D.5 설계 원칙이 스키마에 반영된 지점

3장에서 확정한 원칙 가운데 스키마 구조로 강제한 것을 정리한다. 코드에만 두면 지켜지지 않으므로
테이블 설계 단계에서 막는다.

| 원칙 | 출처 | 스키마 반영 |
|---|---|---|
| 카드에 수치 능력치를 노출하지 않는다 | 3.5 | player_card에 능력치 컬럼을 두지 않는다. 수치는 analysis_metric_value에만 있고 리포트 경로로만 조회된다 |
| 호칭은 미부여 방식으로만 작동한다 | 3.5 | user_title은 부여된 행만 존재한다. 미달을 false로 저장하지 않는다. 그렇게 두면 조회 시 부정 표식이 된다. 사람이 적는 호칭(user_custom_title)도 적은 것만 행으로 있다 |
| 전체 순위표를 두지 않는다 | 3.4 | 사용자 간 비교 점수를 저장하는 테이블을 두지 않는다. fitness_score(**미구현**)는 경기 지원 건에 종속되며 단독 조회 대상이 아니다 |
| 매칭 확정은 사람이 한다 | 3.3 | match_application이 team_accepted_at·user_accepted_at을 각각 갖는다. 단일 상태값으로 두면 확정 조건이 코드에만 남는다 |
| 추천에는 근거를 함께 제시한다 | 3.3 | recommendation.reason을 NOT NULL로 두는 설계다(**미구현** — 지금 추천 판은 사실값 근거를 응답에 싣는다) |
| 지표 산출은 재현 가능해야 한다 | 3.3 | analysis_metric.pipeline_version으로 산출 버전을 기록한다. LLM 생성물인 analysis_report는 테이블을 분리해 지표에 섞이지 않게 한다 |
| 평가 이력은 처음부터 저장한다 | 3.4 | review가 평가자·시점을, review_selection이 선택 결과를 남긴다. 신뢰도는 여기서 언제든 다시 계산한다 |
| 제재는 평가가 아니라 기록으로 처리한다 | 3.5 | report·no_show를 review와 분리한다 |

## D.6 삭제 연쇄

SEC-006은 삭제 요청 시 원본과 파생물이 함께 삭제될 것을 요구한다. 아래 그림은 스키마의 삭제 규칙
(`ON DELETE`)에서 계산한 것이다 — **계정을 지우면** 왼쪽 나무가 함께 지워지고, 그 안의 점선 가지가
**영상 한 편을 지울 때** 함께 지워지는 범위다.

<div style="overflow-x:auto;margin:1.2rem 0;border:1px solid #e3e1da;border-radius:6px"><a href="{{ '/assets/erd/d6-cascade.svg' | relative_url }}?v=20260917b" title="원본 크기로 열기"><img src="{{ '/assets/erd/d6-cascade.svg' | relative_url }}?v=20260917b" alt="D.6 계정·영상 삭제 연쇄와 작성자만 비우는 기록" width="740" height="760" style="max-width:100%;height:auto;display:block"></a></div>

계정 탈퇴는 사용자 행을 실제로 지우고, 딸린 것은 이 연쇄가 지운다 — 자격증명·외부 계정 연결·카드·
호칭·소속·영상 체인·알림·지인·받은 초대·개인 매칭 조건, 그리고 경기 지원·불참·크레딧·코치 연결·
스쿼드 등재·**나에 대한** 평가와 신고. 자격증명과 외부 계정 연결은 계정에 완전히
종속되며 단독으로 남을 이유가 없다. 특히 user_identity가 남으면 **같은 구글 계정으로 다시 가입할 때
사라진 사용자를 가리키게 된다.**

🔴 **정정 (2026-09-17)** — 앞서 이 자리에 「team_member는 left_at으로 소프트 삭제하므로 이 연쇄에
넣지 않는다」고 적었는데 **실제 스키마와 다르다.** 소프트 삭제는 **팀 탈퇴**(계정은 남음)일 때의
처리이고, **계정을 지우면 team_member 행도 연쇄로 함께 지워진다.** 같은 이유로 적었던 「user_title이
분석 지표를 근거로 참조해 이 연쇄에 들어간다」도 그 외래키를 넣지 않아 해당하지 않는다(D.3).

팀은 반대로 **해체해도 행을 지우지 않는다**(`team.disbanded_at`). 팀을 참조하는 외래키 다섯이
삭제를 거부하는 규칙이고, 지난 경기·평가가 팀 이름을 가리킨다.

**내 것은 지우고, 남에게 남긴 것은 작성자만 비운다.** 내가 **남에게 쓴** 평가와 **내가 한** 신고는
지우지 않고 작성자 칸만 비운다(`SET NULL`) — 평가는 받은 사람의 신뢰 등급 원자료이고 신고는 대상의
제재 근거라, 쓴 사람이 떠났다고 사라지면 남의 기록이 바뀐다. 경기·팀·스쿼드·코치처럼 여럿이 쓰는
데이터는 남는다. 그림 오른쪽 「계정 삭제를 막는 기록」은 그래서 비어 있다.

🔴 **정정 (2026-09-17)** — 같은 날 이 자리에 「경기 지원·평가·신고·불참·크레딧·코치 연결·스쿼드 등재
기록이 있으면 외래키가 `NO ACTION` 이라 DB가 계정 행 삭제를 거부한다」고 적었다. 사실이었고(로컬 DB에서
재현), **삭제 규칙을 위처럼 정해 고쳤다.** 그 기록이 있는 사람의 탈퇴를 확인하는 DB 테스트를 함께 두었다.

## D.7 주요 제약조건

기본키 외에 유일 제약이 필요한 곳이다(스키마에서 계산, 구현 27개 + 미구현 2개).

| 테이블 | 유일 제약 | 이유 |
|---|---|---|
| position | (sport_code, code) | 포지션 약칭이 종목 간 겹칠 수 있다 |
| region | (city, district) | 지역 중복 등록 방지(`paik` 19번) |
| team_member | (team_id, user_id, joined_at) | 재가입 이력을 남기면서 중복 소속을 막는다 |
| user | email | 계정 식별 |
| user | nickname | 지인 검색이 닉네임으로 사람을 특정해야 한다(미결 `jin` 35번) |
| user_contact | (requester_user_id, target_user_id) | 같은 방향으로 중복 신청 방지 |
| user_credential | user_id | 사용자당 자격증명 1건 |
| user_identity | (provider, subject) | 한 외부 계정이 두 사용자에 붙는 것을 막는다 |
| user_identity | (user_id, provider) | 한 사용자가 같은 제공자를 두 번 연결하지 못하게 한다 |
| analysis_metric | analysis_job_id | 작업당 지표 집합 1건 |
| analysis_metric_criterion | (analysis_metric_id, criterion_id) | 한 분석에서 같은 채점 항목 중복 방지 |
| analysis_metric_value | (analysis_metric_id, metric_code) | 항목당 값 1건 |
| analysis_report | analysis_metric_id | 지표 집합당 요약 1건 |
| video | user_id (is_featured 인 행만) | 사람당 대표 영상 1개 — 부분 유일 인덱스(2026.09.09) |
| video_validation | video_id | 영상당 검사 결과 1건 |
| player_card | public_slug | 슬러그 중복 방지 |
| player_card | user_id | 사용자당 카드 1건 |
| squad | public_slug | 슬러그 중복 방지 |
| squad_member | (squad_id, player_card_id) | 스쿼드당 카드 1회 등재 |
| user_title | (user_id, title_code) | 같은 호칭 중복 부여 방지 |
| match_application | (match_id, user_id) | 경기당 1인 1회 지원 |
| match_position_need | (match_id, position_id) | 경기당 포지션 1행 |
| member_match_position | (user_id, position_id) | 같은 포지션 중복 등록 방지 |
| member_match_region | (user_id, region_id) | 같은 지역 중복 선호 방지 |
| team_match_region | (team_id, region_id) | 같은 지역 중복 선호 방지 |
| no_show | (match_id, user_id) | 경기당 1인 1건 |
| review | (match_id, reviewer_id, reviewee_id) | 경기당 1회 평가 |
| player_vector | analysis_metric_id | **미구현** — 지표 집합당 벡터 1건 |
| fitness_score | match_application_id | **미구현** — 지원 건당 적합도 1건 |

## D.8 미확정 사항

| 항목 | 내용 |
|---|---|
| ~~탈퇴와 남는 기록~~ | ✅ **확정됨** (2026.09.17) — 내 기록은 함께 지우고, 남에게 쓴 평가·신고는 작성자만 비운다(D.6). 그 전에는 이 기록이 있으면 DB가 탈퇴를 거부했다 |
| 용병 매칭 조건의 중복 | user 의 용병 검색 칸과 ④의 개인 매칭 조건이 같은 개념을 따로 담는다(D.4). 합칠지, 한쪽을 다른 쪽의 폴백으로 둘지 |
| 미구현 테이블 넷 | player_vector(선수 성향 벡터)·fitness_score(적합도)·recommendation(추천 이력)·title_criteria(분석 호칭 기준). 넣을 시점은 정해지지 않았다. title_criteria 는 호칭을 사람이 적기로 하면서(2026.09.16) 필요가 줄었다 |
| ~~지표 항목~~ | ✅ **확정됨** — 종목 무관 물리량으로 정하고(2026.09.08) 시드로 적재했다(2026.09.10) |
| ~~평가 선택지~~ | ✅ **확정됨** — review_option 시드와 노출 순서(`sort_order`)가 들어갔다(2026.09.03~04) |
| 과금 상세 | 4.3 수익 모델이 확정되지 않아 analysis_credit·coach·coach_referral은 최소 형태다. 구인 측 과금이 채택되면 테이블이 추가된다 |
| 평가·지표 대응 | review_option과 metric_definition의 대응 관계. 누적 보정(3.4) 도입 시 정의한다. 설정 데이터라 소급 적용이 가능하므로 지금 두지 않는다 |
| 브랜드 제휴 | 4.3의 확장 모델은 본 개발 기간 범위 밖이므로 테이블을 두지 않는다 |

---

Super-Sub / 슈퍼서브 · 백성검 · 박민호 · 정상호 · 정어진

미확정 사항은 D.8에 모았다.

[← 목차로]({{ "/toc/" | relative_url }})
