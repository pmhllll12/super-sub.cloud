import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/auth/data/auth_repository.dart';

/// AuthRepository의 모든 구현체가 지켜야 하는 계약.
///
/// [build]는 매 테스트마다 깨끗한 구현체를 만들어 돌려준다.
/// [knownEmail]은 그 구현체에 존재하는 계정의 이메일이다.
void runAuthRepositoryContract(
  String name,
  AuthRepository Function() build, {
  required String knownEmail,
  required String knownUserId,
}) {
  group('$name — AuthRepository 계약', () {
    late AuthRepository repo;

    setUp(() => repo = build());

    test('등록된 이메일로 로그인하면 세션을 돌려준다', () async {
      final session = await repo.login(email: knownEmail, password: 'any');
      expect(session.user.email, equals(knownEmail));
    });

    test('없는 이메일로 로그인하면 AuthException을 던진다', () async {
      expect(
        () => repo.login(email: 'nobody@nowhere.test', password: 'any'),
        throwsA(isA<AuthException>()),
      );
    });

    test('로그인 전에는 복원할 세션이 없다', () async {
      expect(await repo.restoreSession(), isNull);
    });

    test('로그인 후에는 세션이 복원된다', () async {
      await repo.login(email: knownEmail, password: 'any');
      final restored = await repo.restoreSession();
      expect(restored, isNotNull);
      expect(restored!.user.email, equals(knownEmail));
    });

    test('로그아웃하면 세션이 사라진다', () async {
      await repo.login(email: knownEmail, password: 'any');
      await repo.logout();
      expect(await repo.restoreSession(), isNull);
    });

    test('loginAs로 특정 사용자로 바로 진입한다', () async {
      final session = await repo.loginAs(knownUserId);
      expect(session.user.id, equals(knownUserId));
    });

    test('없는 사용자로 loginAs하면 AuthException을 던진다', () async {
      expect(
        () => repo.loginAs('u-does-not-exist'),
        throwsA(isA<AuthException>()),
      );
    });

    test('응답은 즉시 오지 않는다 (지연이 있다)', () async {
      final sw = Stopwatch()..start();
      await repo.login(email: knownEmail, password: 'any');
      sw.stop();
      expect(sw.elapsedMilliseconds, greaterThanOrEqualTo(100));
    });
  });
}
