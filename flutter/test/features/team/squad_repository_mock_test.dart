import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/core/network/api_client.dart';
import 'package:super_sub/features/team/data/squad_repository_mock.dart';

import '../../contract/squad_repository_contract.dart';

void main() {
  runSquadRepositoryContract(
    'MockSquadRepository',
    () => MockSquadRepository(MockDb(), captainOfTeams: const {'t-thunder'}),
    teamWithSquad: 't-thunder',
    teamWithoutSquad: 't-bears',
    // 시드의 이감독 카드는 이미 등재돼 있으므로, 앉힐 카드는 새로 만든 셈 친다.
    cardIdToEnlist: 'pc-u-player',
    freeSeat: (1, 0), // FW — 시드에서 비어 있다
    takenSeat: (1, 3), // GK — 이감독이 앉아 있다
  );

  group('MockSquadRepository 고유 규칙', () {
    /// 🔴 계약 테스트에 두지 않는다 — Mock 에만 있는 의무다.
    test('응답은 즉시 오지 않는다 (지연이 있다)', () async {
      final sw = Stopwatch()..start();
      await MockSquadRepository(MockDb()).squadOf('t-thunder');

      expect(sw.elapsedMilliseconds, greaterThanOrEqualTo(200));
    });

    /// 🔴 등재는 주장 전용이다. Mock 이 다 받아 주면 목업으로 만든 화면이
    /// 진짜 서버에서 **처음으로** 403 을 만난다.
    test('주장이 아니면 앉히지 못한다', () async {
      final repo = MockSquadRepository(MockDb()); // captainOfTeams 가 비었다
      await expectLater(
        repo.enlist(
          't-thunder',
          playerCardId: 'pc-u-player',
          positionCode: 'FW',
          gridCol: 1,
          gridRow: 0,
        ),
        throwsA(isA<ApiException>().having((e) => e.status, 'status', 403)),
      );
    });

    test('주장이 아니면 자리도 못 옮긴다', () async {
      final repo = MockSquadRepository(MockDb());
      await expectLater(
        repo.moveSeat(
          't-thunder',
          memberId: 'sm-1',
          positionCode: 'MF',
          gridCol: 0,
          gridRow: 1,
        ),
        throwsA(isA<ApiException>().having((e) => e.status, 'status', 403)),
      );
    });

    test('칸이 있는 등재와 없는 등재를 둘 다 시드한다', () async {
      final squad = await MockSquadRepository(MockDb()).squadOf('t-thunder');

      expect(squad!.members.where((m) => m.hasSeat), hasLength(1));
      expect(squad.members.where((m) => !m.hasSeat), hasLength(1));
    });
  });
}
