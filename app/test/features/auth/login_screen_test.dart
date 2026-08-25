import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/features/auth/presentation/screens/login_screen.dart';
import 'package:super_sub/features/auth/presentation/session_controller.dart';

Widget _wrap() => const ProviderScope(
      child: MaterialApp(home: LoginScreen()),
    );

/// 시트를 끝까지 아래로 접는다.
///
/// 시트는 펼친 채로 시작한다 — 인트로가 끝나면 바로 로그인 폼이 나와야 하기
/// 때문이다. 접힘 상태를 보려면 밀어 내려야 한다.
Future<void> _closeSheet(WidgetTester tester) async {
  await tester.drag(find.byType(LoginScreen), const Offset(0, 600));
  // 안착 애니메이션(340ms)을 흘려보낸다. pumpAndSettle은 쓰지 않는다 —
  // 로딩 인디케이터가 뜨면 무한 애니메이션이라 끝나지 않는다.
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 400));
}

void main() {
  testWidgets('이메일과 비밀번호 입력란이 있다', (tester) async {
    await tester.pumpWidget(_wrap());
    expect(find.byType(TextField), findsNWidgets(2));
  });

  testWidgets('개발용 바로 진입 계정 3종이 있다', (tester) async {
    await tester.pumpWidget(_wrap());
    expect(find.text('개인 사용자 (데이터 있음)'), findsOneWidget);
    expect(find.text('팀 관리자'), findsOneWidget);
    expect(find.text('신규 가입자 (데이터 0건)'), findsOneWidget);
  });

  testWidgets('펼친 채로 시작하고, 접으면 올리라는 힌트로 바뀐다', (tester) async {
    await tester.pumpWidget(_wrap());

    Opacity opacityOf(String text) => tester.widget<Opacity>(
          find.ancestor(
            of: find.text(text),
            matching: find.byType(Opacity),
          ).first,
        );

    expect(opacityOf('아래로 내려 닫기').opacity, 1);
    expect(opacityOf('위로 올려 로그인').opacity, 0);

    await _closeSheet(tester);

    expect(opacityOf('아래로 내려 닫기').opacity, 0);
    expect(opacityOf('위로 올려 로그인').opacity, 1);
  });

  testWidgets('없는 이메일로 로그인하면 오류 문구가 뜬다', (tester) async {
    await tester.pumpWidget(_wrap());

    await tester.enterText(find.byKey(const Key('login-email')), 'x@y.test');
    await tester.enterText(find.byKey(const Key('login-password')), 'pw');
    await tester.tap(find.byKey(const Key('login-submit')));
    await tester.pump();
    // 탭 시점에 SessionController가 초기화되며 fire-and-forget _restore()
    // (Mock 300ms 지연)도 함께 뜬다. 같은 이유로 pump가 필요한 사례가
    // smoke_test.dart에도 있다 — 이 pump는 login()과 _restore() 양쪽을
    // 모두 흘려보낸다.
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
    // 위와 동일 — smoke_test.dart의 pump(500ms) 관용구 참고.
    await tester.pump(const Duration(milliseconds: 500));

    expect(container.read(sessionControllerProvider), isA<SessionLoggedIn>());
  });
}
