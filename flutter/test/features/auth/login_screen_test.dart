import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/core/dev/data_source.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/auth/data/auth_providers.dart';
import 'package:super_sub/features/auth/data/auth_repository.dart';
import 'package:super_sub/features/auth/data/auth_repository_api.dart';
import 'package:super_sub/features/auth/data/auth_repository_mock.dart';
import 'package:super_sub/features/auth/data/google_id_token.dart';
import 'package:super_sub/features/auth/data/models/app_user.dart';
import 'package:super_sub/features/auth/data/models/session.dart';
import 'package:super_sub/features/auth/presentation/screens/login_screen.dart';
import 'package:super_sub/features/auth/presentation/session_controller.dart';

/// `POST /auth/login` 이 429 를 준 상황만 흉내낸다 — [MockAuthRepository]는
/// 서버가 없어 요청 제한을 모르므로, 화면의 잠금 배선만 따로 검증한다.
class _TooManyRequestsAuthRepository implements AuthRepository {
  // 이 대역은 429 잠금만 잰다 — 탈퇴는 안 쓴다.
  @override
  Future<void> deleteAccount({String? password}) => throw UnimplementedError();

  @override
  Future<Session> login({required String email, required String password}) {
    throw const AuthException(
      '요청이 너무 잦습니다',
      code: 'TOO_MANY_REQUESTS',
      retryAfter: 2,
    );
  }

  @override
  Future<Session> signup({
    required String email,
    required String password,
    required String nickname,
  }) {
    throw const AuthException(
      '요청이 너무 잦습니다',
      code: 'TOO_MANY_REQUESTS',
      retryAfter: 2,
    );
  }

  @override
  Future<Session> loginWithGoogle({required String idToken}) {
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
  Future<AppUser> updateProfile({String? nickname, bool? nicknameSearchable}) =>
      throw UnimplementedError();
}

/// 구글 창 대신 정해 둔 토큰을 준다. `null` 이면 사용자가 창을 닫은 것이다.
class _FixedToken implements GoogleIdTokenSource {
  const _FixedToken(this.idToken);

  final String? idToken;

  @override
  Future<String?> fetchIdToken() async => idToken;
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

/// 로그인 ↔ 가입 전환 글자를 누른다.
///
/// 폼 맨 아래라 800×600 시험 화면에서는 밖으로 밀린다 — 폰에서도 굴려서 닿는
/// 자리라 **굴려 보이게 한 뒤** 누른다.
Future<void> _tapModeToggle(WidgetTester tester) async {
  final toggle = find.byKey(const Key('auth-mode-toggle'));
  await tester.ensureVisible(toggle);
  await tester.pump();
  await tester.tap(toggle);
  await tester.pump();
}

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

  // 웹처럼 이메일 로그인과 구글 로그인 둘뿐이다. 바로 진입 버튼은 API 모드에서
  // 예외만 던졌다(2026-09-15 걷어냄).
  testWidgets('로그인 수단은 이메일과 구글 둘뿐이다', (tester) async {
    await tester.pumpWidget(_wrap());
    expect(find.byKey(const Key('login-submit')), findsOneWidget);
    expect(find.byKey(const Key('google-submit')), findsOneWidget);
    expect(find.textContaining('개발용'), findsNothing);
    expect(find.text('팀 관리자'), findsNothing);
  });

  // 개발 빌드(시험도 개발 빌드다)에서만 서는 단추. 서버가 꺼진 곳에서 화면 작업을
  // 잇는 용도다 — 데이터를 목업으로 바꾸고 목업 계정으로 들어간다.
  testWidgets('「개발자 전용」은 목업으로 바꾼 뒤 들어간다', (tester) async {
    // 인증을 덮어쓰지 않는다 — 실제 교체 지점이 스위치를 따라가는지 봐야 한다.
    final container = ProviderContainer();
    addTearDown(container.dispose);
    await tester.pumpWidget(UncontrolledProviderScope(
      container: container,
      child: const MaterialApp(home: LoginScreen()),
    ));
    expect(container.read(useMockProvider), isFalse);
    expect(container.read(authRepositoryProvider), isA<ApiAuthRepository>());

    final button = find.byKey(const Key('dev-only-login'));
    expect(find.text('개발자 전용'), findsOneWidget);
    await tester.ensureVisible(button);
    await tester.pump();
    await tester.tap(button);
    await tester.pump(const Duration(milliseconds: 500));

    expect(container.read(useMockProvider), isTrue);
    expect(container.read(authRepositoryProvider), isA<MockAuthRepository>());
    expect(container.read(sessionControllerProvider), isA<SessionLoggedIn>());
  });

  testWidgets('가입 모드에서는 「개발자 전용」을 안 보인다', (tester) async {
    await tester.pumpWidget(_wrap());
    await _tapModeToggle(tester);
    expect(find.byKey(const Key('dev-only-login')), findsNothing);
  });

  testWidgets('눈 단추로 비밀번호를 보였다 숨긴다', (tester) async {
    await tester.pumpWidget(_wrap());
    TextField password() =>
        tester.widget<TextField>(find.byKey(const Key('login-password')));

    expect(password().obscureText, isTrue);
    await tester.tap(find.byKey(const Key('password-reveal')));
    await tester.pump();
    expect(password().obscureText, isFalse);
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

  group('구글 로그인', () {
    Future<ProviderContainer> pumpWithToken(
      WidgetTester tester,
      String? idToken,
    ) async {
      final container = ProviderContainer(overrides: [
        _authOverride,
        googleIdTokenSourceProvider.overrideWithValue(_FixedToken(idToken)),
      ]);
      addTearDown(container.dispose);
      await tester.pumpWidget(UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(home: LoginScreen()),
      ));
      return container;
    }

    Future<void> tapGoogle(WidgetTester tester) async {
      await tester.tap(find.byKey(const Key('google-submit')));
      // 눌림 애니메이션(340ms) → 로그인(Mock 300ms) → _restore() 까지.
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pump(const Duration(milliseconds: 500));
    }

    testWidgets('토큰을 받으면 로그인된다', (tester) async {
      final container = await pumpWithToken(tester, 'google-id-token');
      await tapGoogle(tester);
      expect(container.read(sessionControllerProvider), isA<SessionLoggedIn>());
    });

    // 창을 닫은 것은 실패가 아니다 — 오류 문구를 띄우지 않는다.
    testWidgets('구글 창을 닫으면 아무 일도 없다', (tester) async {
      final container = await pumpWithToken(tester, null);
      container.read(sessionControllerProvider);
      await tapGoogle(tester);
      expect(
        container.read(sessionControllerProvider),
        isNot(isA<SessionLoggedIn>()),
      );
      expect(find.byType(CircularProgressIndicator), findsNothing);
      expect(find.textContaining('실패'), findsNothing);
    });

    testWidgets('가입 모드에서는 글자만 가입으로 바뀐다', (tester) async {
      await tester.pumpWidget(_wrap());
      expect(find.text('구글 계정으로 로그인'), findsOneWidget);
      await _tapModeToggle(tester);
      expect(find.text('구글 계정으로 가입'), findsOneWidget);
    });
  });

  group('회원가입', () {
    /// 가입으로 바꾸고 세 칸을 채운 뒤 「가입하기」를 누른다.
    Future<void> signUp(
      WidgetTester tester, {
      required String email,
      required String password,
      String nickname = '새식구',
    }) async {
      await _tapModeToggle(tester);
      await tester.enterText(find.byKey(const Key('login-email')), email);
      await tester.enterText(find.byKey(const Key('login-password')), password);
      await tester.enterText(find.byKey(const Key('signup-nickname')), nickname);
      await tester.ensureVisible(find.byKey(const Key('signup-submit')));
      await tester.pump();
      await tester.tap(find.byKey(const Key('signup-submit')));
      // 눌림 애니메이션(340ms) → 가입(Mock 300ms) → _restore() 까지 흘려보낸다.
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pump(const Duration(milliseconds: 500));
    }

    testWidgets('회원가입으로 바꾸면 닉네임 칸과 가입 버튼이 생긴다', (tester) async {
      await tester.pumpWidget(_wrap());
      expect(find.byKey(const Key('signup-nickname')), findsNothing);

      await _tapModeToggle(tester);

      expect(find.byType(TextField), findsNWidgets(3));
      expect(find.byKey(const Key('signup-submit')), findsOneWidget);
      expect(find.byKey(const Key('login-submit')), findsNothing);
    });

    testWidgets('가입하면 곧바로 로그인된다', (tester) async {
      final container = ProviderContainer(overrides: [_authOverride]);
      addTearDown(container.dispose);
      await tester.pumpWidget(UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(home: LoginScreen()),
      ));

      await signUp(tester, email: 'fresh@supersub.test', password: 'password123');

      final state = container.read(sessionControllerProvider);
      expect(state, isA<SessionLoggedIn>());
      expect((state as SessionLoggedIn).user.nickname, '새식구');
    });

    // 🔴 서버도 막지만(422 WEAK_PASSWORD) 보내기 전에 말해 준다 — 규칙은 계약과 같다.
    testWidgets('비밀번호가 8자보다 짧으면 보내지 않고 안내한다', (tester) async {
      final container = ProviderContainer(overrides: [_authOverride]);
      addTearDown(container.dispose);
      await tester.pumpWidget(UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(home: LoginScreen()),
      ));

      // 요청이 안 나가므로 컨트롤러가 안 깨어난다 — 마지막 read 에서 처음 깨어나면
      // Mock 복원(300ms) 타이머가 남아 시험이 실패한다. 먼저 깨워 흘려보낸다.
      container.read(sessionControllerProvider);
      await signUp(tester, email: 'fresh@supersub.test', password: 'short');

      expect(find.text('비밀번호는 8자 이상이어야 합니다'), findsOneWidget);
      expect(container.read(sessionControllerProvider), isNot(isA<SessionLoggedIn>()));
    });

    testWidgets('닉네임이 비어 있으면 보내지 않고 안내한다', (tester) async {
      await tester.pumpWidget(_wrap());
      await signUp(
        tester,
        email: 'fresh@supersub.test',
        password: 'password123',
        nickname: '   ',
      );
      expect(find.text('닉네임을 1~20자로 적어 주세요'), findsOneWidget);
    });

    testWidgets('이미 있는 이메일이면 오류 문구가 뜬다', (tester) async {
      await tester.pumpWidget(_wrap());
      await signUp(tester, email: 'player@supersub.test', password: 'password123');
      expect(find.text('이미 가입된 이메일입니다'), findsOneWidget);
    });

    testWidgets('다시 로그인으로 바꾸면 닉네임 칸이 사라진다', (tester) async {
      await tester.pumpWidget(_wrap());
      await _tapModeToggle(tester);
      await _tapModeToggle(tester);
      expect(find.byType(TextField), findsNWidgets(2));
      expect(find.byKey(const Key('login-submit')), findsOneWidget);
    });
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
