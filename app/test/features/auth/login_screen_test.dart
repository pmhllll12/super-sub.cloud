import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/features/auth/presentation/screens/login_screen.dart';
import 'package:super_sub/features/auth/presentation/session_controller.dart';

Widget _wrap() => const ProviderScope(
      child: MaterialApp(home: LoginScreen()),
    );

void main() {
  testWidgets('이메일과 비밀번호 입력란이 있다', (tester) async {
    await tester.pumpWidget(_wrap());
    // LoginScreen.build()가 sessionControllerProvider.notifier를 읽는 순간
    // SessionController가 fire-and-forget _restore()(Mock 300ms 지연)를
    // 시작한다. pump로 흘려보내지 않으면 테스트 종료 시 타이머가 남아
    // "A Timer is still pending" 실패가 난다.
    await tester.pump(const Duration(milliseconds: 500));
    expect(find.byType(TextField), findsNWidgets(2));
  });

  testWidgets('개발용 바로 진입 계정 3종이 있다', (tester) async {
    await tester.pumpWidget(_wrap());
    await tester.pump(const Duration(milliseconds: 500));
    expect(find.text('개인 사용자 (데이터 있음)'), findsOneWidget);
    expect(find.text('팀 관리자'), findsOneWidget);
    expect(find.text('신규 가입자 (데이터 0건)'), findsOneWidget);
  });

  testWidgets('없는 이메일로 로그인하면 오류 문구가 뜬다', (tester) async {
    await tester.pumpWidget(_wrap());
    await tester.enterText(find.byKey(const Key('login-email')), 'x@y.test');
    await tester.enterText(find.byKey(const Key('login-password')), 'pw');
    await tester.tap(find.byKey(const Key('login-submit')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));
    expect(find.text('등록되지 않은 이메일입니다'), findsOneWidget);
  });

  testWidgets('바로 진입 버튼을 누르면 세션이 생긴다', (tester) async {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    await tester.pumpWidget(UncontrolledProviderScope(
      container: container,
      child: const MaterialApp(home: LoginScreen()),
    ));
    await tester.tap(find.text('팀 관리자'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));

    expect(container.read(sessionControllerProvider), isA<SessionLoggedIn>());
  });
}
