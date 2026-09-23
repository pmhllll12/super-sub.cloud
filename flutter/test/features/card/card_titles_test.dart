import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/card/data/card_repository.dart';
import 'package:super_sub/features/card/data/card_repository_mock.dart';
import 'package:super_sub/features/card/data/models/player_card.dart';

void main() {
  group('CardTitle', () {
    /// 🔴 **여기가 잠재 크래시였다** (2026-09-22). 계약이 2026-09-16 에
    /// `category` 를 `null` 일 수 있게 바꿨는데 앱 모델이 `as String` 으로
    /// 단정하고 있었다 — **직접 적은 호칭을 읽는 순간 그 자리에서 터지고
    /// 카드 화면이 통째로 안 그려진다.**
    test('category 가 null 이어도 읽힌다 — 사람이 적은 호칭이다', () {
      final t = CardTitle.fromJson(const {
        'code': 'custom:abc',
        'label': '시야가 넓은',
        'category': null,
        'granted_at': '2026-09-22T00:00:00Z',
      });

      expect(t.category, isNull);
      expect(t.label, '시야가 넓은');
    });

    test('부여된 호칭은 분류가 있다', () {
      final t = CardTitle.fromJson(const {
        'code': 'sharp_shooter',
        'label': '정확한 슈터',
        'category': '강점',
        'granted_at': '2026-09-22T00:00:00Z',
      });

      expect(t.category, '강점');
    });

    /// 🔴 **가르는 기준은 `code` 다.** `category == null` 로 가르면 옛
    /// 적재분(분류가 없는 부여 호칭)을 「내가 적은 것」으로 읽어 고치기 칸에
    /// 끌어오고, **저장하는 순간 지워 버린다.**
    test('isCustom 은 code 로 가른다 — category 로 가르지 않는다', () {
      CardTitle made(String code, String? category) => CardTitle(
            code: code,
            label: 'x',
            category: category,
            grantedAt: DateTime(2026),
          );

      expect(made('custom:abc', null).isCustom, isTrue);
      expect(made('sharp_shooter', '강점').isCustom, isFalse);
      // 🔴 옛 적재분 — 분류가 없어도 부여된 호칭이다.
      expect(made('sharp_shooter', null).isCustom, isFalse);
    });
  });

  group('호칭 저장', () {
    MockCardRepository build() =>
        MockCardRepository(MockDb(), userId: MockDb.playerId);

    test('적은 호칭이 카드에 남는다', () async {
      final repo = build();

      final card = await repo.updateCard(titles: ['시야가 넓은', '왼발잡이']);

      expect(card.titles.map((t) => t.label), ['시야가 넓은', '왼발잡이']);
      // 사람이 적은 것은 분류를 안 매긴다(계약).
      expect(card.titles.every((t) => t.category == null), isTrue);
      expect(card.titles.every((t) => t.isCustom), isTrue);
    });

    /// 🔴 **부분 병합이 아니다** — 보낸 목록이 그대로 남는다.
    test('다시 보내면 그 목록이 그대로다 — 합치지 않는다', () async {
      final repo = build();

      await repo.updateCard(titles: ['하나', '둘']);
      final card = await repo.updateCard(titles: ['셋']);

      expect(card.titles.map((t) => t.label), ['셋']);
    });

    test('빈 목록을 보내면 전부 지운다', () async {
      final repo = build();

      await repo.updateCard(titles: ['하나']);
      final card = await repo.updateCard(titles: const []);

      expect(card.titles.where((t) => t.isCustom), isEmpty);
    });

    test('안 보내면 안 건드린다', () async {
      final repo = build();

      await repo.updateCard(titles: ['그대로']);
      final card = await repo.updateCard(tagline: '다른 한 줄');

      expect(card.titles.map((t) => t.label), ['그대로']);
    });

    /// 🔴 **부여된 호칭은 사람이 지울 수 있는 값이 아니다.** 여기서 안 지키면
    /// 호칭을 한 번 고칠 때마다 분석이 준 호칭이 말없이 사라진다.
    test('부여된 호칭은 저장으로 사라지지 않는다', () async {
      final db = MockDb();
      // 시드의 내 카드에 부여 호칭 하나를 얹는다.
      final at = db.cards.indexWhere((c) => c.id == 'pc-${MockDb.playerId}');
      final mine = db.cards[at];
      db.cards[at] = PlayerCard(
        id: mine.id,
        publicSlug: mine.publicSlug,
        nickname: mine.nickname,
        titles: [
          CardTitle(
            code: 'sharp_shooter',
            label: '정확한 슈터',
            category: '강점',
            grantedAt: DateTime(2026, 9, 1),
          ),
        ],
      );
      final repo = MockCardRepository(db, userId: MockDb.playerId);

      final card = await repo.updateCard(titles: ['내가 적은 것']);

      expect(card.titles.map((t) => t.label),
          containsAll(['정확한 슈터', '내가 적은 것']));
    });

    /// 🔴 Mock 이 받아 주면 그 오류 화면을 안 만들게 되고, 진짜 서버에서
    /// 처음으로 422 를 본다.
    test('3개를 넘기면 거부한다', () async {
      await expectLater(
        build().updateCard(titles: ['하나', '둘', '셋', '넷']),
        throwsA(anything),
      );
    });

    test('한 개가 20자를 넘기면 거부한다', () async {
      await expectLater(
        build().updateCard(titles: ['가' * (kMaxTitleLen + 1)]),
        throwsA(anything),
      );
    });

    test('딱 20자 · 3개는 통과한다', () async {
      final card = await build().updateCard(
        titles: ['가' * kMaxTitleLen, '나', '다'],
      );

      expect(card.titles.where((t) => t.isCustom), hasLength(3));
    });
  });
}
