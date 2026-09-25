import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/demo_match_repository.dart';
import 'package:super_sub/features/team/data/match_repository.dart';
import 'package:super_sub/features/team/data/models/match_application.dart';
import 'package:super_sub/features/team/data/models/match_candidate.dart';
import 'package:super_sub/features/team/data/models/open_match.dart';
import 'package:super_sub/features/team/data/models/review_option.dart';
import 'package:super_sub/features/team/match_prefs.dart';
import 'package:super_sub/features/team/match_prefs_server.dart';

/// 진짜 서버를 흉내 내는 속 저장소 — **가짜 팀은 여기 없다.**
class _RealIsh implements MatchRepository {
  final requested = <String>[];
  final cancelled = <String>[];

  /// 서버가 죽은 상태를 흉내 낸다.
  bool down = false;

  @override
  Future<List<MatchCandidate>> candidates(String teamId) async {
    if (down) throw const FormatException('Unexpected character');
    return const [
        MatchCandidate(
          teamId: 't-real',
          name: '한강 나이트라이더스',
          regionLabel: '서울 마포구',
          formation: '5:5',
        ),
    ];
  }

  @override
  Future<TeamMatchRequest> requestMatch(
    String teamId, {
    required String targetTeamId,
    required String playedAt,
    required String place,
  }) async {
    requested.add(targetTeamId);
    return TeamMatchRequest(
      id: 'real-1',
      requesterTeamId: teamId,
      targetTeamId: targetTeamId,
      status: 'pending',
      playedAt: playedAt,
      place: place,
    );
  }

  @override
  Future<void> cancelRequest(String teamId, {required String requestId}) async {
    cancelled.add(requestId);
  }

  @override
  Future<List<TeamMatchRequest>> requests(String teamId) async => const [];

  // 받은 쪽 — 이 시험이 안 쓰는 것들.
  @override
  Future<TeamMatchRequest> acceptRequest(String teamId,
          {required String requestId}) =>
      throw UnimplementedError();
  @override
  Future<void> rejectRequest(String teamId,
      {required String requestId}) async {}

  @override
  Future<List<RefItem>> regions() async => const [];
  @override
  Future<List<RefItem>> positions(String s) async => const [];
  @override
  Future<MatchPrefs?> teamPrefs(String t) async => null;

  // 내 조건·경기 탐색 — 이 시험이 안 쓰는 것들.
  @override
  Future<MatchPrefs?> myPrefs() async => null;
  @override
  Future<void> saveMyPrefs(MatchPrefs p) async {}
  @override
  Future<List<OpenMatch>> openMatches({String? sportCode, String? region}) async =>
      const [];

  @override
  Future<void> saveTeamPrefs(String t, MatchPrefs p) async {}
  @override
  Future<MatchApplication> apply(String m) => throw UnimplementedError();
  @override
  Future<void> withdraw(String m, {required String applicationId}) async {}

  @override
  Future<List<ReviewOption>> reviewOptions() async => const [];
  @override
  Future<void> submitReview(String m,
      {required String revieweeId, required List<String> optionCodes}) async {}
}

void main() {
  late _RealIsh inner;
  late DemoMatchRepository repo;

  setUp(() {
    inner = _RealIsh();
    repo = DemoMatchRepository(inner, acceptAfter: const Duration(seconds: 1));
  });

  /// 🔴 **진짜 목록을 가리지 않는다** — 섞는 것이지 대신하는 것이 아니다.
  test('진짜 팀 옆에 가짜 팀 하나가 선다', () async {
    final list = await repo.candidates('t-thunder');

    expect(list.any((t) => t.teamId == 't-real'), isTrue);
    expect(list.where((t) => t.teamId == kDemoTeamId), hasLength(1));
  });

  /// 🔴 **서버가 죽어도 가짜는 남는다** (2026-09-25, 실제로 522 가 났다).
  test('서버가 죽어도 가짜 팀은 남는다', () async {
    inner.down = true;

    final list = await repo.candidates('t-thunder');

    expect(list, hasLength(1));
    expect(list.single.teamId, kDemoTeamId);
  });

  /// 🔴 **이름에 `(mock)` 이 있다** — 진짜와 섞이므로 한눈에 갈려야 한다.
  test('가짜 팀은 이름으로 드러난다', () async {
    final demo = (await repo.candidates('t-thunder'))
        .firstWhere((t) => t.teamId == kDemoTeamId);

    expect(demo.name, contains('mock'));
  });

  /// 🔴 **가짜 팀에 건 신청은 서버로 안 나간다.** 나가면 서버에 없는 팀 id 라
  /// 404 이고, 무엇보다 **진짜 데이터에 가짜가 섞인다.**
  test('가짜 팀 신청은 서버를 안 부른다', () async {
    await repo.requestMatch('t-thunder',
        targetTeamId: kDemoTeamId,
        playedAt: '2026-10-03T11:00:00+09:00',
        place: '어디 풋살장');

    expect(inner.requested, isEmpty);
  });

  test('진짜 팀 신청은 그대로 서버로 간다', () async {
    await repo.requestMatch('t-thunder',
        targetTeamId: 't-real',
        playedAt: '2026-10-03T11:00:00+09:00',
        place: '어디 풋살장');

    expect(inner.requested, ['t-real']);
  });

  /// 🔴 **가짜 팀만 스스로 수락한다** — 실서버 팀은 상대 팀장이 눌러야 한다.
  test('가짜 팀은 몇 초 뒤 스스로 수락한다', () async {
    final made = await repo.requestMatch('t-thunder',
        targetTeamId: kDemoTeamId,
        playedAt: '2026-10-03T11:00:00+09:00',
        place: '어디 풋살장');

    expect(made.isPending, isTrue);

    await Future<void>.delayed(const Duration(milliseconds: 1400));
    final after =
        (await repo.requests('t-thunder')).firstWhere((r) => r.id == made.id);

    expect(after.isAccepted, isTrue);
    expect(after.matchId, isNotNull);
  });

  /// 🔴 **무르는 것도 서버를 안 부른다.**
  test('가짜 신청은 그 자리에서 무른다', () async {
    final made = await repo.requestMatch('t-thunder',
        targetTeamId: kDemoTeamId,
        playedAt: '2026-10-03T11:00:00+09:00',
        place: '어디 풋살장');

    await repo.cancelRequest('t-thunder', requestId: made.id);

    expect(inner.cancelled, isEmpty);
    expect(await repo.requests('t-thunder'), isEmpty);
  });

  /// 🔴 **평가는 서버로 안 나간다** — 가짜 경기 id 라 404 이고, 진짜 평가
  /// 집계에 가짜가 섞이면 등급이 오염된다.
  test('가짜 경기의 평가는 서버를 안 부른다', () async {
    final made = await repo.requestMatch('t-thunder',
        targetTeamId: kDemoTeamId,
        playedAt: '2026-10-03T11:00:00+09:00',
        place: '어디 풋살장');
    await Future<void>.delayed(const Duration(milliseconds: 1400));
    final matchId =
        (await repo.requests('t-thunder')).firstWhere((r) => r.id == made.id).matchId!;

    await repo.submitReview(matchId,
        revieweeId: 'x', optionCodes: const ['manner_time']);
    // 던지지 않으면 된다 — 속 저장소는 아무것도 안 받는다.
  });
}
