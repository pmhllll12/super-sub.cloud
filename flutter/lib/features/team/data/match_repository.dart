import '../match_prefs.dart';
import '../match_prefs_server.dart';
import 'models/match_application.dart';
import 'models/match_candidate.dart';
import 'models/open_match.dart';
import 'models/review_option.dart';

/// 팀 매칭 — 경기 조건(계약 3-13절) · 「맞는 상대」 · 팀 대 팀 신청(3-15절).
abstract class MatchRepository {
  /// 지역 목록 — `GET /regions`. 🔴 **id 가 있어야** 조건을 저장할 수 있다.
  Future<List<RefItem>> regions();

  /// 포지션 목록 — `GET /positions?sport_code=`.
  ///
  /// 🔴 **약칭이 아니라 id 를 쓴다** — 약칭은 종목 안에서만 유일해서
  /// (야구 `C`=포수 · 농구 `C`=센터) 그것만으로는 한 줄을 못 가리킨다.
  Future<List<RefItem>> positions(String sportCode);

  /// 팀의 경기 조건. 🔴 **아직 안 정했으면 `null`** 이다 — 빈 조건과 갈라야
  /// 「처음이라 물어야 하는가」가 정해진다.
  Future<MatchPrefs?> teamPrefs(String teamId);

  /// 조건을 저장한다 — **팀장만**, 그리고 **통째로 교체**다(부분 수정이 아니다).
  ///
  /// 🔴 끝이 시작보다 빠르면 서버가 422 로 막는다 — 뒤집힌 시간은 겹침
  /// 계산에서 늘 거짓이라 **조용히 아무것도 안 걸리는** 사고가 난다.
  Future<void> saveTeamPrefs(String teamId, MatchPrefs prefs);

  /// **내** 경기 조건 — `GET /me/match-preferences`. 아직 안 정했으면 `null`.
  ///
  /// 🔴 **팀 조건과 저장소가 다르다**(계약 3-13절) — 같은 사람이 팀장이면서
  /// 팀원일 수 있어 **절대 안 섞는다.**
  Future<MatchPrefs?> myPrefs();

  /// 내 조건을 저장한다 — **통째로 교체**다.
  ///
  /// 🔴 **여기에만 포지션이 있다.** 여기 올린 자리가 곧 남의 AI 추천 판에
  /// 뜨는 첫 하드 필터다 — 안 올리면 남의 추천에 안 뜬다(계약).
  Future<void> saveMyPrefs(MatchPrefs prefs);

  /// **사람을 찾는 경기들** — `GET /matches`.
  ///
  /// 🔴 **다가오는 것만, 이른 것이 앞에** 온다(계약).
  /// 🔴 **없는 종목은 422 다** — 빈 배열로 답하면 오타와 「그 종목 경기가
  /// 없다」가 같아 보여, 사용자가 없는 것을 계속 기다린다.
  /// ⚠️ 지역은 자유 문자열이라 검증할 대상이 없다 — 안 걸리면 빈 목록이다.
  Future<List<OpenMatch>> openMatches({String? sportCode, String? region});

  /// **그 경기에 내가 지원한다** — 계약 3-5절 `POST /matches/{id}/applications`.
  ///
  /// 🔴 **본문을 비워 보낸다** — 그것이 「본인이 지원」이다. `user_id` 를 담으면
  /// **주장이 남을 제안**하는 뜻이 되어, 주장이 아니면 403 이 온다.
  ///
  /// 🔴 돌려주는 것은 「냈다」이지 「잡혔다」가 아니다
  /// ([MatchApplication.confirmed] 머리말).
  ///
  /// | 막히는 자리 | code |
  /// |---|---|
  /// | 경기당 한 건 | `ALREADY_APPLIED` (409) |
  /// | 그 팀 소속이다 | `TEAM_MEMBER_CANNOT_APPLY` (409) |
  /// | 이미 지난 경기 | `PAST_MATCH` (422) |
  Future<MatchApplication> apply(String matchId);

  /// 낸 지원을 무른다 — `DELETE …/applications/{applicationId}`.
  ///
  /// 🔴 **행을 지운다**(계약이 A-1 로 정했다) — 그래서 무른 뒤에는 같은 경기에
  /// 다시 지원할 수 있다.
  Future<void> withdraw(String matchId, {required String applicationId});

  /// 「맞는 상대」 후보 — **서버가 이미 정렬한 순서 그대로**.
  Future<List<MatchCandidate>> candidates(String teamId);

  /// 경기를 건다 — **신청 팀 주장만**. 상대 팀장이 **수락해야** 확정된다.
  ///
  /// 🔴 돌려주는 것은 「걸었다」이지 「잡혔다」가 아니다. 확정은 `matchId` 가
  /// 차는 순간이다.
  Future<TeamMatchRequest> requestMatch(
    String teamId, {
    required String targetTeamId,
    required String playedAt,
    required String place,
  });

  /// 그 팀이 보낸 신청 전부(상태 무관), 최신순 — 답을 기다릴 때 되풀이해 읽는다.
  Future<List<TeamMatchRequest>> requests(String teamId);

  /// 건 신청을 **무른다** — `DELETE /teams/{id}/match-requests/{id}`.
  ///
  /// 🔴 **신청 팀 주장만, `pending` 일 때만**(아니면 409). 이게 없으면 상대가
  /// 답을 안 할 때 그 팀이 **영영 잠긴 채**로 남는다 — 실기기에서 실제로
  /// 셋이 그렇게 묶였다(2026-09-25).
  Future<void> cancelRequest(String teamId, {required String requestId});

  /// **받은** 신청을 수락 — `POST …/match-requests/{id}/accept`.
  ///
  /// 🔴 **대상 팀 주장만.** 수락되는 순간 **두 팀 각각의 다른 `pending` 이
  /// 전부 `cancelled` 로 정리된다**(계약 3-15절 「동시 확정 방지」) — 한 팀이
  /// 여러 곳에 걸려 있다가 둘 다 수락되는 이중 예약을 막는다.
  ///
  /// 🔴 **웹과 앱을 잇는 자리다** — 앱에서 수락한 것이 웹에 뜨는 길이 이것
  /// 하나뿐이다(2026-09-25 사용자 요청).
  Future<TeamMatchRequest> acceptRequest(
    String teamId, {
    required String requestId,
  });

  /// **받은** 신청을 거절 — `POST …/match-requests/{id}/reject`.
  Future<void> rejectRequest(String teamId, {required String requestId});

  /// 평가 항목 — `GET /review-options`.
  ///
  /// 🔴 **순서를 건드리지 않는다.** 배열 순서가 곧 노출 순서다(계약).
  Future<List<ReviewOption>> reviewOptions();

  /// 평가를 낸다 — `POST /matches/{id}/reviews`.
  ///
  /// 🔴 **점수 필드가 없다**(계약) — 고른 항목만 보낸다.
  /// 🔴 **경기당 1회**다(DB 유일 제약) — 두 번째는 409 `ALREADY_REVIEWED`.
  /// 하나도 안 고르면 422 `NO_OPTION_SELECTED` 다.
  Future<void> submitReview(
    String matchId, {
    required String revieweeId,
    required List<String> optionCodes,
  });
}
