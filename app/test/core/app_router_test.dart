import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/app.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/core/sport/current_sport.dart';
import 'package:super_sub/features/auth/presentation/session_controller.dart';
import 'package:super_sub/features/intro/presentation/intro_gate.dart';

/// redirect는 앱의 내비게이션 정책 전체를 담고 있다 — 복원 중, 로그아웃,
/// 종목 미선택, 온보딩 라우트에 남은 로그인 사용자, 통과. 다섯 갈래를 모두
/// 착지 화면으로 확인한다.
///
/// 관용구 주의: Mock은 300ms 지연을 흉내내고 위젯 테스트의 가짜 시계는
/// pump로만 흐른다. pumpWidget 전에 Mock Future를 await하면 영원히 끝나지
/// 않고, 로딩 인디케이터는 무한 애니메이션이라 pumpAndSettle도 쓰지 않는다
/// (home_screen_test.dart의 주석 참고).
Future<ProviderContainer> _pumpApp(WidgetTester tester) async {
  // 인트로를 끈다 — 켜 두면 3.1초 동안 모든 라우트를 덮어 착지 화면 대신
  // 인트로만 보인다. 인트로 자체는 glitch_intro_screen_test.dart가 본다.
  final container = ProviderContainer(
    overrides: [introEnabledProvider.overrideWithValue(false)],
  );
  addTearDown(container.dispose);

  await tester.pumpWidget(UncontrolledProviderScope(
    container: container,
    child: const SuperSubApp(),
  ));
  return container;
}

Future<ProviderContainer> _pumpHome(WidgetTester tester) async {
  final container = await _pumpApp(tester);
  unawaited(
    container.read(sessionControllerProvider.notifier).loginAs(MockDb.playerId),
  );
  container.read(currentSportProvider.notifier).select('futsal');
  await tester.pump(const Duration(milliseconds: 500));
  return container;
}

void main() {
  testWidgets('복원이 끝나기 전에는 로그인으로 보내지 않는다', (tester) async {
    await _pumpApp(tester);
    // 첫 프레임의 세션 상태는 SessionUnknown이다. 이때 로그인으로 보내면
    // 세션이 살아 있는 사용자도 매번 로그인 화면을 스친다.
    expect(find.text('로그인'), findsNothing);

    // 복원·종목 조회 타이머를 소화하고 끝낸다.
    await tester.pump(const Duration(milliseconds: 500));
  });

  testWidgets('로그아웃 상태면 로그인 화면에 착지한다', (tester) async {
    await _pumpApp(tester);
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.text('로그인'), findsWidgets);
  });

  testWidgets('로그인했지만 종목을 안 골랐으면 온보딩에 착지한다', (tester) async {
    final container = await _pumpApp(tester);
    unawaited(
      container
          .read(sessionControllerProvider.notifier)
          .loginAs(MockDb.playerId),
    );
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.text('종목 선택'), findsOneWidget);
    expect(find.text('로그인'), findsNothing);
  });

  testWidgets('종목까지 고르면 홈에 착지한다', (tester) async {
    await _pumpHome(tester);

    expect(find.text('홈'), findsOneWidget);
    expect(find.text('종목 선택'), findsNothing);
  });

  testWidgets('홈에서 로그아웃하면 로그인으로 돌아간다', (tester) async {
    await _pumpHome(tester);

    await tester.tap(find.byKey(const Key('home-logout')));
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.text('로그인'), findsWidgets);
    expect(find.text('홈'), findsNothing);
  });

  testWidgets('로그인·종목이 모두 갖춰지면 다른 라우트는 그대로 통과한다', (tester) async {
    await _pumpHome(tester);

    await tester.tap(find.text('내 프로필'));
    await tester.pump(const Duration(milliseconds: 500));

    // redirect가 개입하지 않고 /profile에 머무른다.
    expect(find.text('프로필'), findsOneWidget);
    // push로 열었으므로 뒤로가기 착지점이 있다 (I3).
    expect(find.byType(BackButton), findsOneWidget);
  });
}
