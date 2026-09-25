import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/match_providers.dart';
import 'package:super_sub/features/team/data/match_repository.dart';
import 'package:super_sub/features/team/data/models/match_application.dart';
import 'package:super_sub/features/team/data/models/match_candidate.dart';
import 'package:super_sub/features/team/data/models/open_match.dart';
import 'package:super_sub/features/team/data/models/review_option.dart';
import 'package:super_sub/features/team/match_prefs.dart';
import 'package:super_sub/features/team/match_prefs_server.dart';
import 'package:super_sub/features/team/presentation/sheets/team_match_sheet.dart';

/// 무엇을 저장했고 무엇을 신청했는지 받아 적는 가짜 저장소.
class _FakeMatch implements MatchRepository {
  _FakeMatch({this.prefs});

  MatchPrefs? prefs;
  MatchPrefs? saved;
  final requested = <({String target, String playedAt, String place})>[];

  @override
  Future<List<RefItem>> regions() async => const [
        RefItem(id: 'r-1', label: '서울 강남구'),
        RefItem(id: 'r-2', label: '서울 영등포구'),
      ];

  @override
  Future<List<RefItem>> positions(String sportCode) async =>
      const [RefItem(id: 'p-mf', label: 'MF')];

  @override
  Future<MatchPrefs?> teamPrefs(String teamId) async => prefs;

  // 내 조건·경기 탐색 — 이 시험이 안 쓰는 것들.
  @override
  Future<MatchPrefs?> myPrefs() async => null;
  @override
  Future<void> saveMyPrefs(MatchPrefs p) async {}
  @override
  Future<List<OpenMatch>> openMatches({String? sportCode, String? region}) async =>
      const [];


  @override
  Future<void> saveTeamPrefs(String teamId, MatchPrefs p) async {
    saved = p;
    prefs = p;
  }

  @override
  Future<List<MatchCandidate>> candidates(String teamId) async => const [
        MatchCandidate(
          teamId: 't-gangnam',
          name: 'FC 강남',
          regionLabel: '서울 강남구',
          formation: '5:5',
          reasons: [MatchReason(kind: 'time', detail: '토요일 10:00~12:00 겹침')],
        ),
        MatchCandidate(
          teamId: 't-cloud',
          name: '강남 클라우드FC',
          regionLabel: '서울 강남구',
          formation: '5:5',
        ),
      ];

  @override
  Future<TeamMatchRequest> requestMatch(
    String teamId, {
    required String targetTeamId,
    required String playedAt,
    required String place,
  }) async {
    requested.add((target: targetTeamId, playedAt: playedAt, place: place));
    live = [
      ...live,
      TeamMatchRequest(
        id: 'tmr-${live.length + 1}',
        requesterTeamId: teamId,
        targetTeamId: targetTeamId,
        status: 'pending',
        playedAt: playedAt,
        place: place,
      ),
    ];
    return TeamMatchRequest(
      id: 'tmr-1',
      requesterTeamId: teamId,
      targetTeamId: targetTeamId,
      status: 'pending',
      playedAt: playedAt,
      place: place,
    );
  }

  /// 이미 걸어 둔 신청 — 화면이 그 팀을 잠그는지 본다.
  List<TeamMatchRequest> live = const [];

  @override
  Future<List<TeamMatchRequest>> requests(String teamId) async => live;

  // 받은 쪽 — 이 시험이 안 쓰는 것들.
  @override
  Future<TeamMatchRequest> acceptRequest(String teamId,
          {required String requestId}) =>
      throw UnimplementedError();
  @override
  Future<void> rejectRequest(String teamId,
      {required String requestId}) async {}


  final cancelled = <String>[];

  @override
  Future<void> cancelRequest(String teamId, {required String requestId}) async {
    cancelled.add(requestId);
    live = [
      for (final r in live)
        if (r.id != requestId) r,
    ];
  }

  // 이 시트가 안 쓰는 것들.
  @override
  Future<MatchApplication> apply(String m) => throw UnimplementedError();
  @override
  Future<void> withdraw(String m, {required String applicationId}) async {}

  @override
  Future<List<ReviewOption>> reviewOptions() async => const [];
  @override
  Future<void> submitReview(
    String matchId, {
    required String revieweeId,
    required List<String> optionCodes,
  }) async {}
}

/// 시트가 돌려준 신청 — 부르는 쪽이 그것으로 경기 화면을 연다.
TeamMatchRequest? lastPick;

Future<void> _open(WidgetTester tester, _FakeMatch repo) async {
  lastPick = null;
  tester.view.physicalSize = const Size(1080, 2340);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [matchRepositoryProvider.overrideWithValue(repo)],
      child: MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => ElevatedButton(
              onPressed: () async =>
                  lastPick = await showTeamMatchSheet(context, teamId: 't-thunder'),
              child: const Text('열기'),
            ),
          ),
        ),
      ),
    ),
  );

  await tester.tap(find.text('열기'));
  for (var i = 0; i < 4; i++) {
    await tester.pump(const Duration(milliseconds: 400));
  }
}

const _ready = MatchPrefs(
  regions: ['서울 강남구'],
  times: [TimeSlot(day: 6, from: '10:00', to: '12:00')],
);

void main() {
  _liveRequestTests();

  /// 🔴 **조건을 한 번도 안 정했으면 먼저 묻는다** — 조건 없이 찾으면
  /// 「비슷하다」를 판단할 근거가 없다.
  testWidgets('조건이 없으면 조건부터 묻는다', (tester) async {
    await _open(tester, _FakeMatch());

    expect(find.text('어떤 경기를 찾으세요?'), findsOneWidget);
    expect(find.textContaining('어느 동네'), findsOneWidget);
    expect(find.text('팀 찾기'), findsOneWidget);
  });

  /// 🔴 지역·시간 **둘 다** 있어야 찾을 수 있다.
  testWidgets('지역과 시간이 없으면 팀 찾기를 못 누른다', (tester) async {
    final repo = _FakeMatch();
    await _open(tester, repo);

    await tester.tap(find.text('팀 찾기'));
    await tester.pump(const Duration(milliseconds: 400));

    expect(repo.saved, isNull, reason: '빈 조건은 저장되지 않는다');
    expect(find.text('어떤 경기를 찾으세요?'), findsOneWidget);
  });

  testWidgets('조건이 있으면 비슷한 팀을 보여 준다', (tester) async {
    await _open(tester, _FakeMatch(prefs: _ready));

    expect(find.text('비슷한 팀'), findsOneWidget);
    expect(find.text('FC 강남'), findsOneWidget);
  });

  /// 🔴 **근거는 서버가 준 문장 그대로** 적는다 — 화면이 겹침을 다시
  /// 계산하지 않는다(계약의 「하지 말 것」).
  testWidgets('근거를 그대로 적는다', (tester) async {
    await _open(tester, _FakeMatch(prefs: _ready));

    expect(find.text('토요일 10:00~12:00 겹침'), findsOneWidget);
  });

  /// ⚠️ 근거가 빈 팀도 목록에 남는다 — 하드 필터는 통과했다.
  testWidgets('근거가 없는 팀도 목록에 남는다', (tester) async {
    await _open(tester, _FakeMatch(prefs: _ready));

    expect(find.text('강남 클라우드FC'), findsOneWidget);
  });

  /// 🔴 **신청에는 시각과 구장이 필수다**(계약 3-15절). 시각은 **우리가 올린
  /// 조건**에서 만들고 지어내지 않는다.
  testWidgets('경기 신청을 누르면 우리 조건에서 만든 시각이 뜬다', (tester) async {
    await _open(tester, _FakeMatch(prefs: _ready));

    await tester.tap(find.text('경기 신청').first);
    await tester.pump(const Duration(milliseconds: 400));

    // 조건이 토요일 10:00~12:00 하나뿐이라 고를 시각도 그것 하나다.
    expect(find.textContaining('토 '), findsWidgets);
    expect(find.text('이 시각으로 신청'), findsOneWidget);
  });

  testWidgets('시각을 고르고 신청하면 저장소로 간다', (tester) async {
    final repo = _FakeMatch(prefs: _ready);
    await _open(tester, repo);

    await tester.tap(find.text('경기 신청').first);
    await tester.pump(const Duration(milliseconds: 400));
    await tester.tap(find.text('이 시각으로 신청'));
    await tester.pump(const Duration(milliseconds: 400));

    expect(repo.requested, hasLength(1));
    expect(repo.requested.single.target, 't-gangnam');
    expect(repo.requested.single.place, isNotEmpty, reason: '구장이 비면 422 다');
    expect(repo.requested.single.playedAt, contains('T10:00:00'));
  });
}

/// 🔴 **한 번 걸었으면 그 팀은 잠긴다** (2026-09-25, 사용자: 「경기 신청 한 번
/// 했으면 신청 수락 대기중 이라고 떠야 하는거 아님? 그리고 터치 안되게」).
/// 계약도 같은 상대에 겹쳐 거는 것을 409 로 막는다.
void _liveRequestTests() {
  testWidgets('이미 건 팀은 수락 대기중으로 잠긴다', (tester) async {
    final repo = _FakeMatch(prefs: _ready)
      ..live = [
        const TeamMatchRequest(
          id: 'tmr-1',
          requesterTeamId: 't-thunder',
          targetTeamId: 't-gangnam',
          status: 'pending',
          playedAt: '2026-10-03T11:00:00+09:00',
          place: '강남 풋살장',
        ),
      ];
    await _open(tester, repo);

    expect(find.text('수락 대기중'), findsOneWidget);

    // 눌러도 안 펼쳐진다.
    await tester.tap(find.text('수락 대기중'));
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.text('이 시각으로 신청'), findsNothing);
  });

  /// 안 건 팀은 그대로 걸 수 있다.
  testWidgets('안 건 팀은 그대로 경기 신청이다', (tester) async {
    final repo = _FakeMatch(prefs: _ready)
      ..live = [
        const TeamMatchRequest(
          id: 'tmr-1',
          requesterTeamId: 't-thunder',
          targetTeamId: 't-gangnam',
          status: 'pending',
          playedAt: '2026-10-03T11:00:00+09:00',
          place: '강남 풋살장',
        ),
      ];
    await _open(tester, repo);

    expect(find.text('경기 신청'), findsOneWidget);
  });

  /// 🔴 **건 쪽이 무를 수 있어야 한다** (2026-09-25 사용자: 「신청 취소
  /// 버튼도 보여야 하는거 아님? 그 수락대기중 아래에」). 상대가 답을 안
  /// 하면 그 팀이 **영영 잠긴 채**로 남는다.
  testWidgets('수락 대기중 아래에 신청 취소가 있다', (tester) async {
    final repo = _FakeMatch(prefs: _ready)
      ..live = [
        const TeamMatchRequest(
          id: 'tmr-1',
          requesterTeamId: 't-thunder',
          targetTeamId: 't-gangnam',
          status: 'pending',
          playedAt: '2026-10-03T11:00:00+09:00',
          place: '강남 풋살장',
        ),
      ];
    await _open(tester, repo);

    final waiting = tester.getRect(find.text('수락 대기중'));
    final cancel = tester.getRect(find.text('신청 취소'));
    expect(cancel.top, greaterThan(waiting.top), reason: '대기중 아래다');
  });

  /// 🔴 무르면 **그 팀 판에 「경기 신청」만** 남는다.
  testWidgets('신청 취소를 누르면 다시 경기 신청이 된다', (tester) async {
    final repo = _FakeMatch(prefs: _ready)
      ..live = [
        const TeamMatchRequest(
          id: 'tmr-1',
          requesterTeamId: 't-thunder',
          targetTeamId: 't-gangnam',
          status: 'pending',
          playedAt: '2026-10-03T11:00:00+09:00',
          place: '강남 풋살장',
        ),
      ];
    await _open(tester, repo);

    await tester.tap(find.text('신청 취소'));
    for (var i = 0; i < 4; i++) {
      await tester.pump(const Duration(milliseconds: 400));
    }

    expect(repo.cancelled, ['tmr-1']);
    expect(find.text('수락 대기중'), findsNothing);
    expect(find.text('신청 취소'), findsNothing);
    expect(find.text('경기 신청'), findsNWidgets(2));
  });

  /// 🔴 **나에게 온 신청은 내가 건 것이 아니다** (2026-09-25, 사용자: 「경기
  /// 취소 안되는 팀들도 있어」). 계약의 `GET …/match-requests` 는 **보낸 것 +
  /// 받은 것**을 함께 준다 — 안 가르면 받은 신청이 엉뚱한 팀을 잠그고,
  /// 그 팀은 취소도 안 된다(취소는 **신청 팀 주장만**).
  testWidgets('받은 신청은 남의 팀을 잠그지 않는다', (tester) async {
    final repo = _FakeMatch(prefs: _ready)
      ..live = [
        const TeamMatchRequest(
          id: 'tmr-in',
          // 상대가 **우리에게** 건 것 — 우리가 대상이다.
          requesterTeamId: 't-gangnam',
          targetTeamId: 't-thunder',
          status: 'pending',
          playedAt: '2026-10-03T11:00:00+09:00',
          place: '강남 풋살장',
        ),
      ];
    await _open(tester, repo);

    expect(find.text('수락 대기중'), findsNothing);
    expect(find.text('경기 신청'), findsNWidgets(2));
  });

  /// 🔴 **이미 잡힌 경기는 「취소」가 아니라 다른 길이다** — 계약의
  /// `DELETE …/match-requests/{id}` 는 `pending` 일 때만 되고, 잡힌 경기는
  /// `DELETE /matches/{id}` 다. 여기서는 **누를 수 없게** 두고 그렇게 알린다.
  testWidgets('이미 잡힌 경기는 신청 취소가 안 뜬다', (tester) async {
    final repo = _FakeMatch(prefs: _ready)
      ..live = [
        const TeamMatchRequest(
          id: 'tmr-1',
          requesterTeamId: 't-thunder',
          targetTeamId: 't-gangnam',
          status: 'accepted',
          playedAt: '2026-10-03T11:00:00+09:00',
          place: '강남 풋살장',
          matchId: 'm-1',
        ),
      ];
    await _open(tester, repo);

    expect(find.text('경기가 잡혔습니다'), findsOneWidget);
    expect(find.text('신청 취소'), findsNothing);
  });

  /// 🔴 **잡힌 경기는 거기서 끝이 아니다** (2026-09-25, 사용자: 「경기가
  /// 잡혔다고 뜨는데, 뭐 그 다음 아무것도 없어?」). 누르면 그 경기 화면으로
  /// 이어져야 한다 — 시트는 **그 신청을 돌려주고** 부르는 쪽이 연다.
  testWidgets('잡힌 경기를 누르면 그 신청을 돌려준다', (tester) async {
    final repo = _FakeMatch(prefs: _ready)
      ..live = [
        const TeamMatchRequest(
          id: 'tmr-1',
          requesterTeamId: 't-thunder',
          targetTeamId: 't-gangnam',
          status: 'accepted',
          playedAt: '2026-10-03T11:00:00+09:00',
          place: '강남 풋살장',
          matchId: 'm-1',
        ),
      ];
    await _open(tester, repo);

    await tester.tap(find.text('경기가 잡혔습니다'));
    await tester.pump(const Duration(milliseconds: 400));

    expect(lastPick?.id, 'tmr-1');
  });

  /// 🔴 **거절·취소된 것은 안 센다** — 안 그러면 한 번 붙은 팀과 다시는 못 붙는다.
  testWidgets('거절된 신청은 잠그지 않는다', (tester) async {
    final repo = _FakeMatch(prefs: _ready)
      ..live = [
        const TeamMatchRequest(
          id: 'tmr-1',
          requesterTeamId: 't-thunder',
          targetTeamId: 't-gangnam',
          status: 'rejected',
          playedAt: '2026-10-03T11:00:00+09:00',
          place: '강남 풋살장',
        ),
      ];
    await _open(tester, repo);

    expect(find.text('수락 대기중'), findsNothing);
    expect(find.text('경기 신청'), findsNWidgets(2));
  });
}
