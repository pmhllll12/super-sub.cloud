import '../match_prefs.dart';
import '../match_prefs_server.dart';
import 'match_repository.dart';
import 'models/match_application.dart';
import 'models/match_candidate.dart';
import 'models/open_match.dart';
import 'models/review_option.dart';

/// 가짜 팀의 id. 🔴 **이 값은 서버에 없다** — 이것이 붙은 것은 무엇이든
/// 서버로 내보내지 않는다.
const String kDemoTeamId = 'demo-team-mock';

/// 실서버 위에 **가짜 상대 한 팀만** 얹는다.
///
/// 🔴 **왜 있나** (2026-09-25 사용자 요청: 「우리 앱에 그냥 mock 팀 하나만
/// 넣으면 안됨? mock 모드 말고」). 실서버에서는 상대 팀장이 **실제로** 수락을
/// 눌러야 경기가 잡힌다 — 혼자 시험할 때 그 자리에서 막힌다. 목업 모드로
/// 통째로 갈아타면 로그인·카드까지 전부 가짜가 되어 그것대로 못 본다.
///
/// 🔴 **가짜는 서버를 건드리지 않는다.** 가짜 팀에 건 신청·취소·평가는 전부
/// 이 안에서 끝난다 — 나가면 서버에 없는 id 라 404 이고, 무엇보다 **진짜
/// 데이터에 가짜가 섞인다**(평가는 등급 집계로까지 흘러간다).
///
/// 🔴 **걷어낼 때는 provider 한 줄이다** — `match_providers.dart` 에서 이
/// 감싸기를 빼면 된다. 실제 배포에서는 걷는다.
class DemoMatchRepository implements MatchRepository {
  DemoMatchRepository(
    this._inner, {
    this.acceptAfter = const Duration(seconds: 4),
  });

  final MatchRepository _inner;

  /// 가짜 상대가 스스로 수락하기까지. ⚠️ 자리 초대(1.5초)보다 길게 둔다 —
  /// 「신청했다」를 읽을 틈이 있어야 한다.
  final Duration acceptAfter;

  /// 가짜 신청들 — **이 화면이 살아 있는 동안만** 남는다.
  final List<TeamMatchRequest> _demoRequests = [];

  /// 목록에 섞어 넣는 가짜 상대.
  ///
  /// 🔴 **이름에 `(mock)` 을 박는다.** 진짜 팀과 나란히 서므로 한눈에 갈려야
  /// 한다 — 실제로 어느 것이 가짜인지 몰라 한참 헤맨 적이 있다.
  static const _demoTeam = MatchCandidate(
    teamId: kDemoTeamId,
    name: '시험용 상대 (mock)',
    regionLabel: '서울 강남구',
    formation: '5:5',
    reasons: [
      MatchReason(kind: 'demo', detail: '바로 수락합니다 — 흐름 시험용'),
    ],
  );

  bool _isDemo(String id) => id == kDemoTeamId;

  @override
  Future<List<MatchCandidate>> candidates(String teamId) async {
    /* 🔴 **서버가 죽어도 가짜는 남긴다** (2026-09-25, 실서버가 522 를 냈다).
       가짜는 시험하라고 넣은 것인데 진짜와 함께 죽으면 정작 서버가 불안정할
       때 못 쓴다 — 그때가 가장 필요한 때다. */
    List<MatchCandidate> real;
    try {
      real = await _inner.candidates(teamId);
    } catch (_) {
      real = const [];
    }
    /* 🔴 **진짜 목록을 가리지 않는다** — 섞는 것이지 대신하는 것이 아니다.
       맨 앞에 두는 이유는 시험할 때 스크롤하지 않고 닿게 하려는 것이다. */
    return [_demoTeam, ...real];
  }

  @override
  Future<TeamMatchRequest> requestMatch(
    String teamId, {
    required String targetTeamId,
    required String playedAt,
    required String place,
  }) async {
    if (!_isDemo(targetTeamId)) {
      return _inner.requestMatch(
        teamId,
        targetTeamId: targetTeamId,
        playedAt: playedAt,
        place: place,
      );
    }

    final made = TeamMatchRequest(
      id: 'demo-req-${_demoRequests.length + 1}',
      requesterTeamId: teamId,
      targetTeamId: targetTeamId,
      status: 'pending',
      playedAt: playedAt,
      place: place,
      targetTeamName: _demoTeam.name,
      // 가짜 팀에는 진짜 판이 없다 — 대기 화면이 자리표시자로 그린다.
      targetSquadSlug: null,
    );
    _demoRequests.add(made);

    /* 🔴 **가짜만 스스로 수락한다.** 실서버 팀은 상대 팀장이 눌러야 하고,
       그것을 여기서 흉내 내면 **잡히지도 않은 경기가 잡힌 것처럼** 보인다. */
    Future<void>.delayed(acceptAfter, () {
      final i = _demoRequests.indexWhere((r) => r.id == made.id);
      if (i < 0 || !_demoRequests[i].isPending) return;
      _demoRequests[i] = TeamMatchRequest(
        id: made.id,
        requesterTeamId: made.requesterTeamId,
        targetTeamId: made.targetTeamId,
        status: 'accepted',
        playedAt: made.playedAt,
        place: made.place,
        matchId: 'demo-match-${made.id}',
        targetTeamName: made.targetTeamName,
      );
    });

    return made;
  }

  @override
  Future<List<TeamMatchRequest>> requests(String teamId) async => [
        ..._demoRequests,
        ...await _inner.requests(teamId),
      ];

  @override
  /* 🔴 **지원은 가짜를 안 끼운다** — 가짜 팀은 「맞는 상대」 쪽에만 있고,
     「사람을 찾는 경기」 목록은 서버 것 그대로다. 그대로 흘려보낸다. */
  @override
  Future<MatchApplication> apply(String matchId) => _inner.apply(matchId);

  @override
  Future<void> withdraw(String matchId, {required String applicationId}) =>
      _inner.withdraw(matchId, applicationId: applicationId);

  @override
  Future<void> cancelRequest(String teamId, {required String requestId}) async {
    if (requestId.startsWith('demo-req-')) {
      _demoRequests.removeWhere((r) => r.id == requestId);
      return;
    }
    return _inner.cancelRequest(teamId, requestId: requestId);
  }

  @override
  Future<void> submitReview(
    String matchId, {
    required String revieweeId,
    required List<String> optionCodes,
  }) async {
    /* 🔴 **가짜 경기의 평가는 안 내보낸다.** 서버에 없는 경기 id 라 404 이고,
       설령 통과해도 **진짜 등급 집계에 가짜가 섞인다**(평가는 신뢰 축으로
       흘러가 카드 등급까지 바꾼다). */
    if (matchId.startsWith('demo-match-')) return;
    return _inner.submitReview(
      matchId,
      revieweeId: revieweeId,
      optionCodes: optionCodes,
    );
  }

  /* 🔴 **받은 쪽은 흘려보낸다** — 가짜는 **내가 거는 쪽**만 가로챈다.
     나에게 온 신청은 진짜 서버 것이어야 웹과 이어진다. */
  @override
  Future<TeamMatchRequest> acceptRequest(
    String teamId, {
    required String requestId,
  }) =>
      _inner.acceptRequest(teamId, requestId: requestId);

  @override
  Future<void> rejectRequest(String teamId, {required String requestId}) =>
      _inner.rejectRequest(teamId, requestId: requestId);

  // ── 아래는 그대로 흘려보낸다 ──────────────────────────────────────────

  @override
  Future<List<RefItem>> regions() => _inner.regions();

  @override
  Future<List<RefItem>> positions(String sportCode) =>
      _inner.positions(sportCode);

  @override
  Future<MatchPrefs?> teamPrefs(String teamId) => _inner.teamPrefs(teamId);

  /* 🔴 **내 조건과 경기 탐색은 그대로 흘려보낸다** — 가짜를 섞지 않는다.
     「사람을 찾는 팀」은 **진짜 서버 것**이어야 웹과 이어진다. */
  @override
  Future<MatchPrefs?> myPrefs() => _inner.myPrefs();

  @override
  Future<void> saveMyPrefs(MatchPrefs prefs) => _inner.saveMyPrefs(prefs);

  @override
  Future<List<OpenMatch>> openMatches({String? sportCode, String? region}) =>
      _inner.openMatches(sportCode: sportCode, region: region);

  @override
  Future<void> saveTeamPrefs(String teamId, MatchPrefs prefs) =>
      _inner.saveTeamPrefs(teamId, prefs);

  @override
  Future<List<ReviewOption>> reviewOptions() => _inner.reviewOptions();
}
