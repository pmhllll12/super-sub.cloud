# Super-Sub Flutter 앱 설계

- 작성일: 2026-08-25
- 작성자: 백성검
- 브랜치: `paik`
- 근거 문서: [부록 D 데이터베이스 ERD](/부록D-데이터베이스ERD/) (32테이블 · 6도메인)

---

## 0. 범위와 제약

3장 서비스 제안, 5장 요구사항, 6장 시스템 설계가 아직 미작성이다. 따라서 **부록 D의 ERD와
거기 인용된 SFR·SEC·PER 코드가 현재 유일한 확정 근거**다. 이 문서의 모든 기능은 ERD의
테이블에서 역산했고, 근거 없는 화면은 만들지 않는다.

| 항목 | 결정 |
|---|---|
| 작업 경로 | 저장소의 `app/` 디렉터리 **안으로만** 한정 |
| 건드리지 않는 것 | `jekyll/`, `_config.yml`, `_posts/`, `_layouts/`, `assets/`, 루트 파일 전부 |
| 백엔드 | 없음. Mock 구현체로 전 화면을 동작시키고, API가 나오면 구현체만 교체 |
| 역할 범위 | 개인(용병)과 팀 관리자 두 역할을 한 앱에서 처리 |
| 대상 플랫폼 | Android / iOS (웹은 공개 카드 딥링크 확인용으로만 고려) |

`app/`은 다섯 브랜치(`main` `paik` `jin` `min` `ho`) 어디에도 존재하지 않는 새 경로다.
따라서 이 작업은 다른 사람의 브랜치와 git 충돌이 발생하지 않는다.

---

## 1. 설계의 중심 원칙 — 스키마 불변식을 타입으로 옮긴다

ERD의 D.5절은 "설계 원칙이 스키마에 반영된 지점" 8가지를 못박아 두었다. 문제는 **그 8가지가
전부 앱 UI에서 다시 깨질 수 있다**는 것이다. 스키마는 `player_card`에 능력치 컬럼을 두지
않았지만, 앱에서 리포트 화면의 수치를 카드 위젯에 넘기면 그 원칙은 그대로 무너진다.

그래서 이 앱의 기초는 **원칙을 주석이 아니라 Dart 타입으로 강제하는 것**이다. 지켜지지 않는
규칙은 규칙이 아니고, 타입은 지켜진다.

| 원칙 (출처) | 스키마의 방어 | 앱에서의 방어 |
|---|---|---|
| 카드에 수치 능력치를 노출하지 않는다 (3.5) | `player_card`에 능력치 컬럼 없음 | `PlayerCard` 모델에 `MetricValue` 필드를 두지 않는다. 수치는 `AnalysisReport` 경로로만 조회 |
| 호칭은 미부여 방식으로만 작동한다 (3.5) | `user_title`은 부여된 행만 존재 | 호칭 목록에 "잠김/미달성" 상태를 만들지 않는다. `List<UserTitle>`은 획득분만 |
| 전체 순위표를 두지 않는다 (3.4) | 사용자 간 비교 점수 테이블 없음 | 전역 랭킹 라우트를 만들지 않는다. `FitnessScore`는 경기 맥락에서만 조회 |
| 매칭 확정은 사람이 한다 (3.3) | `team_accepted_at` · `user_accepted_at` 분리 | `MatchApplication`에 `status` 필드를 두지 않고 두 시각에서 파생시킨다 |
| 추천에는 근거를 함께 제시한다 (3.3) | `recommendation.reason` NOT NULL | `Recommendation.reason`을 non-nullable `String`으로, 후보 카드 위젯의 **필수 인자**로 |
| 적합도는 3축을 개별 반환한다 (SFR-006) | `level_axis` · `role_axis` · `style_axis` 분리 | `FitnessScore`에 `total`·`average` 게터를 두지 않는다 |
| 제재는 평가가 아니라 기록으로 처리한다 (3.5) | `report` · `no_show`를 `review`와 분리 | 평가 화면에 신고 진입점을 두지 않는다 |
| 지표 산출은 재현 가능해야 한다 (3.3) | `analysis_metric.pipeline_version` | 리포트 화면에 산출 버전을 표시 |

여기에 ERD를 읽으며 도출한 두 가지를 더한다.

| 원칙 | 근거 | 앱에서의 방어 |
|---|---|---|
| 평가는 선택형만, 자유 서술 없음 | `review`에 코멘트 컬럼이 없음 (3.4 피해 상한 설계) | 평가 화면에 `TextField`를 두지 않는다. 선택 칩만 |
| 미확정 설정 데이터를 하드코딩하지 않는다 | D.8에서 지표 항목·평가 선택지가 미확정 | `metric_definition`·`review_option`·`title_definition`을 enum으로 박지 않고 조회해서 렌더 |

---

## 2. 아키텍처

### 2.1 방식 — 기능(도메인)별 수직 분할 + Repository 추상화

ERD의 6도메인을 거의 그대로 feature로 옮긴다. 각 feature 안에 모델·리포지토리·화면·컨트롤러를
함께 둔다. 계층을 가로로 자르지 않고 기능으로 세로로 자른다.

이 방식을 택한 이유는 셋이다.

1. **백엔드 교체 지점이 한 곳으로 모인다.** 화면은 리포지토리 인터페이스만 알고, 그것이
   Mock인지 API인지 모른다. 교체는 provider 한 줄이다.
2. **엄격한 Clean Architecture(3계층 + UseCase)보다 파일 수가 적다.** 10주에 Flutter 담당이
   1명인 조건에서 구조 유지 비용이 낮아야 한다.
3. **기능 단위로 병렬 작업이 가능하다.** 나중에 인원이 붙어도 feature 폴더 단위로 나눌 수 있다.

### 2.2 기술 선택

| 영역 | 선택 | 이유 |
|---|---|---|
| 상태관리 | `flutter_riverpod` | 리포지토리 교체가 provider override 한 줄로 끝난다. 테스트에서 주입도 같은 방식 |
| 라우팅 | `go_router` | 공개 카드 `public_slug` 딥링크(SFR-009)가 필수 요건이라 URL 기반 라우팅이 필요 |
| 모델 | `freezed` + `json_serializable` | 불변 모델·`copyWith`·`fromJson`. API 전환 시 직렬화를 새로 짜지 않아도 된다 |
| 기타 | `uuid`, `intl` | Mock의 ID 생성, 날짜·시각 표기 |

`freezed`는 `build_runner`가 필요해 초기 마찰이 있다. **단계 1(토대)에서는 코드 생성을 쓰지
않는다.** 지금은 JSON이 존재하지 않으므로(Mock 전용) 직렬화 코드 생성은 근거 없는 선반영이다.
손으로 쓴 불변 클래스(`const` 생성자 + `copyWith` + `==`/`hashCode`)로 시작하고, 도입은 API
스펙이 정해지는 단계 7에서 모델 수를 보고 재검토한다.

### 2.3 디렉터리 구조

```
app/
  lib/
    main.dart
    app.dart                      # MaterialApp.router
    core/
      router/router.dart          # go_router 라우트 정의
      theme/                      # 색·타이포·컴포넌트 테마
      sport/sport_scope.dart      # 종목 전역 컨텍스트 (3절)
      result/                     # 로딩·에러·빈 상태 공통 처리
      widgets/                    # 도메인 무관 공통 위젯
      mock/mock_db.dart           # Mock 공용 인메모리 저장소 (4.3)
    features/
      auth/                       # user, 세션
      team/                       # team, team_member, sport, position
      video/                      # video, video_validation
      analysis/                   # analysis_job, metric, value, report
      card/                       # player_card, user_title, squad
      match/                      # match, need, application, fitness, recommendation
      review/                     # review, option, selection, report, no_show
      credit/                     # analysis_credit, coach, coach_referral
  test/
    contract/                     # 리포지토리 계약 테스트 (9절)
  docs/                           # 이 문서
  .gitignore                      # 루트 .gitignore를 건드리지 않기 위해 여기 둔다
```

각 feature는 다음 형태를 갖는다.

```
features/match/
  data/
    models/                       # Match, MatchApplication, FitnessScore, ...
    match_repository.dart         # 인터페이스 — 화면이 아는 유일한 것
    match_repository_mock.dart    # 지금 쓰는 구현체
    match_repository_api.dart     # 나중에 추가 (지금은 없음)
    match_providers.dart          # provider 정의 — 교체 지점
  presentation/
    screens/
    widgets/
    controllers/
```

**루트 `.gitignore`를 수정하지 않는다.** Flutter의 `build/`, `.dart_tool/` 등은
`app/.gitignore`에 둔다. git은 하위 디렉터리의 `.gitignore`를 그대로 적용한다.

---

## 3. 종목(sport) 전역 컨텍스트

ERD에서 `metric_definition`, `title_definition`, `position`이 모두 `sport_code`에 매달려
있다. 즉 **지표도 호칭도 포지션도 종목마다 다르다.** 이것을 나중에 끼워넣으면 거의 모든
화면을 고치게 되므로 처음부터 전역 컨텍스트로 둔다.

- 온보딩에서 종목을 고르고 `currentSportProvider`에 저장한다.
- 지표·호칭·포지션·경기 탐색을 조회하는 **모든 리포지토리 메서드는 `sportCode`를 받는다.**
- 사용자가 두 종목을 다 하는 경우가 있으므로 종목 전환을 홈 상단에 둔다.
- `match`에는 `sport_code`가 없다(3정규형, `match → team → sport`). 따라서 경기 탐색의
  종목 필터는 팀을 거친다. 앱 모델에서는 `Match`가 `Team`을 품는 형태로 받는다.

---

## 4. 데이터 계층

### 4.1 인터페이스 규칙

```dart
abstract class MatchRepository {
  Future<List<Match>> openMatches({required String sportCode, String? region});
  Future<Match> matchDetail(String matchId);
  Future<MatchApplication> apply({required String matchId, required String positionId});
  Future<List<MatchApplication>> myApplications();
  // 팀 관리자
  Future<Match> createMatch({required String teamId, required DateTime playedAt, required String place});
  Future<void> setPositionNeeds(String matchId, List<PositionNeed> needs);
  Future<List<Applicant>> applicants(String matchId);
  Future<void> acceptApplication(String applicationId);
  Future<List<Recommendation>> recommendations(String matchId);
}
```

지켜야 할 세 가지다.

1. **도메인 모델로만 말한다.** `Map<String, dynamic>`이나 DTO를 리턴하지 않는다. 화면이 API
   응답 모양에 묶이면 서버 스펙이 바뀔 때마다 화면을 고치게 된다.
2. **모두 `Future`다.** 동기 반환이 하나라도 있으면 API 전환 시 그 화면을 다시 짠다.
3. **ID·생성 시각은 서버 소유로 가정한다.** 생성 결과는 서버(지금은 Mock)가 돌려주는 것을 쓴다.

### 4.2 교체 지점

```dart
final matchRepositoryProvider = Provider<MatchRepository>(
  (ref) => MockMatchRepository(ref.read(mockDbProvider)),
  // API 완성 후: (ref) => ApiMatchRepository(ref.read(dioProvider)),
);
```

feature가 8개이므로 교체 대상은 provider 8줄이다. 화면·위젯·컨트롤러는 수정하지 않는다.

### 4.3 Mock 구현 규칙

Mock이 "항상 즉시 성공"하면 로딩 UI와 에러 UI를 만들지 않게 되고, API를 붙이는 날 화면을
다시 짜게 된다. 그래서 Mock은 진짜처럼 굴어야 한다.

- 모든 응답에 `Future.delayed(200~500ms)`를 넣는다.
- 실패 케이스를 재현할 수 있게 한다 (설정 화면에 개발자용 "Mock 실패율" 토글).
- 빈 목록, 첫 사용자(영상 0건·호칭 0개) 상태를 기본 시드에 포함한다.
- **모든 Mock 리포지토리는 `MockDb` 하나를 공유한다.** feature마다 각자 가짜 데이터를 들고
  있으면 서로 모순된다 — 경기가 존재하지 않는 팀을 참조하는 식이다. 인메모리 저장소 하나에
  ERD와 같은 구조로 시드를 넣고 모든 Mock이 거기서 읽는다.
- 분석은 비동기다. `MockDb`가 `analysis_job.status`를 시간에 따라
  `queued → running → done`으로 실제로 전이시킨다.

---

## 5. 화면 목록과 라우팅

### 5.1 원칙 — 라우트 ≠ 화면

테이블마다 화면을 하나씩 붙이면 36개가 나온다. 그러나 실제 앱은 그렇게 만들지 않는다.
**딥링크로 진입해야 하거나, 뒤로가기의 착지점이 되어야 하는 것만 풀 페이지로 둔다.** 나머지는
기존 화면의 탭·바텀시트·다이얼로그로 처리한다.

그 기준으로 정리하면 **디자인·구현 대상 화면은 21개, 서브뷰가 17개**다. 10주 · 1인 개발
조건에서 21개는 상한선에 가까운 수치이고, Sprint 2 데모에 필요한 최소 코어는 그중 10개다.

화면 수보다 **재사용 위젯을 몇 개 만드느냐가 실제 작업량을 좌우한다.** 선수 카드, 3축 적합도,
호칭 배지, 지표 리스트 — 이 넷을 제대로 만들어두면 나머지 화면은 대부분 조립으로 끝난다.

`/splash`는 화면이 아니라 라우팅 분기 로직이므로 목록에서 제외한다 (`go_router`의 `redirect`).

### 5.2 풀 페이지 (21)

`[팀]`은 팀 관리자 역할 전용이다.

| 라우트 | 화면 | 품고 있는 서브뷰 | 근거 |
|---|---|---|---|
| `/login` | 로그인 | 회원가입 토글, 개발용 바로 진입 | `user`, SEC-003 |
| `/onboarding/sport` | 종목 선택 | — | `sport` |
| `/home` | 홈 (종목 전환, 진입점) | — | — |
| `/profile` | 내 프로필 | 프로필 수정, 받은 평가 탭 | `user`, `position`, `review_selection` |
| `/settings` | 설정 | 영상 삭제 확인 | SEC-006 |
| `/videos` | 내 영상 목록 + 분석 상태 | 영상 상세 펼침, 반려 사유 | `video`, `analysis_job`, `video_validation` |
| `/videos/upload` | 영상 업로드 | — | `video`, SFR-001 |
| `/analysis/:jobId/report` | 분석 리포트 | — | `analysis_report`, `analysis_metric_value`, SFR-002·003 |
| `/card` | 내 선수 카드 | 호칭 탭, 호칭 근거 | `player_card`, `user_title`, SFR-004·009 |
| `/c/:slug` | 공개 카드 (딥링크·비로그인) | — | `player_card.public_slug` |
| `/teams` | 내 팀 목록 | 팀 만들기, 팀 가입 | `team_member` |
| `/teams/:teamId` | 팀 상세·팀원 | 스쿼드 탭 | `team`, `team_member`, `squad` |
| `/matches` | 경기 탐색 | — | `match`, `team`, `match_position_need` |
| `/matches/:matchId` | 경기 상세 | 지원 (포지션 선택) | `match_position_need`, `match_application` |
| `/applications` | 내 지원 현황 | — | `match_application` |
| `/teams/:teamId/matches/new` | [팀] 경기 등록 | 필요 포지션·인원 (2단계) | `match`, `match_position_need`, SFR-010 |
| `/matches/:matchId/applicants` | [팀] 지원자 관리 | 추천 후보 탭, 불참 기록 | `match_application`, `fitness_score`, `recommendation`, `no_show` |
| `/reviews/pending` | 평가 대상 목록 | — | `match_application`, `review` |
| `/reviews/new/:matchId/:revieweeId` | 평가 작성 | — | `review`, `review_option`, SFR-008 |
| `/credits` | 크레딧 잔량·내역 | 차감 확인 | `analysis_credit` |
| `/coaches` | 제휴 코치 목록 | 코치 연결 요청 | `coach`, `coach_referral` |

### 5.3 서브뷰 (17)

풀 페이지가 아니라 기존 화면 안의 요소로 구현한다.

| 서브뷰 | 형태 | 위치 |
|---|---|---|
| 회원가입 | 화면 내 토글 | `/login` |
| 개발용 바로 진입 | 하단 목록 (`kDebugMode`) | `/login` |
| 프로필 수정 | 바텀시트 | `/profile` |
| 받은 평가 | 탭 | `/profile` |
| 영상 상세 | 목록 아이템 펼침 | `/videos` |
| 규격 반려 사유 | 바텀시트 | `/videos` |
| 호칭 목록 | 탭 | `/card` |
| 호칭 근거 | 바텀시트 | `/card` 호칭 탭 |
| 팀 만들기 | 다이얼로그 | `/teams` |
| 팀 가입 (초대코드) | 다이얼로그 | `/teams` |
| 스쿼드 | 탭 | `/teams/:teamId` |
| 경기 지원 (포지션 선택) | 바텀시트 | `/matches/:matchId` |
| 필요 포지션·인원 설정 | 등록 폼 2단계 | `/teams/:teamId/matches/new` |
| 추천 후보 | 탭 | `/matches/:matchId/applicants` |
| 불참·지각 기록 | 액션 + 확인 다이얼로그 | `/matches/:matchId/applicants` |
| 신고 | 다이얼로그 | `/profile`, `/matches/:matchId` |
| 코치 연결 요청 | 바텀시트 | `/coaches` |

### 5.4 개발용 바로 진입과 시드 계정

로그인은 Mock으로 실제 동작한다(네트워크 호출 없음). 그럼에도 개발 중 매번 입력하는 비용이
크므로, 로그인 화면 하단에 **디버그 빌드에서만 보이는** 바로 진입 목록을 둔다.

```dart
if (kDebugMode) ...[
  const Divider(),
  _DevLoginButton('개인 사용자 (데이터 있음)', seed: MockDb.player),
  _DevLoginButton('팀 관리자',              seed: MockDb.manager),
  _DevLoginButton('신규 가입자 (데이터 0건)', seed: MockDb.newbie),
]
```

`kDebugMode`로 감싸면 릴리즈 빌드에서 코드째 제거되므로 발표용 빌드에는 나타나지 않는다.

시드 계정을 셋으로 두는 이유는 각각 다르다.

| 계정 | 목적 |
|---|---|
| 개인 사용자 | 영상·호칭·지원 이력이 있는 상태. 대부분의 화면 확인용 |
| 팀 관리자 | `[팀]` 전용 화면 2개와 서브뷰 3개는 역할이 달라야 진입할 수 있다 |
| 신규 가입자 | 영상 0건·호칭 0개. **빈 상태 UI를 만들도록 강제하는 장치.** 이 계정이 없으면 빈 화면 디자인을 끝까지 미루게 되고, 실제 서비스에서 신규 사용자가 처음 보는 화면이 바로 그것이다 |

### 5.5 도메인별로 지켜야 할 것

#### 사용자·팀

`team_member.left_at`은 소프트 삭제다. 재가입이 가능해 `(team_id, user_id, joined_at)`이
유일키이므로, 모델에 `bool get isActive => leftAt == null`을 두고 "내 팀"은 활성만 보여준다.

#### 영상·분석

- **분석은 비동기다.** `analysis_job.status`가 테이블에 있다는 것은 업로드 즉시 결과가 나오지
  않는다는 뜻이다. "업로드 → 로딩 → 결과" 한 화면이 아니라, 업로드하면 목록으로 돌아가고
  나중에 완료를 확인하는 구조로 만든다 (PER-001).
- **지표는 행이지 컬럼이 아니다.** `class Metrics { double kneeAngle; ... }` 처럼 짜지 않는다.
  항목 목록은 `metric_definition`에 있고 D.8에서 아직 미확정이다. `List<MetricValue>`
  (code·name·unit·value)로 받아 리스트로 렌더한다.
- **삭제는 파생물 연쇄를 명시한다.** D.6의 체인이 영상 → 분석 → 지표 → 리포트 → 벡터 →
  **호칭 회수**까지 간다. 삭제 확인 다이얼로그에 "이 영상으로 받은 호칭 N개도 함께
  회수됩니다"를 반드시 표시한다.
- 리포트 화면에 `analysis_metric.pipeline_version`을 표시한다 (재현 가능성, 3.3).

#### 카드·호칭

- `PlayerCard` 모델은 지표값 필드를 갖지 않는다 (1절).
- 호칭 탭에 "잠김/미달성" 섹션을 만들지 않는다.
- `source_metric_id`는 **nullable**이다. 활동·용병 호칭은 분석에서 나오지 않는다.
  `sourceMetricId == null`이면 근거 보기 진입 자체를 렌더하지 않는다.

#### 매칭

**확정은 상태값이 아니라 두 시각의 AND다.**

```dart
bool get isConfirmed => teamAcceptedAt != null && userAcceptedAt != null;
```

이 테이블 하나가 두 방향을 모두 표현한다. 개인이 먼저 지원하면 `user_accepted_at`만 차고,
팀이 먼저 제안(스카우트)하면 `team_accepted_at`만 찬다. UI의 "지원함 / 제안받음 / 확정"은
**어느 쪽이 먼저 찼는지로 파생**되는 것이지 별도 필드가 아니다. 이를 모르고 `status` 필드를
두면 나중에 스카우트 기능을 넣을 때 테이블을 하나 더 만들자는 얘기가 나온다.

- 적합도는 3축을 개별 표시한다. 평균이나 별점으로 환산하면 SFR-006의 검수 기준을 깬다.
- 추천 카드 위젯은 `reason`을 필수 인자로 받는다. 사유 없는 추천 카드는 컴파일되지 않아야 한다.
- `fitness_score`는 경기 지원 건에 종속되며 단독 조회 대상이 아니다 — **용병 랭킹 화면을
  만들지 않는다.**
- `match`에는 `sport_code`가 없다(`match → team → sport`). 경기 탐색의 종목 필터는 팀을 거친다.

#### 평가·신뢰

- **자유 텍스트 입력을 만들지 않는다.** `review`에 코멘트 컬럼이 없다. 3.4의 피해 상한 설계가
  스키마로 나타난 것이므로 `TextField` 하나로 무너진다. 선택 칩만 둔다.
- **선택지를 하드코딩하지 않는다.** `review_option` 구성은 D.8에서 미확정이다. 조회해서
  `category`별로 묶어 렌더한다.
- **경기당 1회, 수정 없음.** `(match_id, reviewer_id, reviewee_id)` 유일 제약이다. 평가한
  상대는 목록에서 제외하거나 읽기 전용으로 둔다.
- **신고는 평가 화면에 두지 않는다.** 프로필이나 경기 상세에서 별도로 들어간다.

#### 과금

- **잔량은 값이 아니라 합계다.** `balance` 컬럼을 3정규형 때문에 뺐고 잔량은 `SUM(delta)`다.
  앱이 로컬 변수를 `-1` 하는 방식은 쓰지 않는다. 분석 요청 후 서버에서 잔량을 다시 읽는다.
- 지급(양수)과 차감(음수)이 한 리스트다. 무료 한도도 지급으로 표현되므로 화면은 하나다.
- **팀(구인 측) 결제 화면은 만들지 않는다.** 4.3 수익 모델이 미확정이라 테이블 자체가 없다(D.8).
- 분석 요청 전에 차감 안내를 띄우고, 잔량이 부족하면 요청을 차단한다.

## 6. 상태·에러 처리

모든 비동기 화면은 네 가지 상태를 갖는다. 공통 위젯으로 처리해 화면마다 다시 짜지 않는다.

| 상태 | 처리 |
|---|---|
| 로딩 | 스켈레톤 또는 인디케이터 |
| 성공 | 본 내용 |
| 빈 결과 | 빈 상태 안내 + 다음 행동 유도 (예: "아직 영상이 없습니다 → 업로드") |
| 오류 | 사유 + 재시도 버튼 |

Mock이 지연·실패·빈 목록을 실제로 만들어내므로(4.3) 이 네 상태는 개발 중에 계속 눈에 띈다.
이것이 Mock을 진짜처럼 만드는 이유다.

---

## 7. 알림 — 미해결 지점

ERD에 알림 테이블이 없다. 그런데 이 앱은 알림 없이는 성립이 어렵다.

- 분석이 비동기다 → "분석이 완료되었다"를 알려야 한다 (`analysis_job.status` 전이).
- 매칭이 양측 수락이다 → "팀이 수락했다"를 알려야 한다 (`team_accepted_at` 기록).

**본 개발 기간에는 앱에서 폴링으로 처리**하고, `notification` 테이블 추가 여부는 팀 결정으로
넘긴다. 폴링 주기는 홈·영상 목록·지원 현황 진입 시 재조회로 시작한다.

---

## 8. 구현 순서

로드맵(7장 4절)의 스프린트 구획에 맞춘다.

| 단계 | 범위 | 대응 스프린트 |
|---|---|---|
| 0 | 프로젝트 셋업, 디렉터리 구조, 테마, 라우터 뼈대, `MockDb` 시드 | Sprint 1 (~08.31) |
| 1 | 로그인·회원가입·온보딩·홈·프로필 | Sprint 2 |
| 2 | 영상 업로드·목록·분석 상태·리포트 | Sprint 2 |
| 3 | 선수 카드·호칭·공개 카드 딥링크 | Sprint 2~3 |
| 4 | 경기 탐색·상세·지원·내 지원 현황 | Sprint 3 |
| 5 | [팀] 경기 등록·포지션·지원자 관리·추천 후보 | Sprint 3 |
| 6 | 평가·신고·불참, 크레딧·코치 | Sprint 4 |
| 7 | API 리포지토리 교체, 통합 | Sprint 4~5 |

Sprint 2 데모에 필요한 최소 코어는 10개 화면이다 — `/login`, `/onboarding/sport`, `/home`,
`/profile`, `/videos`, `/videos/upload`, `/analysis/:jobId/report`, `/card`(호칭 탭 포함),
`/matches`, `/credits`.

---

## 9. 테스트 전략

### 9.1 리포지토리 계약 테스트

**Mock과 실제 API 구현체가 동일한 계약을 지키는지 한 벌의 테스트로 검증한다.** 인터페이스에
대해 테스트를 한 번 쓰고, 지금은 Mock에 물려 돌리고, API가 나오면 같은 테스트를 API 구현체에
물린다. 이것이 "provider 한 줄 교체"를 실제로 보장하는 장치다.

```dart
// test/contract/match_repository_contract.dart
void runMatchRepositoryContract(String name, MatchRepository Function() build) {
  group('$name — MatchRepository 계약', () {
    test('지원 직후에는 확정 상태가 아니다', () async { ... });
    test('팀 수락 후 양측이 차면 확정이다', () async { ... });
    test('같은 경기에 두 번 지원하면 실패한다', () async { ... });  // 유일 제약
  });
}
```

### 9.2 불변식 테스트

1절의 원칙 가운데 타입으로 못 막는 것을 테스트로 막는다.

- `PlayerCard`를 그리는 위젯 트리에 지표 수치 문자열이 나타나지 않는다.
- 호칭 목록 위젯에 미획득 항목이 렌더되지 않는다.
- 추천 후보 위젯은 `reason`을 반드시 렌더한다.
- 평가 화면에 `TextField`가 존재하지 않는다.

### 9.3 화면 테스트

핵심 플로우 위주로 위젯 테스트를 둔다 — 업로드 → 상태 확인 → 리포트, 경기 탐색 → 지원 →
확정 표시, 평가 작성 → 재평가 차단.

---

## 10. 미결 항목

| 항목 | 내용 | 처리 |
|---|---|---|
| 알림 | `notification` 테이블 부재. 분석 완료·수락 통지 경로 없음 | 폴링으로 시작, 팀 결정 필요 (7절) |
| 지표 항목 | `metric_definition` 목록 미확정 (D.8) | 하드코딩 금지, 조회 렌더 |
| 평가 선택지 | `review_option` 구성 미확정 (D.8) | 하드코딩 금지, 조회 렌더 |
| 평가자 신뢰도 노출 | 집계 뷰로만 존재. 화면 노출 시 사용자 간 비교 점수가 생겨 순위표 금지 원칙과 충돌 | **노출하지 않기를 권고**, 팀 확인 필요 |
| **선호 종목 저장 위치** | ERD의 `user` 테이블에 종목 컬럼이 없다. 온보딩에서 고른 종목을 저장할 서버 자리가 스키마에 없음 | 단계 1은 앱 메모리에만 유지. 기기 저장소로 둘지 `user`에 컬럼을 추가할지 팀 결정 필요 |
| 인증 방식 | 이메일/소셜/OTP 미정. `user`에 `email`만 있음 | Mock은 이메일 기준, 확정 시 교체 |
| 영상 업로드 경로 | `video.s3_key`가 S3를 전제. 앱 직접 업로드인지 서버 경유인지 미정 | 리포지토리 뒤로 숨겨 어느 쪽이든 수용 |

---

## 11. 팀 전달 사항 (머지 시점)

`app/` 밖은 건드리지 않았다. 아래는 다른 사람이 처리해야 할 항목이다.

1. `_config.yml`의 `exclude:`에 `app/` 추가 — 없으면 Flutter 소스가 사이트에 함께 복사된다.
   (배포 워크플로가 `--baseurl`을 덮어쓰므로 빌드가 깨지지는 않는다.)
2. `_config.yml`의 `baseurl`·`url`이 이전 저장소(`supersub.parkminho.cloud`) 값으로 남아 있다.
   배포는 워크플로가 덮어써서 정상이나 `url:`은 틀린 절대 주소를 만든다.
3. 표지(`jekyll/pages/index.markdown`)의 깃허브·데모 주소가 `paiksunggum` 계정으로 되어 있어
   실제 저장소(`pmhllll12/super-sub.cloud`)와 불일치한다.
4. 7장 로드맵의 Flutter 담당자 표기가 역할 재조정 이전 값이다.
5. 이 문서의 5절(화면 목록)과 1절(원칙)은 6장 5) 화면 설계와 7장 2) 주요 기능 구현 방안에
   그대로 옮겨 쓸 수 있다.
