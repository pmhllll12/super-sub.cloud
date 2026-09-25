import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/match_providers.dart';
import 'package:super_sub/features/team/data/match_repository.dart';
import 'package:super_sub/features/team/data/models/match_candidate.dart';
import 'package:super_sub/features/team/data/models/open_match.dart';
import 'package:super_sub/features/team/data/models/review_option.dart';
import 'package:super_sub/features/team/match_prefs.dart';
import 'package:super_sub/features/team/match_prefs_server.dart';
import 'package:super_sub/features/team/presentation/sheets/team_seek_sheet.dart';

class _Fake implements MatchRepository {
  _Fake({this.prefs});

  MatchPrefs? prefs;
  MatchPrefs? saved;
  final asked = <({String? sport, String? region})>[];

  @override
  Future<MatchPrefs?> myPrefs() async => prefs;

  @override
  Future<void> saveMyPrefs(MatchPrefs p) async {
    saved = p;
    prefs = p;
  }

  @override
  Future<List<OpenMatch>> openMatches({String? sportCode, String? region}) async {
    asked.add((sport: sportCode, region: region));
    return [
      OpenMatch(
        id: 'om-1',
        teamId: 't-bears',
        teamName: '베어스',
        region: '서울 송파구',
        sportCode: 'football',
        playedAt: '2026-10-02T19:00:00Z',
        place: '잠실 풋살장',
        needs: const [
          MatchNeed(positionCode: 'GK', positionLabel: '골키퍼', headCount: 1),
        ],
      ),
      // 🔴 찾는 자리가 **빈 것도 정상**이다 — 팀 대 팀으로 잡힌 경기다.
      OpenMatch(
        id: 'om-2',
        teamId: 't-hangang',
        teamName: '한강 나이트',
        region: '서울 강남구',
        sportCode: 'football',
        playedAt: '2026-10-04T19:00:00Z',
        place: '보라매공원',
      ),
    ];
  }

  @override
  Future<List<RefItem>> regions() async => const [
        RefItem(id: 'r-1', label: '서울 강남구'),
      ];
  @override
  Future<List<RefItem>> positions(String s) async =>
      const [RefItem(id: 'p-mf', label: 'MF')];

  // 이 화면이 안 쓰는 것들.
  @override
  Future<MatchPrefs?> teamPrefs(String t) async => null;
  @override
  Future<void> saveTeamPrefs(String t, MatchPrefs p) async {}
  @override
  Future<List<MatchCandidate>> candidates(String t) async => const [];
  @override
  Future<TeamMatchRequest> requestMatch(String teamId,
          {required String targetTeamId,
          required String playedAt,
          required String place}) =>
      throw UnimplementedError();
  @override
  Future<void> cancelRequest(String teamId, {required String requestId}) async {}
  @override
  Future<List<TeamMatchRequest>> requests(String teamId) async => const [];
  @override
  Future<TeamMatchRequest> acceptRequest(String teamId,
          {required String requestId}) =>
      throw UnimplementedError();
  @override
  Future<void> rejectRequest(String teamId, {required String requestId}) async {}
  @override
  Future<List<ReviewOption>> reviewOptions() async => const [];
  @override
  Future<void> submitReview(String m,
      {required String revieweeId, required List<String> optionCodes}) async {}
}

const _ready = MatchPrefs(
  regions: ['서울 강남구'],
  times: [TimeSlot(day: 6, from: '10:00', to: '12:00')],
  positions: ['MF'],
);

Future<void> _open(WidgetTester tester, _Fake repo) async {
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
              onPressed: () => showTeamSeekSheet(context),
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

void main() {
  /// 🔴 **내 조건을 한 번도 안 정했으면 먼저 묻는다** — 웹과 같다. 조건이
  /// 없으면 어느 경기가 나에게 맞는지 판단할 근거가 없다.
  testWidgets('조건이 없으면 조건부터 묻는다', (tester) async {
    await _open(tester, _Fake());

    expect(find.text('어떤 경기를 찾으세요?'), findsOneWidget);
    expect(find.textContaining('내 자리'), findsOneWidget);
  });

  /// 🔴 **내 조건에만 자리가 있다**(계약) — 팀 조건 폼에는 없는 칸이다.
  testWidgets('내 자리를 고르면 조건에 실린다', (tester) async {
    final repo = _Fake();
    await _open(tester, repo);

    await tester.tap(find.byKey(const Key('seek-region-서울 강남구')));
    await tester.pump(const Duration(milliseconds: 400));
    await tester.tap(find.byKey(const Key('seek-add-time')));
    await tester.pump(const Duration(milliseconds: 400));
    await tester.tap(find.byKey(const Key('seek-pos-MF')));
    await tester.pump(const Duration(milliseconds: 400));
    // 칸이 셋이라 폼이 길다 — 끌어 올려 누른다.
    await tester.drag(find.byType(ListView).last, const Offset(0, -400));
    await tester.pump();
    await tester.tap(find.text('팀 찾기'));
    for (var i = 0; i < 4; i++) {
      await tester.pump(const Duration(milliseconds: 400));
    }

    expect(repo.saved?.positions, ['MF']);
    expect(repo.saved?.regions, ['서울 강남구']);
  });

  testWidgets('조건이 있으면 사람을 찾는 팀이 뜬다', (tester) async {
    await _open(tester, _Fake(prefs: _ready));

    expect(find.text('사람을 찾는 팀'), findsOneWidget);
    expect(find.text('베어스'), findsOneWidget);
  });

  /// 🔴 **어느 자리를 몇 명 찾는지 적는다** — 그게 없으면 지원할지 판단할 수
  /// 없다. 서버가 준 이름(`position_label`)을 그대로 쓴다.
  testWidgets('찾는 자리를 그대로 적는다', (tester) async {
    await _open(tester, _Fake(prefs: _ready));

    expect(find.textContaining('골키퍼'), findsOneWidget);
  });

  /// ⚠️ 찾는 자리가 **빈 경기도 목록에 남는다**(팀 대 팀으로 잡힌 경기다).
  testWidgets('찾는 자리가 없는 경기도 남는다', (tester) async {
    await _open(tester, _Fake(prefs: _ready));

    expect(find.text('한강 나이트'), findsOneWidget);
  });

  /// 🔴 **지역은 서버로 보낸다** — 받아 놓고 화면에서 거르면 다음 쪽을
  /// 못 가져온다.
  testWidgets('지역을 고르면 서버에 그 지역으로 묻는다', (tester) async {
    final repo = _Fake(prefs: _ready);
    await _open(tester, repo);

    expect(repo.asked.last.region, isNull);

    await tester.tap(find.byKey(const Key('seek-filter-서울 강남구')));
    for (var i = 0; i < 3; i++) {
      await tester.pump(const Duration(milliseconds: 400));
    }

    expect(repo.asked.last.region, '서울 강남구');
  });
}
