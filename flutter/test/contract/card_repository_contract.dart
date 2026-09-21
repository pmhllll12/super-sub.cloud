import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/card/data/card_repository.dart';

/// CardRepository 의 모든 구현체가 지켜야 하는 계약.
///
/// 🔴 **여기에는 프로토콜의 성질만 둔다.** Mock 에만 있는 의무(지연 하한)는
/// 구현체별 테스트 파일로 내린다 — 계약에 섞으면 API 구현체가 통과할 수 없는
/// 조건이 된다(`flutter/CLAUDE.md`).
///
/// 같은 파일을 Mock 과 API 에 **둘 다** 물려 돌린다. 그것이 "provider 한 줄
/// 교체"가 진짜라는 유일한 보증이다.
///
/// [build] 는 매 테스트마다 깨끗한 구현체를 만든다.
/// [slugWithCard] 는 그 구현체에 **실제로 존재하는** 카드의 공개 슬러그다.
void runCardRepositoryContract(
  String name,
  CardRepository Function() build, {
  required String slugWithCard,
}) {
  group('$name — CardRepository 계약', () {
    late CardRepository repo;

    setUp(() => repo = build());

    /// 🔴 **이것이 이 계약의 핵심이다.** 404 `CARD_NOT_FOUND` 는 오류가 아니라
    /// 「아직 안 만들었다」이고, 화면은 그때 빈 카드를 그린다. 예외로 올리면
    /// 화면마다 try/catch 로 정상 상태를 가려내야 하고, 그러면 진짜 오류
    /// (네트워크·401)와 구분이 사라진다.
    test('카드가 없으면 예외가 아니라 null 이다', () async {
      expect(await repo.myCard(), isNull);
    });

    test('만들면 카드가 생기고 슬러그가 있다', () async {
      final card = await repo.createMyCard();

      expect(card.publicSlug, isNotEmpty);
      expect(await repo.myCard(), isNotNull);
    });

    /// 🔴 이미 공유한 주소가 죽으면 안 된다 — 네트워크가 끊겨 재시도해도
    /// 공유 링크가 바뀌지 않아야 한다(계약 `POST /me/card`).
    test('두 번 만들어도 슬러그가 안 바뀐다 — 멱등', () async {
      final first = await repo.createMyCard();
      final second = await repo.createMyCard();

      expect(second.publicSlug, equals(first.publicSlug));
    });

    test('만든 직후에는 호칭이 비어 있다', () async {
      // 만든 직후에는 부여된 것도 적은 것도 없다(계약).
      expect((await repo.createMyCard()).titles, isEmpty);
    });

    test('남의 카드를 공개 슬러그로 읽는다', () async {
      final card = await repo.cardBySlug(slugWithCard);

      expect(card, isNotNull);
      expect(card!.publicSlug, equals(slugWithCard));
    });

    test('없는 슬러그는 null 이다', () async {
      expect(await repo.cardBySlug('no-such-slug-0000'), isNull);
    });
  });
}
