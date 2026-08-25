import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/auth/data/auth_providers.dart';
import 'package:super_sub/features/auth/presentation/session_controller.dart';
import 'package:super_sub/features/profile/presentation/screens/profile_screen.dart';

Future<ProviderContainer> _pump(WidgetTester tester, String userId) async {
  final container = ProviderContainer();
  addTearDown(container.dispose);

  await tester.pumpWidget(UncontrolledProviderScope(
    container: container,
    child: const MaterialApp(home: ProfileScreen()),
  ));

  // MockAuthRepository는 300ms 지연을 흉내낸다. pumpWidget 이전에 이 Future를
  // 직접 await하면 위젯 테스트의 가짜 시계가 아직 흐르지 않아 영원히 끝나지
  // 않는다 — home_screen_test.dart / login_screen_test.dart와 동일한
  // 관용구(먼저 pumpWidget, 그 다음 트리거, pump(500ms)로 소화)를 따른다.
  unawaited(
    container.read(sessionControllerProvider.notifier).loginAs(userId),
  );
  await tester.pump(const Duration(milliseconds: 500));
  await tester.pumpAndSettle();
  return container;
}

void main() {
  testWidgets('닉네임과 이메일을 보여준다', (tester) async {
    await _pump(tester, MockDb.playerId);
    expect(find.text('김용병'), findsOneWidget);
    expect(find.text('player@supersub.test'), findsOneWidget);
  });

  testWidgets('바텀시트에서 닉네임을 바꾼다', (tester) async {
    final container = await _pump(tester, MockDb.playerId);

    await tester.tap(find.byKey(const Key('profile-edit')));
    await tester.pumpAndSettle();

    await tester.enterText(find.byKey(const Key('profile-nickname')), '김교체');
    await tester.tap(find.byKey(const Key('profile-save')));
    // 저장은 리포지토리를 거치므로 300ms 지연이 있다. 저장 중에는
    // 인디케이터가 계속 애니메이션하므로 pumpAndSettle을 쓰면 안 된다.
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pumpAndSettle();

    final state = container.read(sessionControllerProvider) as SessionLoggedIn;
    expect(state.user.nickname, equals('김교체'));
    expect(find.text('김교체'), findsOneWidget);
  });

  testWidgets('저장하는 동안 진행 표시가 뜨고 버튼이 잠긴다', (tester) async {
    await _pump(tester, MockDb.playerId);

    await tester.tap(find.byKey(const Key('profile-edit')));
    await tester.pumpAndSettle();

    await tester.enterText(find.byKey(const Key('profile-nickname')), '김교체');
    await tester.tap(find.byKey(const Key('profile-save')));
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    final button = tester.widget<FilledButton>(
      find.byKey(const Key('profile-save')),
    );
    expect(button.onPressed, isNull);

    await tester.pump(const Duration(milliseconds: 500));
    await tester.pumpAndSettle();
  });

  testWidgets('저장에 실패하면 시트가 닫히지 않고 오류를 보여준다', (tester) async {
    final container = await _pump(tester, MockDb.playerId);

    await tester.tap(find.byKey(const Key('profile-edit')));
    await tester.pumpAndSettle();

    // 세션이 끊긴 상태에서의 저장 = 서버가 거절하는 경우.
    // 여기서도 Future를 직접 await하면 가짜 시계가 멈춰 있어 끝나지 않는다.
    unawaited(container.read(authRepositoryProvider).logout());
    await tester.pump(const Duration(milliseconds: 500));

    await tester.enterText(find.byKey(const Key('profile-nickname')), '김교체');
    await tester.tap(find.byKey(const Key('profile-save')));
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pumpAndSettle();

    expect(find.text('로그인이 필요합니다'), findsOneWidget);
    expect(find.byKey(const Key('profile-nickname')), findsOneWidget);
  });
}
