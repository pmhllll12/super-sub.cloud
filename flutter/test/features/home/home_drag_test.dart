import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/dev/data_source.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/auth/data/auth_providers.dart';
import 'package:super_sub/features/auth/data/auth_repository_mock.dart';
import 'package:super_sub/features/auth/presentation/session_controller.dart';
import 'package:super_sub/features/home/presentation/screens/home_screen.dart';
import 'package:super_sub/features/team/data/models/squad.dart';

/// 🔴 **홈 전체를 통과하는 끌기**(2026-09-21).
///
/// 지금까지 `seatsFromSquad` 단위 시험과 `SquadBoard` 단독 시험만 있었고,
/// **홈 → 판 → 리포지토리 → 낙관적 갱신** 이 이어지는지는 아무도 안 봤다.
/// 사용자가 실기기에서 잡은 둘(「내 카드가 사라진다」·「골키퍼를 옮기면
/// 포워드가 간다」)이 그 사이에서 난다.
class _AlwaysMock extends DataSourceController {
  @override
  bool build() => true;
}

Future<ProviderContainer> _pumpHome(WidgetTester tester) async {
  tester.view.physicalSize = const Size(1080, 2340);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);

  final container = ProviderContainer(
    overrides: [
      authRepositoryProvider.overrideWith(
        (ref) => MockAuthRepository(ref.watch(mockDbProvider)),
      ),
      useMockProvider.overrideWith(() => _AlwaysMock()),
    ],
  );
  addTearDown(container.dispose);

  await tester.pumpWidget(UncontrolledProviderScope(
    container: container,
    child: const MaterialApp(home: HomeScreen()),
  ));
  unawaited(
    container.read(sessionControllerProvider.notifier).loginAs(MockDb.playerId),
  );
  // Mock 지연이 줄줄이 걸린다(로그인 → 스쿼드 → 팀원 카드 → 자동 착석).
  for (var i = 0; i < 5; i += 1) {
    await tester.pump(const Duration(milliseconds: 500));
  }
  return container;
}

/// 판을 펼친다 — 접혀 있으면 안 눌린다.
Future<void> _openSheet(WidgetTester tester) async {
  await tester.tap(find.byKey(const Key('home-squad-handle')));
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 1500));
  await tester.pump(const Duration(milliseconds: 700));
}

Future<void> _drag(WidgetTester tester, String from, String to) async {
  final a = tester.getCenter(find.byKey(ValueKey('squad-seat-$from')));
  final b = tester.getCenter(find.byKey(ValueKey('squad-seat-$to')));
  final g = await tester.startGesture(a);
  await tester.pump(const Duration(milliseconds: 600));
  await g.moveTo(b);
  await tester.pump();
  await g.up();
  // 낙관적 갱신 + 서버 왕복(300ms).
  for (var i = 0; i < 3; i += 1) {
    await tester.pump(const Duration(milliseconds: 300));
  }
}

/// 🔴 **서버(=MockDb)의 실제 상태를 본다.** `squadProvider` 는 한 번 읽은
/// 값을 들고 있어서, 쓰기가 서버에 반영됐는지는 저장소를 봐야 안다.
Squad _squadOf(ProviderContainer c) {
  final me = c.read(sessionControllerProvider) as SessionLoggedIn;
  return c
      .read(mockDbProvider)
      .squads
      .firstWhere((s) => s.teamId == me.user.ownedTeamId);
}

void main() {
  /// 시드: 내 카드는 자동 착석으로 FW(1,0), 이감독 GK(1,3), 박신입 MF.
  testWidgets('처음에 내 카드가 FW 에 있다', (tester) async {
    final c = await _pumpHome(tester);

    final squad = _squadOf(c);
    final mine = squad.members.where(
      (m) => m.cardPublicSlug == 'baek-seonggeom-3a71',
    );
    expect(mine, hasLength(1));
    expect([mine.single.gridCol, mine.single.gridRow], [1, 0]);
  });

  /// 🔴 사용자가 잡은 것 — 「내 포워드 카드를 다른 자리로 옮기면 사라진다」.
  testWidgets('내 카드를 옮겨도 판에 남는다', (tester) async {
    final c = await _pumpHome(tester);
    await _openSheet(tester);

    await _drag(tester, 'fw1', 'df1'); // FW(1,0) → DF(1,2)

    final squad = _squadOf(c);
    final mine = squad.members.where(
      (m) => m.cardPublicSlug == 'baek-seonggeom-3a71',
    );
    expect(mine, hasLength(1), reason: '내 등재가 사라졌다');
    expect([mine.single.gridCol, mine.single.gridRow], [1, 2],
        reason: '내 카드가 옮겨지지 않았다');
  });

  /// 🔴 사용자가 잡은 것 — 「골키퍼를 옮기면 포워드 카드가 골키퍼로 간다」.
  testWidgets('골키퍼를 옮겨도 내 카드는 FW 에 남는다', (tester) async {
    final c = await _pumpHome(tester);
    await _openSheet(tester);

    await _drag(tester, 'gk', 'mf2'); // GK(1,3) → MF 오른쪽(2,1)

    final squad = _squadOf(c);
    final mine = squad.members.singleWhere(
      (m) => m.cardPublicSlug == 'baek-seonggeom-3a71',
    );
    expect([mine.gridCol, mine.gridRow], [1, 0], reason: '내 카드가 딸려 갔다');

    final gk = squad.members.singleWhere((m) => m.nickname == '이감독');
    expect([gk.gridCol, gk.gridRow], [2, 1], reason: '골키퍼가 안 옮겨졌다');
  });
}
