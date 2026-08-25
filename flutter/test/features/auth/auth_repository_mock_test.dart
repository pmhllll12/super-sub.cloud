import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/auth/data/auth_repository.dart';
import 'package:super_sub/features/auth/data/auth_repository_mock.dart';

import '../../contract/auth_repository_contract.dart';

void main() {
  runAuthRepositoryContract(
    'MockAuthRepository',
    () => MockAuthRepository(MockDb()),
    knownEmail: 'player@supersub.test',
    knownUserId: MockDb.playerId,
  );

  group('MockAuthRepository 고유 규칙', () {
    late MockAuthRepository repo;

    setUp(() => repo = MockAuthRepository(MockDb()));

    // 지연은 인증 프로토콜의 성질이 아니라 Mock의 의무다(스펙 4.3). Mock이
    // 즉시 성공하면 로딩 UI를 만들지 않게 되고 API를 붙이는 날 화면을 다시
    // 짠다. 40ms에 응답하는 실제 API는 옳은 구현이므로 공용 계약에 두면
    // 안 된다.
    test('응답은 즉시 오지 않는다 (지연이 있다)', () async {
      final sw = Stopwatch()..start();
      await repo.login(email: 'player@supersub.test', password: 'any');
      sw.stop();
      expect(sw.elapsedMilliseconds, greaterThanOrEqualTo(100));
    });

    // loginAs는 자격증명 없이 임의의 id로 진입하는 개발용 바로가기다
    // (스펙 5.4, kDebugMode 한정). 운영 구현체가 이것을 제공할 의무는 없고
    // 제공해서도 안 되므로 공용 계약이 아니라 여기서 검증한다.
    test('loginAs로 특정 사용자로 바로 진입한다', () async {
      final session = await repo.loginAs(MockDb.playerId);
      expect(session.user.id, equals(MockDb.playerId));
    });

    test('없는 사용자로 loginAs하면 AuthException을 던진다', () async {
      expect(
        () => repo.loginAs('u-does-not-exist'),
        throwsA(isA<AuthException>()),
      );
    });
  });
}
