import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/invitation_repository_mock.dart';

import '../../contract/invitation_repository_contract.dart';

void main() {
  runInvitationRepositoryContract(
    'MockInvitationRepository',
    MockInvitationRepository.new,
    myTeamId: 't-thunder',
    foreignTeamId: 't-bears',
    userId: 'u-kim',
  );

  group('MockInvitationRepository 고유 규칙', () {
    test('응답은 즉시 오지 않는다 (지연이 있다)', () async {
      final sw = Stopwatch()..start();
      await MockInvitationRepository().invite('t-thunder', userId: 'u-kim');

      expect(sw.elapsedMilliseconds, greaterThanOrEqualTo(200));
    });

    /// 🔴 **자동 수락을 넣지 않는다.** 웹에는 1.5초 뒤 스스로 수락하는 데모
    /// 장치가 있고 주석에 「실제 배포에서는 걷어야 한다」가 달려 있다. 그걸
    /// 옮겨 오면 앱에서도 같은 것을 걷어내야 한다 — 처음부터 안 넣는다.
    test('보낸 초대는 스스로 수락되지 않는다', () async {
      final repo = MockInvitationRepository();
      final inv = await repo.invite('t-thunder', userId: 'u-kim');

      await Future<void>.delayed(const Duration(seconds: 2));

      expect(inv.isPending, isTrue);
    });
  });
}
