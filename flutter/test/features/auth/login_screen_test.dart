import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/auth/data/auth_providers.dart';
import 'package:super_sub/features/auth/data/auth_repository.dart';
import 'package:super_sub/features/auth/data/auth_repository_mock.dart';
import 'package:super_sub/features/auth/data/models/app_user.dart';
import 'package:super_sub/features/auth/data/models/session.dart';
import 'package:super_sub/features/auth/presentation/screens/login_screen.dart';
import 'package:super_sub/features/auth/presentation/session_controller.dart';

/// `POST /auth/login` 이 429 를 준 상황만 흉내낸다 — [MockAuthRepository]는
/// 서버가 없어 요청 제한을 모르므로, 화면의 잠금 배선만 따로 검증한다.
class _TooManyRequestsAuthRepository implements AuthRepository {
  @override
  Future<Session> login({required String email, required String password}) {
    throw const AuthException(
      '요청이 너무 잦습니다',
      code: 'TOO_MANY_REQUESTS',
      retryAfter: 2,
    );
  }

  @override
  Future<Session> loginAs(String userId) => throw UnimplementedError();

  @override
  Future<void> logout() async {}

  @override
  Future<Session?> restoreSession() async => null;

  @override
  Future<AppUser> updateProfile({required String nickname}) =>
      throw UnimplementedError();
}

// 화면·세션 로직 테스트는 실제 API가 아니라 Mock을 상대한다 — 빠르고
// 결정적이며, 백엔드 없이도 돈다. ApiAuthRepository 자체의 동작은
// auth_repository_api_test.dart(있다면)가 따로 본다.
final _authOverride = authRepositoryProvider.overrideWith(
  (ref) => MockAuthRepository(ref.watch(mockDbProvider)),
);

Widget _wrap() => ProviderScope(
      overrides: [_authOverride],
      child: const MaterialApp(home: LoginScreen()),
    );

void main() {
  testWidgets('이메일과 비밀번호 입력란이 있다', (tester) async {
    await tester.pumpWidget(_wrap());
    expect(find.byType(TextField), findsNWidgets(2));
  });

  testWidgets('시트가 고정이라 여닫는 힌트가 없다', (tester) async {
    await tester.pumpWidget(_wrap());
    expect(find.textContaining('올려'), findsNothing);
    expect(find.textContaining('내려'), findsNothing);
  });

  testWidgets('개발용 바로 진입 계정 3종이 있다', (tester) async {
    await tester.pumpWidget(_wrap());
    expect(find.text('개인 사용자 (데이터 있음)'), findsOneWidget);
    expect(find.text('팀 관리자'), findsOneWidget);
    expect(find.text('신규 가입자 (데이터 0건)'), findsOneWidget);
  });

  testWidgets('없는 이메일로 로그인하면 오류 문구가 뜬다', (tester) async {
    await tester.pumpWidget(_wrap());

    await tester.enterText(find.byKey(const Key('login-email')), 'x@y.test');
    await tester.enterText(find.byKey(const Key('login-password')), 'pw');
    await tester.tap(find.byKey(const Key('login-submit')));
    // 버튼은 눌림 애니메이션(340ms)이 끝난 뒤에 동작한다 — 눌린 것이 눈에
    // 보이고 나서 화면이 움직이게 하려는 것이다.
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    // 탭 시점에 SessionController가 초기화되며 fire-and-forget _restore()
    // (Mock 300ms 지연)도 함께 뜬다. 같은 이유로 pump가 필요한 사례가
    // smoke_test.dart에도 있다 — 이 pump는 login()과 _restore() 양쪽을
    // 모두 흘려보낸다.
    await tester.pump(const Duration(milliseconds: 500));
    expect(find.text('등록되지 않은 이메일입니다'), findsOneWidget);
  });

  testWidgets('바로 진입 버튼을 누르면 세션이 생긴다', (tester) async {
    final container = ProviderContainer(overrides: [_authOverride]);
    addTearDown(container.dispose);

    await tester.pumpWidget(UncontrolledProviderScope(
      container: container,
      child: const MaterialApp(home: LoginScreen()),
    ));

    await tester.tap(find.text('팀 관리자'));
    // 눌림 애니메이션(340ms)을 먼저 흘려보낸다.
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    // 위와 동일 — smoke_test.dart의 pump(500ms) 관용구 참고.
    await tester.pump(const Duration(milliseconds: 500));

    expect(container.read(sessionControllerProvider), isA<SessionLoggedIn>());
  });

  testWidgets('429를 받으면 안내 문구가 뜨고 로그인 버튼이 잠긴다', (tester) async {
    final override = authRepositoryProvider.overrideWith(
      (ref) => _TooManyRequestsAuthRepository(),
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [override],
        child: const MaterialApp(home: LoginScreen()),
      ),
    );

    await tester.enterText(find.byKey(const Key('login-email')), 'x@y.test');
    await tester.enterText(find.byKey(const Key('login-password')), 'pw');
    await tester.tap(find.byKey(const Key('login-submit')));
    // 눌림 애니메이션(340ms) 뒤에 로그인이 실행되고 곧바로 실패한다.
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));

    expect(find.text('요청이 너무 잦습니다. 2초 뒤에 다시 시도해 주세요.'),
        findsOneWidget);
    // 서버 메시지 그대로가 아니라 잠금 안내로 대체된다.
    expect(find.text('요청이 너무 잦습니다'), findsNothing);

    // 잠긴 동안 다시 눌러도 세션이 생기지 않는다(버튼이 잠겨 눌림 자체가 막힌다).
    await tester.tap(find.byKey(const Key('login-submit')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.text('요청이 너무 잦습니다. 2초 뒤에 다시 시도해 주세요.'),
        findsOneWidget);

    // 1초 뒤: 아직 잠겨 있다.
    await tester.pump(const Duration(seconds: 1));
    expect(find.text('요청이 너무 잦습니다. 1초 뒤에 다시 시도해 주세요.'),
        findsOneWidget);

    // 2초 뒤: 잠금이 풀리고 안내 문구가 사라진다.
    await tester.pump(const Duration(seconds: 1));
    expect(find.textContaining('다시 시도해 주세요'), findsNothing);
  });
}
