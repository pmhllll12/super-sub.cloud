import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/candidate_providers.dart';
import 'package:super_sub/features/team/data/candidate_repository.dart';
import 'package:super_sub/features/team/data/contact_repository.dart';
import 'package:super_sub/features/team/data/models/contact.dart';
import 'package:super_sub/features/team/data/models/squad_candidate.dart';
import 'package:super_sub/features/team/presentation/sheets/seat_fill_sheet.dart';

/// 무엇을 어떤 등급으로 물었는지 받아 적는 가짜 저장소.
class _FakeCandidates implements CandidateRepository {
  _FakeCandidates(this._rows);

  final List<SquadCandidate> _rows;
  final asked = <String?>[];

  @override
  Future<List<SquadCandidate>> candidates(
    String teamId, {
    required String positionCode,
    String? grade,
  }) async {
    asked.add(grade);
    if (grade == null) return _rows;
    return _rows.where((c) => c.grade == grade).toList();
  }

  @override
  Future<String?> featuredVideoId(String cardPublicSlug) async => null;
}

class _FakeContacts implements ContactRepository {
  _FakeContacts(this._list);

  final List<Contact> _list;
  final requested = <String>[];

  @override
  Future<List<Contact>> contacts() async => _list;
  @override
  Future<List<ContactRequest>> requests() async => const [];
  @override
  Future<List<FoundUser>> search(String query) async => query.isEmpty
      ? const []
      : const [FoundUser(id: 'u-new', nickname: '새사람')];
  @override
  Future<void> request(String targetUserId) async => requested.add(targetUserId);
  @override
  Future<void> accept(String contactId) async {}
}

const _rows = [
  SquadCandidate(
    userId: 'u-line',
    nickname: '라인세우기',
    cardPublicSlug: 'line-1',
    grade: 'A',
    provisional: false,
    notes: ['수비 라인을 먼저 올립니다'],
  ),
  SquadCandidate(
    userId: 'u-futsal',
    nickname: '풋살초보',
    cardPublicSlug: 'futsal-1',
    grade: 'F',
    provisional: true,
    notes: ['공을 몸 가까이에 두려 합니다'],
  ),
  SquadCandidate(userId: 'u-rookie', nickname: '오재현'),
];

/// 마지막으로 고른 사람. 시트는 `Navigator.pop` 으로 돌려주므로 호출자 쪽에서
/// 받아 둔다.
SeatPick? lastPick;

/// 🔴 시트에는 무한 애니메이션이 없지만 그래도 `pumpAndSettle` 을 쓰지
/// 않는다 — 이 폴더의 관례는 「옆 파일을 따라 쓰지 말고 그 화면을 보고
/// 정한다」이고, 바텀시트의 등장 애니메이션은 `pump(500ms)` 로 충분하다.
Future<void> _open(
  WidgetTester tester, {
  required CandidateRepository candidates,
  required ContactRepository contacts,
  Map<String, String> placed = const {},
}) async {
  lastPick = null;
  tester.view.physicalSize = const Size(1080, 2340);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        candidateRepositoryProvider.overrideWithValue(candidates),
        contactRepositoryProvider.overrideWithValue(contacts),
      ],
      child: MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => ElevatedButton(
              onPressed: () async {
                lastPick = await showSeatFillSheet(
                  context,
                  teamId: 't-thunder',
                  positionCode: 'DF',
                  positionLabel: '수비수',
                  placed: placed,
                );
              },
              child: const Text('열기'),
            ),
          ),
        ),
      ),
    ),
  );

  await tester.tap(find.text('열기'));
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 500));
}

void main() {
  _friendGroupingTests();

  testWidgets('후보의 닉네임·등급·문구가 보인다', (tester) async {
    await _open(
      tester,
      candidates: _FakeCandidates(_rows),
      contacts: _FakeContacts(const []),
    );

    expect(find.text('라인세우기'), findsOneWidget);
    expect(find.byKey(const Key('cand-grade-u-line')), findsOneWidget);
    expect(find.text('수비 라인을 먼저 올립니다'), findsOneWidget);
  });

  /// 🔴 어느 자리를 채우는지 머리말에 있어야 한다 — 자리를 누르고 들어왔어도
  /// 목록을 훑다 보면 무엇을 고르던 중인지 잊는다.
  testWidgets('어느 자리를 채우는지 머리말에 있다', (tester) async {
    await _open(
      tester,
      candidates: _FakeCandidates(_rows),
      contacts: _FakeContacts(const []),
    );

    expect(find.textContaining('수비수'), findsWidgets);
  });

  /// 🔴 「검수 전」은 `provisional` 일 때만 — 늘 붙이면 검수된 등급까지
  /// 의심스럽게 보인다.
  testWidgets('검수 전은 그 사람에게만 붙는다', (tester) async {
    await _open(
      tester,
      candidates: _FakeCandidates(_rows),
      contacts: _FakeContacts(const []),
    );

    expect(find.text('검수 전'), findsOneWidget);
  });

  /// 🔴 등급을 모르는 후보도 목록에 남는다 — 서버가 뒤로 보낼 뿐이다.
  testWidgets('등급 없는 후보도 사라지지 않는다', (tester) async {
    await _open(
      tester,
      candidates: _FakeCandidates(_rows),
      contacts: _FakeContacts(const []),
    );

    expect(find.text('오재현'), findsOneWidget);
    expect(find.byKey(const Key('cand-grade-u-rookie')), findsNothing);
  });

  /// 🔴 **등급 필터는 서버로 간다.** 받아 놓고 화면에서 거르면 머리말의
  /// 「N명」이 안 맞는다 — 이 시험이 그걸 지킨다.
  testWidgets('등급을 누르면 그 등급으로 서버에 다시 묻는다', (tester) async {
    final repo = _FakeCandidates(_rows);
    await _open(tester, candidates: repo, contacts: _FakeContacts(const []));

    expect(repo.asked, [null]);

    await tester.tap(find.byKey(const Key('grade-chip-A')));
    await tester.pump(const Duration(milliseconds: 500));

    expect(repo.asked, [null, 'A']);
  });

  /// 🔴 「없음」을 오류처럼 보이게 하면 사용자가 등급을 풀 생각을 못 한다.
  testWidgets('후보가 없으면 등급을 풀라고 안내한다', (tester) async {
    await _open(
      tester,
      candidates: _FakeCandidates(const []),
      contacts: _FakeContacts(const []),
    );

    expect(find.textContaining('없습니다'), findsOneWidget);
  });

  testWidgets('후보를 고르면 그 사람을 돌려준다', (tester) async {
    await _open(
      tester,
      candidates: _FakeCandidates(_rows),
      contacts: _FakeContacts(const []),
    );

    await tester.tap(find.text('라인세우기'));
    await tester.pump(const Duration(milliseconds: 500));

    expect(lastPick?.userId, 'u-line');
    expect(lastPick?.nickname, '라인세우기');
    expect(lastPick?.cardPublicSlug, 'line-1');
  });

  testWidgets('지인 탭으로 옮기면 지인이 보인다', (tester) async {
    await _open(
      tester,
      candidates: _FakeCandidates(_rows),
      contacts: _FakeContacts(const [
        Contact(contactId: 'c1', userId: 'u-jin', nickname: '정어진'),
      ]),
    );

    await tester.tap(find.byKey(const Key('seat-tab-friends')));
    await tester.pump(const Duration(milliseconds: 500));
    // 지인 목록은 탭을 열 때 **비로소** 물어본다 — 그 답이 오는 프레임이 하나 더 있다.
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.text('정어진'), findsOneWidget);
  });

  /// 🔴 이미 판에 앉은 지인은 다시 못 고른다 — 고르면 같은 사람이 판에
  /// 둘이 된다. 어느 자리에 있는지도 함께 보여 준다.
  testWidgets('이미 앉은 지인은 자리를 보여 주고 못 고른다', (tester) async {
    await _open(
      tester,
      candidates: _FakeCandidates(_rows),
      contacts: _FakeContacts(const [
        Contact(contactId: 'c1', userId: 'u-jin', nickname: '정어진'),
      ]),
      placed: const {'정어진': 'MF'},
    );

    await tester.tap(find.byKey(const Key('seat-tab-friends')));
    await tester.pump(const Duration(milliseconds: 500));
    // 지인 목록은 탭을 열 때 **비로소** 물어본다 — 그 답이 오는 프레임이 하나 더 있다.
    await tester.pump(const Duration(milliseconds: 500));
    expect(find.text('MF'), findsOneWidget);

    await tester.tap(find.text('정어진'));
    await tester.pump(const Duration(milliseconds: 500));

    // 안 닫혔고 아무도 안 골랐다.
    expect(find.text('정어진'), findsOneWidget);
    expect(lastPick, isNull);
  });

  /// 🔴 지인이 아닌 사람은 **바로 앉힐 수 없다** — 지인 신청이 먼저다.
  /// 검색 결과를 그냥 고를 수 있게 두면 동의 없이 부르는 길이 생긴다.
  testWidgets('검색으로 찾은 남은 지인 신청부터 한다', (tester) async {
    final contacts = _FakeContacts(const []);
    await _open(
      tester,
      candidates: _FakeCandidates(_rows),
      contacts: contacts,
    );

    await tester.tap(find.byKey(const Key('seat-tab-friends')));
    await tester.pump(const Duration(milliseconds: 500));
    // 지인 목록은 탭을 열 때 **비로소** 물어본다 — 그 답이 오는 프레임이 하나 더 있다.
    await tester.pump(const Duration(milliseconds: 500));

    await tester.enterText(find.byKey(const Key('friend-search')), '새');
    await tester.pump(const Duration(milliseconds: 600));

    expect(find.text('새사람'), findsOneWidget);
    await tester.tap(find.text('지인 신청'));
    await tester.pump(const Duration(milliseconds: 500));

    expect(contacts.requested, ['u-new']);
    expect(lastPick, isNull);
  });
}

/// 🔴 **지인이 위, 다른 사람이 아래** (2026-09-25 사용자 요청: 「지인들만 위에
/// 나오게 하고, 그 외에 실제 다른 사용자들 이름 아래로」).
///
/// ⚠️ **아무것도 안 친 상태에서는 아래가 빈다.** 서버의 `GET /users/search` 가
/// `q` 를 **최소 한 자** 받고(빈 값은 422), 「전체 사용자 목록」 경로가 계약에
/// 없다 — 그 경로가 생기면 아래 묶음을 처음부터 채운다.
void _friendGroupingTests() {
  testWidgets('지인과 다른 사람이 묶음으로 갈린다', (tester) async {
    await _open(
      tester,
      candidates: _FakeCandidates(_rows),
      contacts: _FakeContacts(const [
        Contact(contactId: 'c1', userId: 'u-jin', nickname: '정어진'),
      ]),
    );

    await tester.tap(find.byKey(const Key('seat-tab-friends')));
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.text('지인'), findsWidgets);

    /* 「정」은 지인(정어진)에도 걸리고, 가짜 서버는 아무 글자에나 「새사람」을
       내준다 — 두 묶음이 함께 서는 상태를 만든다. */
    await tester.enterText(find.byKey(const Key('friend-search')), '정');
    await tester.pump(const Duration(milliseconds: 600));

    final friends = tester.getRect(find.text('정어진'));
    final others = tester.getRect(find.text('새사람'));
    expect(others.top, greaterThan(friends.top), reason: '다른 사람이 아래다');
    expect(find.text('다른 사람'), findsOneWidget);
  });
}
