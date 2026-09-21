import 'dart:math' as math;

import '../../../core/mock/mock_db.dart';
import '../../../core/network/api_client.dart';
import 'card_repository.dart';
import 'models/player_card.dart';

/// 백엔드 없이 도는 카드 저장소.
///
/// 🔴 **시드에서 로그인한 사람의 카드를 안 만든다** — 「카드 없음」 빈 상태를
/// 반드시 만들게 하는 장치다(`MockDb` 가 신규 가입자에게 소속을 안 넣은 것과
/// 같은 이유). 만들려면 화면에서 실제로 [createMyCard] 를 밟아야 한다.
class MockCardRepository implements CardRepository {
  MockCardRepository(this._db, {required this.userId});

  final MockDb _db;

  /// 지금 로그인한 사람 — 「내 카드」가 누구 것인지 가른다.
  final String userId;

  /// 계약 테스트가 「있는 카드」로 쓰는 슬러그(시드의 이감독 카드).
  static const managerCardSlug = 'lee-gamdok-7f21';

  static const _delay = Duration(milliseconds: 300);

  String get _myCardId => 'pc-$userId';

  @override
  Future<PlayerCard?> myCard() async {
    // 🔴 Mock 이 즉시 성공하면 로딩 UI 를 안 만들게 되고, API 를 붙이는 날
    //    화면을 다시 짠다. 다른 Mock 과 같은 지연을 쓴다.
    await Future<void>.delayed(_delay);
    return _mine;
  }

  @override
  Future<PlayerCard> createMyCard() async {
    await Future<void>.delayed(_delay);
    // 🔴 **멱등이다** — 이미 있으면 있는 것을 그대로 돌려준다. 새 슬러그를
    //    뽑으면 이미 공유한 주소가 죽는다.
    final existing = _mine;
    if (existing != null) return existing;
    final card = PlayerCard(
      id: _myCardId,
      // 🔴 슬러그를 닉네임에서 유도하지 않는다(SEC-005) — 유도하면 이름만
      //    알고 남의 카드 주소를 맞힐 수 있다. 여기서도 같은 성질을 흉내 낸다.
      publicSlug: 'card-${math.Random().nextInt(0xFFFFFF).toRadixString(16)}',
      nickname: _db.findUserById(userId)?.nickname ?? '',
      // 만든 직후에는 호칭도 꾸밈도 없다(계약).
    );
    _db.cards.add(card);
    return card;
  }

  @override
  Future<PlayerCard?> cardBySlug(String slug) async {
    await Future<void>.delayed(_delay);
    for (final c in _db.cards) {
      if (c.publicSlug == slug) return c;
    }
    return null;
  }

  @override
  Future<PlayerCard> updateCard({
    String? tagline,
    bool clearTagline = false,
    CardStyle? style,
  }) async {
    await Future<void>.delayed(_delay);
    final card = _mine;
    if (card == null) {
      throw const ApiException('카드가 없습니다',
          code: 'CARD_NOT_FOUND', status: 404);
    }
    /* 🔴 **20자까지다** — 넘으면 서버가 422 다. Mock 이 받아 주면 그 화면을
       안 만들게 되고, 진짜 서버에서 처음으로 막힌다. */
    if (tagline != null && tagline.length > 20) {
      throw const ApiException('한 줄은 20자까지입니다',
          code: 'VALIDATION_ERROR', status: 422);
    }
    final next = PlayerCard(
      id: card.id,
      userId: card.userId,
      publicSlug: card.publicSlug,
      nickname: card.nickname,
      // 보낸 것만 바뀐다.
      tagline: clearTagline ? null : (tagline ?? card.tagline),
      style: style ?? card.style,
      photoUrl: card.photoUrl,
      titles: card.titles,
    );
    _db.cards[_db.cards.indexOf(card)] = next;
    return next;
  }

  PlayerCard? get _mine {
    for (final c in _db.cards) {
      if (c.id == _myCardId) return c;
    }
    return null;
  }
}
