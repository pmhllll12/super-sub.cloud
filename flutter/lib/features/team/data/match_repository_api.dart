import '../../../core/network/api_client.dart';
import '../match_prefs.dart';
import '../match_prefs_server.dart';
import 'match_repository.dart';
import 'models/match_candidate.dart';
import 'models/open_match.dart';
import 'models/review_option.dart';

/// `fastapi/` 백엔드에 붙는 실제 구현.
/// 계약은 `api-contract.md` 3-13절(조건) · 3-15절(팀 대 팀 신청).
class ApiMatchRepository implements MatchRepository {
  ApiMatchRepository(this._api);

  final ApiClient _api;

  @override
  Future<List<RefItem>> regions() async => [
        for (final r in await _api.getList('/regions'))
          RefItem(id: r['id'] as String, label: r['label'] as String),
      ];

  @override
  Future<List<RefItem>> positions(String sportCode) async {
    final q = Uri(queryParameters: {'sport_code': sportCode}).query;
    return [
      for (final p in await _api.getList('/positions?$q'))
        /* 🔴 `label` 이 아니라 **`code`** 를 담는다 — 화면이 다루는 것은
           약칭(`MF`)이고, 계약으로 나갈 때 id 로 바뀐다. */
        RefItem(id: p['id'] as String, label: p['code'] as String),
    ];
  }

  @override
  Future<MatchPrefs?> teamPrefs(String teamId) async {
    final refs = await regions();
    try {
      final body = await _api
          .get('/teams/${Uri.encodeComponent(teamId)}/match-preferences');
      final server = ServerPrefs.fromJson(body);
      /* 🔴 **한 번도 안 정한 것과 빈 조건을 가른다.** 계약은 404 를 안 주고
         빈 목록을 주므로, 둘 다 비어 있으면 「아직 안 정했다」로 읽는다 —
         그래야 화면이 조건 폼을 먼저 띄운다. */
      if (server.regionIds.isEmpty && server.slots.isEmpty) return null;
      return toScreenPrefs(server, refs);
    } on ApiException catch (e) {
      if (e.status == 404) return null;
      rethrow;
    }
  }

  @override
  Future<void> saveTeamPrefs(String teamId, MatchPrefs prefs) async {
    final refs = await regions();
    await _api.put(
      '/teams/${Uri.encodeComponent(teamId)}/match-preferences',
      toServerPrefs(prefs, refs).toJson(),
    );
  }

  @override
  Future<MatchPrefs?> myPrefs() async {
    final refs = await regions();
    final codes = await positions('football');
    try {
      final body = await _api.get('/me/match-preferences');
      final server = ServerPrefs.fromJson(body);
      /* 🔴 **한 번도 안 정한 것과 빈 조건을 가른다** — 팀 조건과 같은 판단
         이다(계약이 404 를 안 주고 빈 목록을 준다). */
      if (server.regionIds.isEmpty &&
          server.slots.isEmpty &&
          server.positionIds.isEmpty) {
        return null;
      }
      return toScreenPrefs(server, refs, positions: codes);
    } on ApiException catch (e) {
      if (e.status == 404) return null;
      rethrow;
    }
  }

  @override
  Future<void> saveMyPrefs(MatchPrefs prefs) async {
    final refs = await regions();
    final codes = await positions('football');
    await _api.put(
      '/me/match-preferences',
      toServerMemberPrefs(prefs, refs, codes).toJson(withPositions: true),
    );
  }

  @override
  Future<List<OpenMatch>> openMatches({
    String? sportCode,
    String? region,
  }) async {
    final q = Uri(queryParameters: {
      'size': '20',
      'sport_code': ?sportCode,
      'region': ?region,
    }).query;
    /* 🔴 **`items` 로 한 겹 감싸여 온다**(페이지 형식). 배열로 읽으면
       `type 'Map' is not a subtype of List` 로 터진다. */
    final body = await _api.get('/matches?$q');
    final items = (body['items'] as List?) ?? const [];
    return items
        .cast<Map<String, dynamic>>()
        .map(OpenMatch.fromJson)
        .toList();
  }

  @override
  Future<List<MatchCandidate>> candidates(String teamId) async =>
      (await _api.getList(
        '/teams/${Uri.encodeComponent(teamId)}/match-candidates',
      ))
          // 🔴 순서를 건드리지 않는다 — 서버가 이미 정렬했다.
          .map(MatchCandidate.fromJson)
          .toList();

  @override
  Future<TeamMatchRequest> requestMatch(
    String teamId, {
    required String targetTeamId,
    required String playedAt,
    required String place,
  }) async =>
      TeamMatchRequest.fromJson(
        await _api.post('/teams/${Uri.encodeComponent(teamId)}/match-requests', {
          'target_team_id': targetTeamId,
          'played_at': playedAt,
          'place': place,
        }),
      );

  @override
  Future<void> cancelRequest(String teamId, {required String requestId}) =>
      /* 🔴 **본문을 돌려주지만 안 읽는다** — 계약이 204 대신 취소된 신청을
         그대로 준다. 화면은 목록을 다시 읽으므로 그 값이 필요 없다. */
      _api.delete(
        '/teams/${Uri.encodeComponent(teamId)}/match-requests/'
        '${Uri.encodeComponent(requestId)}',
      );

  @override
  Future<TeamMatchRequest> acceptRequest(
    String teamId, {
    required String requestId,
  }) async =>
      TeamMatchRequest.fromJson(
        await _api.post(
          '/teams/${Uri.encodeComponent(teamId)}/match-requests/'
          '${Uri.encodeComponent(requestId)}/accept',
          null,
        ),
      );

  @override
  Future<void> rejectRequest(String teamId, {required String requestId}) =>
      _api.post(
        '/teams/${Uri.encodeComponent(teamId)}/match-requests/'
        '${Uri.encodeComponent(requestId)}/reject',
        null,
      );

  @override
  Future<List<ReviewOption>> reviewOptions() async =>
      // 🔴 순서를 건드리지 않는다 — 배열 순서가 곧 노출 순서다(계약).
      (await _api.getList('/review-options'))
          .map(ReviewOption.fromJson)
          .toList();

  @override
  Future<void> submitReview(
    String matchId, {
    required String revieweeId,
    required List<String> optionCodes,
  }) =>
      _api.post('/matches/${Uri.encodeComponent(matchId)}/reviews', {
        'reviewee_id': revieweeId,
        'option_codes': optionCodes,
      });

  @override
  Future<List<TeamMatchRequest>> requests(String teamId) async =>
      (await _api.getList(
        '/teams/${Uri.encodeComponent(teamId)}/match-requests',
      ))
          .map(TeamMatchRequest.fromJson)
          .toList();
}
