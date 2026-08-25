import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/auth/data/auth_repository.dart';
import 'package:super_sub/features/auth/presentation/session_controller.dart';

void main() {
  late ProviderContainer container;

  setUp(() {
    container = ProviderContainer();
    addTearDown(container.dispose);
  });

  test('처음에는 세션 상태를 모른다', () {
    expect(container.read(sessionControllerProvider), isA<SessionUnknown>());
  });

  test('복원할 세션이 없으면 로그아웃 상태가 된다', () async {
    container.read(sessionControllerProvider);
    await Future<void>.delayed(const Duration(milliseconds: 500));
    expect(container.read(sessionControllerProvider), isA<SessionLoggedOut>());
  });

  test('로그인하면 로그인 상태가 된다', () async {
    await container
        .read(sessionControllerProvider.notifier)
        .login('player@supersub.test', 'any');
    final state = container.read(sessionControllerProvider);
    expect(state, isA<SessionLoggedIn>());
    expect((state as SessionLoggedIn).user.id, equals(MockDb.playerId));
  });

  test('로그인 실패는 AuthException으로 전달되고 상태는 로그아웃이다', () async {
    await expectLater(
      container
          .read(sessionControllerProvider.notifier)
          .login('nobody@nowhere.test', 'any'),
      throwsA(isA<AuthException>()),
    );
    expect(container.read(sessionControllerProvider), isA<SessionLoggedOut>());
  });

  test('loginAs로 팀 관리자로 진입한다', () async {
    await container
        .read(sessionControllerProvider.notifier)
        .loginAs(MockDb.managerId);
    final state = container.read(sessionControllerProvider);
    expect((state as SessionLoggedIn).user.id, equals(MockDb.managerId));
  });

  test('로그아웃하면 로그아웃 상태가 된다', () async {
    final c = container.read(sessionControllerProvider.notifier);
    await c.login('player@supersub.test', 'any');
    await c.logout();
    expect(container.read(sessionControllerProvider), isA<SessionLoggedOut>());
  });
}
