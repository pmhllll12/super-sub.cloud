import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/contact_repository_mock.dart';

import '../../contract/contact_repository_contract.dart';

void main() {
  runContactRepositoryContract(
    'MockContactRepository',
    MockContactRepository.new,
    knownNickname: '한박자빠른패스',
    strangerId: 'u-stranger',
    pendingRequestId: 'ct-pending',
    myOwnId: 'u-me',
  );

  group('MockContactRepository 고유 규칙', () {
    /// 🔴 계약 테스트에 두지 않는다 — Mock 에만 있는 의무다.
    test('응답은 즉시 오지 않는다 (지연이 있다)', () async {
      final sw = Stopwatch()..start();
      await MockContactRepository().contacts();

      expect(sw.elapsedMilliseconds, greaterThanOrEqualTo(200));
    });

    /// 🔴 화면이 두 갈래(카드 있는 지인 · 카드 없는 지인)를 다 그려 보게
    /// 시드를 섞는다.
    test('시드에 카드 있는 지인과 없는 지인이 모두 있다', () async {
      final list = await MockContactRepository().contacts();

      expect(list.any((c) => c.cardPublicSlug != null), isTrue);
      expect(list.any((c) => c.cardPublicSlug == null), isTrue);
    });

    /// 🔴 수락한 사람은 **지인 목록으로 옮겨 간다** — 신청 목록에서 사라지는
    /// 것만으로는 화면이 「수락했는데 아무 일도 안 일어났다」로 보인다.
    test('수락하면 지인 목록에 나타난다', () async {
      final repo = MockContactRepository();
      final before = (await repo.contacts()).length;

      await repo.accept('ct-pending');

      expect(await repo.contacts(), hasLength(before + 1));
    });
  });
}
