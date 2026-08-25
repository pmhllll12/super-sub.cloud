import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/team/data/sport_repository_mock.dart';

import '../../contract/sport_repository_contract.dart';

void main() {
  runSportRepositoryContract(
    'MockSportRepository',
    () => MockSportRepository(MockDb()),
    knownSportCode: 'futsal',
  );

  group('MockSportRepository 고유 규칙', () {
    // 지연은 종목 조회 프로토콜의 성질이 아니라 Mock의 의무다(스펙 4.3).
    test('응답은 즉시 오지 않는다 (지연이 있다)', () async {
      final repo = MockSportRepository(MockDb());
      final sw = Stopwatch()..start();
      await repo.sports();
      sw.stop();
      expect(sw.elapsedMilliseconds, greaterThanOrEqualTo(100));
    });
  });
}
