---
layout: default
title: 데이터베이스 ERD
permalink: /부록D-데이터베이스ERD/
parent: 부록
nav_order: 4
---

Super-Sub 플랫폼의 데이터 모델이다. 3장 서비스 기능과 5장 요구사항에서 도출했다.
각자 담당 도메인부터 보면 된다.

**34 테이블 · 6 도메인 · 1~3정규형 준수**

본 부록은 3장에서 정의한 서비스 기능과 5장 요구사항(SFR·SEC)에서 도출한 데이터 모델이다.
34개 테이블을 6개 도메인으로 나누어 정리한다.

제1정규형부터 제3정규형까지 준수한다. 비원자 값(jsonb), 이행 종속 컬럼, 파생·집계 컬럼을 두지
않는다. 정규화 근거와 그에 따른 조회 비용은 D.4에서 다룬다.

user가 대부분의 테이블과 연결되는 허브이므로 전체를 한 장에 그리면 읽을 수 없다. 도메인별로
나누어 정리하고, 전체 외래키 목록은 D.3에 표로 정리한다.

## D.1 한눈에 보기

도메인 사이의 데이터 흐름이다. 영상이 지표가 되고, 그 지표가 카드(표시)와 매칭(판단) 두 갈래로
쓰인다는 것이 이 모델의 골격이다.

![D.1 도메인 간 데이터 흐름]({{ "/assets/erd/d1-overview.svg" | relative_url }}){: class="erd-diagram" }

## D.2 도메인별 상세

컬럼 표에서 "키" 열의 화살표는 참조 대상 테이블이다. 다른 도메인의 테이블을 참조하는 경우는
D.3에 별도로 모았다.

### ① 사용자·팀

![도메인 ① 사용자·팀 ERD]({{ "/assets/erd/domain1-user-team.svg" | relative_url }}){: class="erd-diagram" }

> 위 그림에는 user_credential과 user_identity가 아직 반영되어 있지 않다.
> **표가 최신이다.** 그림은 좌표가 직접 박힌 수작업 SVG라 갱신 비용이 커서 미뤄 둔다.
>
> - `user_credential` — `id uuid PK` · `user_id uuid FK→user` · `password_hash text` ·
>   `updated_at timestamptz`
> - `user_identity` — `id uuid PK` · `user_id uuid FK→user` · `provider text` ·
>   `subject text` · `created_at timestamptz`

| 테이블 | 용도 | 1행이 뜻하는 것 |
|---|---|---|
| user | 계정과 신원 (SEC-003) | 가입한 사람 1명 |
| user_credential | 로그인 자격증명. 비밀번호 해시를 user에 두지 않고 분리한다. 소셜 로그인을 추가할 때 user를 건드리지 않아도 되고, 자격증명 조회 경로를 따로 제한할 수 있다 | 한 사람의 자격증명 1건 |
| user_identity | 외부 제공자(구글 등) 계정과의 연결. provider가 준 고유 ID(subject)를 그대로 보관한다. **이메일로 사람을 식별하지 않는다** — 이메일은 바뀔 수 있고 재사용될 수도 있다 | 한 사람의 한 제공자 연결 1건 |
| team | 동호회 | 등록된 팀 1개 |
| team_member | 소속과 역할. 탈퇴 후에도 경기·평가 이력이 남아야 하므로 left_at으로 소프트 삭제한다. 재가입이 가능하므로 joined_at을 함께 둔다 | 한 사람의 한 팀 소속 구간 1건 |
| sport | 축구·야구·농구 종목 코드 | 종목 1개 (현재 3행) |
| position | 종목별 포지션. 포지션 약칭이 종목 간 겹칠 수 있어 대리키를 두고 (sport_code, code)에 유일 제약을 건다 | 한 종목의 포지션 1개 |

### ② 영상·분석

업로드부터 지표 산출까지 한 줄로 이어지는 체인이다. 이 순서가 곧 SEC-006의 삭제 연쇄 경로가
된다(D.6).

지표는 종목마다 항목이 다르므로 컬럼으로 고정하지 않는다. metric_definition에 항목을 정의하고
analysis_metric_value에 항목당 한 행씩 적재한다.

![도메인 ② 영상·분석 ERD]({{ "/assets/erd/domain2-video-analysis.svg" | relative_url }}){: class="erd-diagram" }

| 테이블 | 용도 | 1행이 뜻하는 것 |
|---|---|---|
| video | 업로드한 클립의 저장 위치와 메타 (SFR-001) | 업로드된 클립 1개 |
| video_validation | 규격 검사 결과와 반려 사유. 사유를 값으로 남겨야 검수 기준을 확인할 수 있다 | 클립 1개의 검사 결과 |
| analysis_job | 비동기 분석 작업의 상태와 소요 시간 (PER-001) | 분석 실행 1회 |
| analysis_metric | 분석 1회가 산출한 지표 집합. 산출 버전을 기록한다 (QUA-002) | 분석 실행 1회가 낸 지표 묶음 |
| metric_definition | 종목별 지표 항목의 정의와 단위 | 지표 항목 1개 (예: 임팩트 시 무릎 각도) |
| analysis_metric_value | 지표 항목별 값 (SFR-002) | 지표 묶음 1개 안의 항목 1개 값 |
| analysis_report | 지표를 근거로 생성한 요약 문장 (SFR-003) | 지표 묶음 1개의 요약문 |
| player_vector | 성향 비교용 특징 벡터. pgvector로 색인한다 (SFR-005) | 지표 묶음 1개의 임베딩 |

### ③ 카드·호칭

호칭 기준도 종목·항목마다 다르므로 title_criteria에 조건 한 줄씩 나누어 담는다.

![도메인 ③ 카드·호칭 ERD]({{ "/assets/erd/domain3-card-title.svg" | relative_url }}){: class="erd-diagram" }

| 테이블 | 용도 | 1행이 뜻하는 것 |
|---|---|---|
| title_definition | 호칭의 종류와 분류(강점·활동·용병) (SFR-004) | 호칭 1종 |
| title_criteria | 호칭별 절대 기준. 항목·비교연산자·임계값을 행으로 나눈다 | 호칭 1종의 판정 조건 1줄 |
| user_title | 호칭 부여 이력 | 한 사람이 받은 호칭 1개 |
| player_card | 공개 카드와 공유용 슬러그 (SFR-009) | 한 사람의 카드 1장 |
| squad | 팀 단위 카드 묶음 | 한 팀의 스쿼드 1개 |
| squad_member | 스쿼드에 등재된 카드와 포지션 | 스쿼드 1개에 등재된 카드 1장 |

### ④ 매칭

![도메인 ④ 매칭 ERD]({{ "/assets/erd/domain4-matching.svg" | relative_url }}){: class="erd-diagram" }

| 테이블 | 용도 | 1행이 뜻하는 것 |
|---|---|---|
| match | 경기 등록 (SFR-010). 종목은 team이 결정하므로 컬럼을 두지 않는다 | 등록된 경기 1건 |
| match_position_need | 경기별 필요 포지션과 인원. 포지션이 둘 이상일 수 있어 행으로 나눈다 | 경기 1건의 포지션 1종 필요분 |
| match_application | 지원과 제안. 양측 수락 시각을 각각 갖고, 둘 다 채워진 상태를 확정으로 본다 | 경기 1건에 대한 한 사람의 지원 1건 |
| fitness_score | 수준·역할·성향 3축 적합도 (SFR-006) | 지원 1건의 적합도 산출 결과 |
| recommendation | 후보 추천 이력과 추천 사유 (SFR-007) | 경기 1건에 제시된 후보 1명 |

### ⑤ 평가·신뢰

평가는 선택형이므로(3.4) 선택지를 review_option에 정의하고 선택 결과를 review_selection에
행으로 담는다.

![도메인 ⑤ 평가·신뢰 ERD]({{ "/assets/erd/domain5-review-trust.svg" | relative_url }}){: class="erd-diagram" }

| 테이블 | 용도 | 1행이 뜻하는 것 |
|---|---|---|
| review | 경기 후 상호 평가의 제출 사실과 시점 (SFR-008) | 경기 1건에서 A가 B를 평가한 1건 |
| review_option | 평가 선택지 정의 | 선택지 1개 |
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

![도메인 ⑥ 과금 ERD]({{ "/assets/erd/domain6-billing.svg" | relative_url }}){: class="erd-diagram" }

| 테이블 | 용도 | 1행이 뜻하는 것 |
|---|---|---|
| analysis_credit | 분석 크레딧의 증감 이력. 잔량은 delta의 합으로 구한다 | 크레딧 증감 1건 (지급 또는 차감) |
| coach | 제휴 코치 | 제휴 코치 1명 |
| coach_referral | 레슨·코치 연결과 수수료 | 코치 연결 1건 |

무료 한도는 크레딧 지급(delta 양수)으로 표현하고, 분석 1건마다 차감(delta 음수)한다. 따라서
무료 한도를 두든 건당 과금을 하든 테이블 구조는 같다. 과금 방식이 확정되어도 analysis_credit은
그대로 쓴다.

구인 측(팀)에 과금하는 경로는 아직 반영하지 않았다. 4.3 수익 모델이 확정되면 해당 과금 행위를
기록할 테이블을 추가한다(D.8).

## D.3 도메인을 잇는 외래키

도메인 경계를 넘는 외래키를 한곳에 모았다. 대부분이 user를 향하며, 이것이 34개 테이블을 한
장에 그릴 수 없는 이유다.

| 출발 테이블 | 컬럼 | 도착 | 의미 |
|---|---|---|---|
| video | user_id | user | 업로더 |
| video | sport_code | sport | 종목 |
| metric_definition | sport_code | sport | 종목별 지표 항목 |
| title_definition | sport_code | sport | 종목별 호칭 기준 |
| title_criteria | metric_code | metric_definition | 판정에 쓰는 지표 항목 |
| user_title | user_id | user | 호칭 대상자 |
| user_title | source_metric_id | analysis_metric | 호칭 부여 근거 |
| player_card | user_id | user | 카드 소유자 |
| squad | team_id | team | 소속 팀 |
| squad_member | position_id | position | 포지션 |
| match | team_id | team | 주최 팀 |
| match_position_need | position_id | position | 필요 포지션 |
| match_application | user_id | user | 지원자 |
| recommendation | candidate_user_id | user | 추천 후보 |
| review | match_id | match | 대상 경기 |
| review | reviewer_id · reviewee_id | user | 평가자와 피평가자 |
| report | reporter_id · target_user_id | user | 신고자와 대상 |
| no_show | match_id · user_id | match · user | 불참 경기와 대상 |
| analysis_credit | user_id | user | 크레딧 소유자 |
| coach_referral | user_id | user | 연결 요청자 |

user_title.source_metric_id만 성격이 다르다. 나머지가 소유·참조 관계인 데 반해 이것은 호칭이
어느 분석에서 나왔는지를 남기는 근거 링크이고, 삭제 연쇄에도 관여한다(D.6). 활동·용병 호칭은
분석에서 나오지 않으므로 이 컬럼은 널을 허용한다.

## D.4 정규화

### 제1정규형 — 모든 컬럼이 원자값이다

| 대상 | 처리 |
|---|---|
| 지표값 | jsonb 대신 metric_definition + analysis_metric_value로 전개했다. 지표 항목이 종목마다 달라 컬럼 고정이 불가능하므로 항목을 데이터로 둔다 |
| 호칭 기준 | jsonb 대신 title_criteria에 조건 한 줄씩 담는다 |
| 필요 포지션 | 문자열 한 컬럼 대신 match_position_need로 분리했다. 포지션이 둘 이상일 수 있다 |
| 평가 선택 결과 | review_selection으로 분리했다 |

fitness_score의 level_axis·role_axis·style_axis는 반복 그룹이 아니다. 수준·역할·성향 세 개의
서로 다른 속성이며, 축별로 개별 반환하는 것이 SFR-006의 검수 기준이다.

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
| 벡터 검색 (SFR-005) | 사용자로 좁히려면 player_vector → analysis_metric → analysis_job → video 4단 조인이 필요하다. PER-003의 P95 500ms에 가장 위험한 지점 | 조인 결과 뷰, 또는 부분 인덱스 |
| 지표 조회 | 지표 1건이 여러 행이라 조회 시 피벗이 필요하다 | 지표 집합 단위 조회 후 애플리케이션에서 조립 |
| 크레딧 잔량 | 매번 SUM(delta) | 사용자별 인덱스, 필요 시 구체화 뷰 |
| 평가자 신뢰도 | 매 산출 시 집계 | 구체화 뷰와 주기적 갱신 |

## D.5 설계 원칙이 스키마에 반영된 지점

3장에서 확정한 원칙 가운데 스키마 구조로 강제한 것을 정리한다. 코드에만 두면 지켜지지 않으므로
테이블 설계 단계에서 막는다.

| 원칙 | 출처 | 스키마 반영 |
|---|---|---|
| 카드에 수치 능력치를 노출하지 않는다 | 3.5 | player_card에 능력치 컬럼을 두지 않는다. 수치는 analysis_metric_value에만 있고 리포트 경로로만 조회된다 |
| 호칭은 미부여 방식으로만 작동한다 | 3.5 | user_title은 부여된 행만 존재한다. 미달을 false로 저장하지 않는다. 그렇게 두면 조회 시 부정 표식이 된다 |
| 전체 순위표를 두지 않는다 | 3.4 | 사용자 간 비교 점수를 저장하는 테이블을 두지 않는다. fitness_score는 경기 지원 건에 종속되며 단독 조회 대상이 아니다 |
| 매칭 확정은 사람이 한다 | 3.3 | match_application이 team_accepted_at·user_accepted_at을 각각 갖는다. 단일 상태값으로 두면 확정 조건이 코드에만 남는다 |
| 추천에는 근거를 함께 제시한다 | 3.3 | recommendation.reason을 NOT NULL로 둔다 |
| 지표 산출은 재현 가능해야 한다 | 3.3 | analysis_metric.pipeline_version으로 산출 버전을 기록한다. LLM 생성물인 analysis_report는 테이블을 분리해 지표에 섞이지 않게 한다 |
| 평가 이력은 처음부터 저장한다 | 3.4 | review가 평가자·시점을, review_selection이 선택 결과를 남긴다. 신뢰도는 여기서 언제든 다시 계산한다 |
| 제재는 평가가 아니라 기록으로 처리한다 | 3.5 | report·no_show를 review와 분리한다 |

## D.6 삭제 연쇄

SEC-006은 삭제 요청 시 원본과 파생물이 함께 삭제될 것을 요구한다. 영상 한 건의 파생물은 다음
경로로 이어지므로, 이 체인의 외래키 삭제 규칙을 스키마 확정 시 일괄로 정한다.

![D.6 영상 삭제 연쇄 경로]({{ "/assets/erd/d6-cascade.svg" | relative_url }}){: class="erd-diagram" }

user_title은 호칭 부여의 근거가 되는 지표를 참조한다. 근거가 삭제되면 호칭도 함께 회수되어야
하므로 이 체인에 포함한다.

계정 탈퇴는 별개의 경로다. user가 삭제되면 user_credential과 user_identity도 함께
삭제된다(ON DELETE CASCADE). 자격증명과 외부 계정 연결은 계정에 완전히 종속되며 단독으로
남을 이유가 없다. 특히 user_identity가 남으면 **같은 구글 계정으로 다시 가입할 때 사라진
사용자를 가리키게 된다.** 반면 team_member는 left_at으로
소프트 삭제하므로 이 연쇄에 넣지 않는다 — 경기·평가 이력이 참조하고 있다.

## D.7 주요 제약조건

기본키 외에 유일 제약이 필요한 곳이다.

| 테이블 | 유일 제약 | 이유 |
|---|---|---|
| user | email | 계정 식별 |
| user_credential | user_id | 사용자당 자격증명 1건 |
| user_identity | (provider, subject) | 한 외부 계정이 두 사용자에 붙는 것을 막는다 |
| user_identity | (user_id, provider) | 한 사용자가 같은 제공자를 두 번 연결하지 못하게 한다 |
| position | (sport_code, code) | 포지션 약칭이 종목 간 겹칠 수 있다 |
| video_validation | video_id | 영상당 검사 결과 1건 |
| analysis_metric | analysis_job_id | 작업당 지표 집합 1건 |
| analysis_metric_value | (analysis_metric_id, metric_code) | 항목당 값 1건 |
| analysis_report | analysis_metric_id | 지표 집합당 요약 1건 |
| player_vector | analysis_metric_id | 지표 집합당 벡터 1건 |
| player_card | user_id, public_slug | 사용자당 카드 1건, 슬러그 중복 방지 |
| squad | public_slug | 슬러그 중복 방지 |
| user_title | (user_id, title_code) | 같은 호칭 중복 부여 방지 |
| match_application | (match_id, user_id) | 경기당 1인 1회 지원 |
| fitness_score | match_application_id | 지원 건당 적합도 1건 |
| review | (match_id, reviewer_id, reviewee_id) | 경기당 1회 평가 |
| team_member | (team_id, user_id, joined_at) | 재가입 이력을 남기면서 중복 소속을 막는다 |
| squad_member | (squad_id, player_card_id) | 스쿼드당 카드 1회 등재 |
| match_position_need | (match_id, position_id) | 경기당 포지션 1행 |
| no_show | (match_id, user_id) | 경기당 1인 1건 |

## D.8 미확정 사항

| 항목 | 내용 |
|---|---|
| 지표 항목 | metric_definition에 들어갈 종목별 항목 목록. 스프린트 1에서 확정한다 |
| 평가 선택지 | review_option의 항목 구성. 3.4의 피해 상한 설계와 함께 정한다 |
| 과금 상세 | 4.3 수익 모델이 확정되지 않아 analysis_credit·coach_referral은 최소 형태다. 구인 측 과금이 채택되면 테이블이 추가된다 |
| 평가·지표 대응 | review_option과 metric_definition의 대응 관계. 누적 보정(3.4) 도입 시 정의한다. 설정 데이터라 소급 적용이 가능하므로 지금 두지 않는다 |
| 브랜드 제휴 | 4.3의 확장 모델은 본 개발 기간 범위 밖이므로 테이블을 두지 않는다 |

---

Super-Sub / 슈퍼서브 · 백성검 · 박민호 · 정상호 · 정어진

지표 항목과 평가 선택지는 스프린트 1에서 확정한다. D.8 미확정 사항을 함께 확인한다.

[← 목차로]({{ "/toc/" | relative_url }})
