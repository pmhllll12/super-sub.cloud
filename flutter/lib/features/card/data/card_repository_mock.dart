import 'dart:math' as math;

import '../../../core/mock/mock_db.dart';
import '../../../core/network/api_client.dart';
import '../../../core/network/upload_file.dart';
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
    List<String>? titles,
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
    /* 🔴 **호칭도 상한을 지킨다** — 3개 · 한 개당 20자. Mock 이 받아 주면
       그 오류 문구를 안 만들게 되고 진짜 서버에서 처음으로 422 를 본다. */
    if (titles != null) {
      if (titles.length > kMaxTitles) {
        throw const ApiException('호칭은 3개까지입니다',
            code: 'VALIDATION_ERROR', status: 422);
      }
      if (titles.any((t) => t.length > kMaxTitleLen)) {
        throw const ApiException('호칭은 한 개당 20자까지입니다',
            code: 'VALIDATION_ERROR', status: 422);
      }
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
      /* 🔴 **보낸 목록이 그대로 남는다** — 부분 병합이 아니다. 빈 목록이면
         직접 적은 것이 전부 지워진다.
         🔴 **부여된 호칭은 건드리지 않는다** — 그건 사람이 지울 수 있는 값이
         아니다(`code` 가 `custom:` 이 아닌 것들). 서버도 같은 자리에서
         가른다. */
      titles: titles == null
          ? card.titles
          : [
              for (final t in card.titles)
                if (!t.isCustom) t,
              for (final label in titles)
                CardTitle(
                  code: 'custom:${label.hashCode.toRadixString(16)}',
                  label: label,
                  // 사람이 적은 글에는 분류를 안 매긴다(계약).
                  category: null,
                  grantedAt: DateTime.now(),
                ),
            ],
    );
    _db.cards[_db.cards.indexOf(card)] = next;
    return next;
  }

  @override
  Future<String> uploadCardPhoto(UploadFile file) async {
    // 두 단계(자리 받기 · S3)를 흉내 내느라 한 박자 더 쉰다.
    await Future<void>.delayed(_delay * 2);

    /* 🔴 **카드가 먼저 있어야 한다** — 저장 키에 카드 id 가 들어가서 서버가
       404 `CARD_NOT_FOUND` 를 낸다. Mock 이 받아 주면 「카드 만들기 전에
       사진부터」 갈래의 오류 문구를 안 만들게 된다. */
    final card = _mine;
    if (card == null) {
      throw const ApiException('카드를 먼저 만들어야 합니다',
          code: 'CARD_NOT_FOUND', status: 404);
    }

    /* 🔴 **받는 형식 셋만**(계약 3-5절). Mock 이 HEIC 를 받아 주면 진짜
       서버에서 처음으로 422 를 본다. */
    final bad = checkCardPhoto(file);
    if (bad != null) {
      throw ApiException(bad, code: 'UNSUPPORTED_PHOTO_TYPE', status: 422);
    }

    /* 🔴 **키만 돌려준다 — 여기서 카드에 붙이지 않는다.** 붙는 것은
       `updateCard(style: …photoKey)` 때다. Mock 이 몰래 붙여 주면 「올리기만
       하고 저장을 안 하면 아무 일도 안 난다」를 앱에서 밟을 수가 없다. */
    return 'cards/photos/$userId/${card.id}-'
        '${math.Random().nextInt(0xFFFFFFF).toRadixString(16)}';
  }

  PlayerCard? get _mine {
    for (final c in _db.cards) {
      if (c.id == _myCardId) return c;
    }
    return null;
  }
}
