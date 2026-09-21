import '../../../profile/presentation/widgets/player_card_view.dart'
    show kDefaultCardAlias;

/// 카드에 붙은 호칭.
///
/// 🔴 **받은 것만 그린다** — `earned: false` 같은 미달 표식을 만들지 않는다
/// (웹과 같은 규칙). 호칭은 카드가 아니라 **사람**에 붙어 있어서 카드를 지웠다
/// 다시 만들어도 그대로 실린다.
class CardTitle {
  const CardTitle({
    required this.code,
    required this.label,
    required this.category,
    required this.grantedAt,
  });

  factory CardTitle.fromJson(Map<String, dynamic> json) => CardTitle(
        code: json['code'] as String,
        label: json['label'] as String,
        category: json['category'] as String,
        grantedAt: DateTime.parse(json['granted_at'] as String),
      );

  final String code;
  final String label;
  final String category;
  final DateTime grantedAt;
}

/// 카드 꾸미기. **1단계에서는 원본 맵을 들고만 있는다** — 색·자국·사진을 실제로
/// 그리는 것은 2단계다(`flutter/docs/2026-09-21-카드-스쿼드-서버연결-design.md` 3절).
///
/// 🔴 **그럼에도 지금 필요하다**: 별명 규칙이 「`style` 이 있는가」로 갈린다
/// ([aliasOf]). 2단계까지 미루면 그동안 지운 글자가 되살아난다.
class CardStyle {
  const CardStyle(this.raw);

  factory CardStyle.fromJson(Map<String, dynamic> json) => CardStyle(json);

  /// 🔴 **통째로 들고 있는다.** 필드를 하나씩 풀어 두면 2단계에서 모르는 필드가
  /// 조용히 버려진다 — 서버가 칸을 늘려도 앱은 그대로 실어 나를 수 있어야 한다.
  final Map<String, dynamic> raw;
}

/// `GET /me/card` · `POST /me/card` · `GET /cards/{slug}` 의 응답.
///
/// ⚠️ **공개 응답(`/cards/{slug}`)에는 `id` 가 없다** — 공개해도 되는 것만 담기
/// 때문이다. 그래서 [id] 가 `null` 일 수 있다. 밖으로 나가는 길은 [publicSlug]
/// 하나이고, 그것이 내부 id 를 안 내보내는 원칙이다.
class PlayerCard {
  const PlayerCard({
    required this.publicSlug,
    required this.nickname,
    this.id,
    this.tagline,
    this.style,
    this.photoUrl,
    this.titles = const [],
  });

  factory PlayerCard.fromJson(Map<String, dynamic> json) {
    final user = json['user'] as Map<String, dynamic>?;
    final style = json['style'] as Map<String, dynamic>?;
    return PlayerCard(
      id: json['id'] as String?,
      publicSlug: json['public_slug'] as String,
      nickname: (user?['nickname'] as String?) ?? '',
      tagline: json['tagline'] as String?,
      style: style == null ? null : CardStyle.fromJson(style),
      // 🔴 **그릴 주소는 이것이다** — `style.photo_key` 는 저장용이라 그대로
      //    그릴 수 없다. 이 값은 사전 서명이고 만료가 있다.
      photoUrl: json['photo_url'] as String?,
      titles: ((json['titles'] as List<dynamic>?) ?? const [])
          .map((e) => CardTitle.fromJson(e as Map<String, dynamic>))
          .toList(growable: false),
    );
  }

  final String? id;

  /// 공개 주소이자 **붓자국의 씨앗**이다 — 웹과 같은 무늬가 나오려면 이 값을
  /// `PlayerCardView.seed` 로 넘겨야 한다.
  final String publicSlug;

  final String nickname;
  final String? tagline;
  final CardStyle? style;
  final String? photoUrl;
  final List<CardTitle> titles;
}

/// 카드에 그릴 큰 글자 — 🔴 「비웠다」와 「안 정했다」를 **`style` 유무로** 가른다.
///
/// 서버는 `tagline: null` 과 `"   "` 를 똑같이 「안 정한 상태」로 만들어서
/// `tagline` 만으로는 못 가른다. `style` 이 있다는 것은 **저장을 한 번 거쳤다**는
/// 뜻이고 그때 글자 칸에는 카드에 보이던 값이 들어 있었으니, `style` 이 있는데
/// `tagline` 이 비었으면 **지운 것**이다.
///
/// 🔴 **웹 `aliasOf()` 와 한 글자도 달라지면 안 된다** — 같은 카드가 웹과 앱에서
/// 다른 글자를 이고 있으면 같은 카드로 안 보인다.
///
/// ⚠️ **한 번도 안 꾸민 카드는 자리 표시가 남는다.** 새로 가입한 사람 카드가
/// 갑자기 글자 없이 그려지지 않게 한 것이다.
String aliasOf(PlayerCard card) =>
    card.tagline ?? (card.style != null ? '' : kDefaultCardAlias);
