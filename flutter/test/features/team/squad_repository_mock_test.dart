import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/team/data/squad_repository_mock.dart';

import '../../contract/squad_repository_contract.dart';

void main() {
  runSquadRepositoryContract(
    'MockSquadRepository',
    () => MockSquadRepository(MockDb()),
    teamWithSquad: 't-thunder',
    teamWithoutSquad: 't-bears',
  );

  group('MockSquadRepository 고유 규칙', () {
    /// 🔴 계약 테스트에 두지 않는다 — Mock 에만 있는 의무다.
    test('응답은 즉시 오지 않는다 (지연이 있다)', () async {
      final sw = Stopwatch()..start();
      await MockSquadRepository(MockDb()).squadOf('t-thunder');

      expect(sw.elapsedMilliseconds, greaterThanOrEqualTo(200));
    });

    test('칸이 있는 등재와 없는 등재를 둘 다 시드한다', () async {
      final squad = await MockSquadRepository(MockDb()).squadOf('t-thunder');

      expect(squad!.members.where((m) => m.hasSeat), hasLength(1));
      expect(squad.members.where((m) => !m.hasSeat), hasLength(1));
    });
  });
}
