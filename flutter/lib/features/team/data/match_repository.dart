import '../match_prefs.dart';
import '../match_prefs_server.dart';
import 'models/match_candidate.dart';
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
