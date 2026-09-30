import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/card/data/card_repository_mock.dart';

import '../../contract/card_repository_contract.dart';

void main() {
  runCardRepositoryContract(
    'MockCardRepository',
    /* 🔴 **newbieId 가 「카드 없는 사람」이다 (2026-09-21 정정).** 전에는
       playerId 였는데, 목업으로 들어가는 계정이라 카드가 없으면 자동 착석을
       영영 못 봐서 시드를 바꿨다(`MockDb` 주석). 계약의 「없으면 null」은
       이제 newbieId 가 밟는다. */
    () => MockCardRepository(MockDb(), userId: MockDb.newbieId),
    slugWithCard: MockCardRepository.managerCardSlug,
  );

  group('MockCardRepository 고유 규칙', () {
    /// 🔴 계약 테스트에 두지 않는다 — Mock 에만 있는 의무다. API 구현체는
    /// 서버가 빠르면 즉시 올 수 있어 이 조건을 통과할 수 없다.
    test('응답은 즉시 오지 않는다 (지연이 있다)', () async {
      final sw = Stopwatch()..start();
      await MockCardRepository(MockDb(), userId: MockDb.newbieId).myCard();

      expect(sw.elapsedMilliseconds, greaterThanOrEqualTo(200));
    });

    test('시드에 카드가 있는 사람은 처음부터 카드가 있다', () async {
      final repo = MockCardRepository(MockDb(), userId: MockDb.managerId);

      final card = await repo.myCard();

      expect(card, isNotNull);
      expect(card!.publicSlug, MockCardRepository.managerCardSlug);
    });

    test('만든 카드는 공개 슬러그로도 읽힌다', () async {
      final repo = MockCardRepository(MockDb(), userId: MockDb.newbieId);
      final made = await repo.createMyCard();

      expect((await repo.cardBySlug(made.publicSlug))!.publicSlug,
          made.publicSlug);
    });
  });
}
