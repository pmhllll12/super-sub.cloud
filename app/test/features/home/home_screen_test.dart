import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/core/sport/current_sport.dart';
import 'package:super_sub/features/auth/presentation/session_controller.dart';
import 'package:super_sub/features/home/presentation/screens/home_screen.dart';

Future<ProviderContainer> _pumpLoggedIn(WidgetTester tester) async {
  final container = ProviderContainer();
  addTearDown(container.dispose);

  await tester.pumpWidget(UncontrolledProviderScope(
    container: container,
    child: const MaterialApp(home: HomeScreen()),
  ));

  // MockAuthRepository는 300ms 지연을 흉내낸다. 위젯 테스트의 가짜 시계는
  // pump로만 흘러가므로, pumpWidget 이전에 이 Future를 직접 await하면
  // 시계가 멈춰 있어 영원히 끝나지 않는다 — login_screen_test.dart와
  // 동일한 관용구(탭/트리거 후 pump)를 따른다.
  unawaited(
    container.read(sessionControllerProvider.notifier).loginAs(MockDb.playerId),
  );
  container.read(currentSportProvider.notifier).select('futsal');
  await tester.pump(const Duration(milliseconds: 500));
  await tester.pumpAndSettle();
  return container;
}

void main() {
  testWidgets('종목을 불러오는 동안 로딩을 보여준다', (tester) async {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    await tester.pumpWidget(UncontrolledProviderScope(
      container: container,
      child: const MaterialApp(home: HomeScreen()),
    ));
    // 종목 목록도 리포지토리에서 온다 — 첫 프레임은 아직 로딩이다.
    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    await tester.pump(const Duration(milliseconds: 500));
    expect(find.byType(CircularProgressIndicator), findsNothing);
  });

  testWidgets('닉네임과 현재 종목을 보여준다', (tester) async {
    await _pumpLoggedIn(tester);
    expect(find.textContaining('김용병'), findsOneWidget);
    expect(find.text('풋살'), findsOneWidget);
  });

  testWidgets('종목 칩으로 전환할 수 있다', (tester) async {
    final container = await _pumpLoggedIn(tester);
    await tester.tap(find.byKey(const Key('home-sport-baseball')));
    await tester.pumpAndSettle();
    expect(container.read(currentSportProvider), equals('baseball'));
  });

  testWidgets('갈라져 나가는 곳들을 모두 보여 준다', (tester) async {
    await _pumpLoggedIn(tester);
    for (final title in const [
      '영상 분석',
      '용병 매칭',
      '내 선수 카드',
      '내 팀',
      '레슨 · 코치',
      '내 프로필',
    ]) {
      expect(find.text(title), findsOneWidget, reason: title);
    }
  });

  testWidgets('아직 없는 화면은 준비 중으로 표시한다', (tester) async {
    await _pumpLoggedIn(tester);
    // 프로필만 실제 화면이 있다 — 나머지 다섯은 준비 중이다.
    expect(find.text('준비 중'), findsNWidgets(5));
  });

  testWidgets('바 메뉴를 열면 로그아웃 칸이 선다', (tester) async {
    await _pumpLoggedIn(tester);
    // 닫혀 있을 때는 아무 칸도 세우지 않는다.
    expect(find.byKey(const Key('barmenu-logout')), findsNothing);

    await tester.tap(find.byKey(const Key('navbar-icon-menu')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.byKey(const Key('barmenu-logout')), findsOneWidget);
    // 로그인·로그아웃은 함께 설 수 없다.
    expect(find.byKey(const Key('barmenu-login')), findsNothing);
  });

  testWidgets('바 메뉴의 로그아웃으로 세션이 끝난다', (tester) async {
    final container = await _pumpLoggedIn(tester);

    await tester.tap(find.byKey(const Key('navbar-icon-menu')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));
    await tester.tap(find.byKey(const Key('barmenu-logout')));
    await tester.pump(const Duration(milliseconds: 500));

    expect(container.read(sessionControllerProvider), isA<SessionLoggedOut>());
  });

  testWidgets('로그아웃 버튼이 있다', (tester) async {
    final container = await _pumpLoggedIn(tester);
    await tester.tap(find.byKey(const Key('home-logout')));
    await tester.pump(const Duration(milliseconds: 500));
    expect(container.read(sessionControllerProvider), isA<SessionLoggedOut>());
  });
}
