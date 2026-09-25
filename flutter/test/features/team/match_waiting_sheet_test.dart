import 'package:flutter/material.dart';
import 'package:super_sub/features/profile/presentation/widgets/player_card_view.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/match_providers.dart';
import 'package:super_sub/features/team/data/match_repository.dart';
import 'package:super_sub/features/team/data/squad_providers.dart';
import 'package:super_sub/features/team/data/squad_repository.dart';
import 'package:super_sub/features/team/data/models/match_application.dart';
import 'package:super_sub/features/team/data/models/match_candidate.dart';
import 'package:super_sub/features/team/data/models/open_match.dart';
import 'package:super_sub/features/team/data/models/review_option.dart';
import 'package:super_sub/features/team/data/models/squad.dart';
import 'package:super_sub/features/team/match_prefs.dart';
import 'package:super_sub/features/team/match_prefs_server.dart';
import 'package:super_sub/features/team/presentation/sheets/match_waiting_sheet.dart';

/// 수락을 **몇 번 물은 뒤에** 내주는 가짜 저장소 — 기다리는 갈래를 밟는다.
class _FakeMatch implements MatchRepository {
  _FakeMatch({this.acceptAfterPolls = 1, this.withSlug = false});

  final int acceptAfterPolls;

  /// 상대 팀이 판을 갖고 있는가 — `null` 인 것도 정상이다(계약).
  final bool withSlug;
  int polls = 0;
  final submitted = <({String reviewee, List<String> codes})>[];

  TeamMatchRequest _req(String status, {String? matchId}) => TeamMatchRequest(
        id: 'tmr-1',
        requesterTeamId: 't-thunder',
        targetTeamId: 't-gangnam',
        status: status,
        playedAt: '2026-10-03T11:00:00+09:00',
        place: '강남 풋살장',
        matchId: matchId,
        targetTeamName: 'FC 강남',
        targetSquadSlug: withSlug ? 'p-them' : null,
      );

  @override
  Future<List<TeamMatchRequest>> requests(String teamId) async {
    polls++;
    return [
      polls > acceptAfterPolls
          ? _req('accepted', matchId: 'm-1')
          : _req('pending'),
    ];
  }

  @override
  Future<MatchApplication> apply(String m) => throw UnimplementedError();
  @override
  Future<void> withdraw(String m, {required String applicationId}) async {}

  @override
  Future<List<ReviewOption>> reviewOptions() async => const [
        ReviewOption(code: 'manner_time', category: 'manner', label: '시간을 잘 지켰다'),
        ReviewOption(
            code: 'caution_would_not_repeat',
            category: 'caution',
            label: '다시 함께 뛰고 싶지 않다'),
      ];

  @override
  Future<void> submitReview(
    String matchId, {
    required String revieweeId,
    required List<String> optionCodes,
  }) async {
    submitted.add((reviewee: revieweeId, codes: optionCodes));
  }

  // 이 화면이 안 쓰는 것들.
  @override
  Future<void> cancelRequest(String teamId, {required String requestId}) async {}

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
  Future<List<MatchCandidate>> candidates(String t) async => const [];
  @override
  Future<TeamMatchRequest> requestMatch(
    String teamId, {
    required String targetTeamId,
    required String playedAt,
    required String place,
  }) async =>
      _req('pending');
}

SquadMember _m(String id, String nickname, String pos, int col, int row) =>
    SquadMember(
      id: id,
      playerCardId: 'c-$id',
      cardPublicSlug: 's-$id',
      nickname: nickname,
      positionCode: pos,
      positionLabel: pos,
      gridCol: col,
      gridRow: row,
      accepted: true,
    );

final _us = Squad(
  id: 'sq',
  teamId: 't-thunder',
  publicSlug: 'p',
  formation: '5:5',
  members: [
    _m('1', '정상호', 'FW', 1, 0),
    _m('2', '정어진', 'MF', 0, 1),
  ],
);

/// 상대 판을 슬러그로 내주는 가짜 저장소.
class _FakeSquads implements SquadRepository {
  @override
  Future<Squad?> squadBySlug(String publicSlug) async =>
      publicSlug == 'p-them'
          ? Squad(
              id: 'sq-them',
              teamId: 't-gangnam',
              publicSlug: 'p-them',
              formation: '5:5',
              members: [_m('9', '강남에이스', 'FW', 1, 0)],
            )
          : null;

  @override
  Future<Squad?> squadOf(String teamId) async => null;
  @override
  Future<Squad> enlist(String teamId,
          {required String playerCardId,
          required String positionCode,
          int? gridCol,
          int? gridRow}) =>
      throw UnimplementedError();
  @override
  Future<Squad> moveSeat(String teamId,
          {required String memberId,
          required String positionCode,
          int? gridCol,
          int? gridRow}) =>
      throw UnimplementedError();
  @override
  Future<Squad> removeSeat(String teamId, {required String memberId}) =>
      throw UnimplementedError();
  @override
  Future<void> removeTeamMember(String teamId, {required String userId}) async {}
}

Future<void> _open(WidgetTester tester, _FakeMatch repo) async {
  tester.view.physicalSize = const Size(1080, 2340);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        matchRepositoryProvider.overrideWithValue(repo),
        squadRepositoryProvider.overrideWithValue(_FakeSquads()),
      ],
      child: MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => ElevatedButton(
              onPressed: () => showMatchWaitingSheet(
                context,
                teamId: 't-thunder',
                requestId: 'tmr-1',
                ourTeamName: '영등포 pizza',
                ourSquad: _us,
              ),
              child: const Text('열기'),
            ),
          ),
        ),
      ),
    ),
  );

  await tester.tap(find.text('열기'));
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 400));
}

/// 폴링 한 바퀴를 흘려보낸다.
Future<void> _tick(WidgetTester tester) async {
  await tester.pump(kMatchPollEvery);
  await tester.pump(const Duration(milliseconds: 400));
}

void main() {
  _realCardTests();

  _realOpponentTests();

  /// 🔴 **「걸었다」와 「잡혔다」는 다르다** — 수락 전에는 기다리는 화면이다.
  testWidgets('수락 전에는 기다린다고 알린다', (tester) async {
    await _open(tester, _FakeMatch(acceptAfterPolls: 99));

    expect(find.textContaining('기다리는 중'), findsOneWidget);
    expect(find.text('경기 완료'), findsNothing);
  });

  testWidgets('수락되면 두 팀 판이 선다', (tester) async {
    await _open(tester, _FakeMatch());
    await _tick(tester);

    expect(find.text('영등포 pizza'), findsOneWidget);
    expect(find.text('FC 강남'), findsOneWidget);
    expect(find.text('정상호'), findsOneWidget);
  });

  /// 🔴 시각과 구장은 **신청할 때 우리가 고른 것**이다 — 여기서 지어내지 않는다.
  testWidgets('수락되면 언제 어디서가 보인다', (tester) async {
    await _open(tester, _FakeMatch());
    await _tick(tester);

    expect(find.textContaining('10월 3일'), findsOneWidget);
    expect(find.text('강남 풋살장'), findsOneWidget);
  });

  /// 🔴 상대 선수는 **이름을 지어내지 않는다** — 상대 판을 못 읽으면
  /// 「FC 강남 선수 N」처럼 **자리만** 채운다는 것이 드러나야 한다.
  testWidgets('상대 판을 못 읽으면 자리만 채운다', (tester) async {
    await _open(tester, _FakeMatch());
    await _tick(tester);

    expect(find.textContaining('FC 강남 선수'), findsWidgets);
  });

  /// 🔴 **판 둘이 위아래로 선다** (2026-09-25 사용자 요청). 폰 폭에 나란히
  /// 놓으면 카드가 손톱만 해진다 — 세로로 쌓으면 카드 크기가 산다.
  testWidgets('우리 판과 상대 판이 위아래로 선다', (tester) async {
    await _open(tester, _FakeMatch());
    await _tick(tester);

    final boards = find.byKey(const Key('waiting-pitch'));
    expect(boards, findsNWidgets(2));

    final us = tester.getRect(boards.first);
    final them = tester.getRect(boards.last);
    expect(them.top, greaterThan(us.bottom - 1), reason: '상대 판이 아래에 온다');
    expect(us.left, closeTo(them.left, 1), reason: '가로로 나란히 두지 않는다');
  });

  /// 🔴 **자리대로 선다** — 이름만 줄 세우면 어느 포지션인지가 사라진다.
  testWidgets('판에 포지션 줄이 보인다', (tester) async {
    await _open(tester, _FakeMatch());
    await _tick(tester);

    expect(find.text('GK'), findsWidgets);
    expect(find.text('FW'), findsWidgets);
  });

  /// 🔴 **우리 팀도 평가한다** (2026-09-25, 사용자: 「리뷰 페이지에서 우리
  /// 팀들도 있어야 하고」). 같이 뛴 사람은 상대만이 아니다.
  testWidgets('리뷰에 우리 팀원도 나온다', (tester) async {
    await _open(tester, _FakeMatch());
    await _tick(tester);
    await tester.drag(find.byType(ListView).last, const Offset(0, -900));
    await tester.pump();
    await tester.tap(find.text('경기 완료'));
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));

    expect(find.text('정상호'), findsOneWidget);
    expect(find.textContaining('FC 강남 선수'), findsWidgets);
  });

  /// 🔴 **항목은 그 사람을 눌러야 열린다** (같은 요청: 「사람 판마다 리뷰
  /// 버튼 다 처음부터 보여주지말고, 그사람 누르면 리뷰 버튼 나오게」).
  /// 다섯 명 × 아홉 항목이 한꺼번에 펼쳐지면 무엇을 고르는 중인지 잃는다.
  testWidgets('사람을 눌러야 평가 항목이 열린다', (tester) async {
    await _open(tester, _FakeMatch());
    await _tick(tester);
    await tester.drag(find.byType(ListView).last, const Offset(0, -900));
    await tester.pump();
    await tester.tap(find.text('경기 완료'));
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pump(const Duration(milliseconds: 400));

    expect(find.text('시간을 잘 지켰다'), findsNothing);

    await tester.tap(find.text('정상호'));
    await tester.pump(const Duration(milliseconds: 400));

    expect(find.text('시간을 잘 지켰다'), findsOneWidget);
  });

  testWidgets('경기 완료를 누르면 리뷰가 뜬다', (tester) async {
    await _open(tester, _FakeMatch());
    await _tick(tester);

    // 판 둘이 세로로 서면서 단추가 아래로 밀렸다 — 끌어 올려 누른다.
    await tester.drag(find.byType(ListView).last, const Offset(0, -900));
    await tester.pump();
    await tester.tap(find.text('경기 완료'));
    await tester.pump(const Duration(milliseconds: 400));
    // 평가 항목은 그 화면이 뜬 뒤에 **비로소** 물어본다 — 답이 오는 프레임이
    // 하나 더 있다.
    await tester.pump(const Duration(milliseconds: 400));

    expect(find.textContaining('평가해'), findsOneWidget);
  });

  /// 🔴 **하나도 안 고르면 못 낸다**(422 `NO_OPTION_SELECTED`) — 화면이 먼저
  /// 막아야 빈 평가로 서버를 부르지 않는다.
  testWidgets('아무것도 안 고르면 제출이 안 된다', (tester) async {
    final repo = _FakeMatch();
    await _open(tester, repo);
    await _tick(tester);

    // 판 둘이 세로로 서면서 단추가 아래로 밀렸다 — 끌어 올려 누른다.
    await tester.drag(find.byType(ListView).last, const Offset(0, -900));
    await tester.pump();
    await tester.tap(find.text('경기 완료'));
    await tester.pump(const Duration(milliseconds: 400));
    // 평가 항목은 그 화면이 뜬 뒤에 **비로소** 물어본다 — 답이 오는 프레임이
    // 하나 더 있다.
    await tester.pump(const Duration(milliseconds: 400));
    // 상대가 다섯이라 보내기 단추는 아래에 있다 — 끌어 올려 누른다.
    await tester.drag(find.byType(ListView).last, const Offset(0, -600));
    await tester.pump();
    await tester.tap(find.text('평가 보내기'));
    await tester.pump(const Duration(milliseconds: 400));

    expect(repo.submitted, isEmpty);
  });

  testWidgets('고르고 보내면 그 항목이 나간다', (tester) async {
    final repo = _FakeMatch();
    await _open(tester, repo);
    await _tick(tester);

    // 판 둘이 세로로 서면서 단추가 아래로 밀렸다 — 끌어 올려 누른다.
    await tester.drag(find.byType(ListView).last, const Offset(0, -900));
    await tester.pump();
    await tester.tap(find.text('경기 완료'));
    await tester.pump(const Duration(milliseconds: 400));
    // 평가 항목은 그 화면이 뜬 뒤에 **비로소** 물어본다 — 답이 오는 프레임이
    // 하나 더 있다.
    await tester.pump(const Duration(milliseconds: 400));
    await tester.tap(find.text('정상호'));
    await tester.pump(const Duration(milliseconds: 400));
    await tester.tap(find.text('시간을 잘 지켰다'));
    await tester.pump(const Duration(milliseconds: 400));
    // 상대가 다섯이라 보내기 단추는 아래에 있다 — 끌어 올려 누른다.
    await tester.drag(find.byType(ListView).last, const Offset(0, -600));
    await tester.pump();
    await tester.tap(find.text('평가 보내기'));
    await tester.pump(const Duration(milliseconds: 400));

    expect(repo.submitted, hasLength(1));
    expect(repo.submitted.single.codes, ['manner_time']);
  });
}

/// 🔴 **상대 판은 진짜로 읽는다** (2026-09-25, 사용자: 「실제 그 사람들의
/// 카드가 나와야지. 이게 뭐야」). 신청 응답의 `target_squad_public_slug` 로
/// `GET /squads/{slug}` 를 부른다 — 누구나 읽는 경로다(SEC-005).
void _realOpponentTests() {
  testWidgets('상대 판이 있으면 그 사람들의 이름이 뜬다', (tester) async {
    await _open(tester, _FakeMatch(withSlug: true));
    await _tick(tester);
    await tester.pump(const Duration(milliseconds: 400));

    expect(find.text('강남에이스'), findsOneWidget);
    expect(find.textContaining('FC 강남 선수'), findsNothing,
        reason: '진짜 판이 있으면 자리표시자를 쓰지 않는다');
  });
}

/// 🔴 **판에는 카드가 선다** (2026-09-25, 사용자가 두 번 짚었다: 「실제
/// 카드들이 나와야 한다고 ... 지금 그냥 가로로 긴 사각형 이잖아」).
/// 카드가 아직 안 왔으면 **빈 카드 + 이름**이다 — 홈 판과 같은 물러남이고,
/// 가로로 긴 상자가 아니다. 진짜 카드를 그리는 갈래는
/// `read_only_pitch_test.dart` 가 따로 본다.
void _realCardTests() {
  testWidgets('자리가 카드 모양으로 선다', (tester) async {
    await _open(tester, _FakeMatch());
    await _tick(tester);

    expect(find.byType(BlankPlayerCardView), findsWidgets);
  });

  testWidgets('상대 선수도 카드에 이름이 든다', (tester) async {
    await _open(tester, _FakeMatch(withSlug: true));
    await _tick(tester);
    await tester.pump(const Duration(milliseconds: 400));

    expect(find.text('강남에이스'), findsOneWidget);
  });
}
