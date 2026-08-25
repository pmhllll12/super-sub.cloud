import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/auth/data/auth_repository.dart';

/// AuthRepository의 모든 구현체가 지켜야 하는 계약.
///
/// 이 파일은 나중에 ApiAuthRepository에 **그대로** 물려 돌린다. 그것이
/// "provider 한 줄 교체"를 실제로 보장하는 장치다(스펙 9.1). 따라서 여기에는
/// 인증 프로토콜의 성질만 둔다 — Mock에만 해당하는 의무(지연 하한 같은 것)나
/// 개발용 편의 기능(loginAs)은 구현체별 테스트 파일로 내린다.
///
/// [build]는 매 테스트마다 깨끗한 구현체를 만들어 돌려준다.
/// [knownEmail]·[knownUserId]는 그 구현체에 존재하는 계정의 이메일과 id다.
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

    test('프로필 수정 결과는 서버가 돌려준 사용자다', () async {
      await repo.login(email: knownEmail, password: 'any');
      final updated = await repo.updateProfile(nickname: '바뀐이름');
      expect(updated.nickname, equals('바뀐이름'));
      // id는 서버 소유라 프로필 수정으로 바뀌지 않는다.
      expect(updated.id, equals(knownUserId));
    });

    test('프로필 수정은 로그아웃·재로그인 후에도 유지된다', () async {
      await repo.login(email: knownEmail, password: 'any');
      await repo.updateProfile(nickname: '바뀐이름');
      await repo.logout();

      final again = await repo.login(email: knownEmail, password: 'any');
      expect(again.user.nickname, equals('바뀐이름'));
    });

    test('로그인하지 않으면 프로필을 수정할 수 없다', () async {
      expect(
        () => repo.updateProfile(nickname: '바뀐이름'),
        throwsA(isA<AuthException>()),
      );
    });

    test('로그아웃하면 세션이 사라진다', () async {
      await repo.login(email: knownEmail, password: 'any');
      await repo.logout();
      expect(await repo.restoreSession(), isNull);
    });

  });
}
