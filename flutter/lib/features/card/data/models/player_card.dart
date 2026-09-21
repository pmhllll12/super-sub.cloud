import 'dart:ui' show Color;

import '../../../profile/presentation/widgets/player_card_view.dart'
    show kCardBg, kCardFg, kDefaultCardAlias;

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
/// 사진을 어떻게 앉히는가.
enum CardMode {
  /// 사람만 오려낸 그림 — 자르지 않고 카드 바닥에 앉힌다.
  cutout,

  /// 사진이 카드를 덮는다.
  full,
}

/// `#rrggbb` → [Color]. 🔴 **모양이 틀리면 [fallback] 으로 물러난다** —
/// 여기서 던지면 서버가 이상한 값 하나를 준 것으로 **판 전체가 안 뜬다.**
Color colorOrDefault(Object? value, Color fallback) {
  if (value is! String) return fallback;
  final hex = value.startsWith('#') ? value.substring(1) : value;
  if (hex.length != 6) return fallback;
  final n = int.tryParse(hex, radix: 16);
  return n == null ? fallback : Color(0xFF000000 | n);
}

/// 🔴 **자국 번호는 영구 계약이다.** 0 은 절차적 붓자국, 1 은 「없음」,
/// 2~18 은 `assets/marks/01~17.png` — **파일 번호 = `brush` − 1** 이다.
///
/// 🔴 **목록에서 항목을 빼면 그 뒤 번호가 당겨져 남의 카드가 말없이 다른
/// 그림이 된다.** 거둘 때는 자리를 남기고 고르는 칸에서만 숨긴다(웹 `HIDDEN_MARKS`).
///
/// 저장된 값이 목록보다 클 수 있으므로 범위 밖은 `null` 이다 — 아무것도 안 그린다.
String? markAssetFor(int brush) {
  final n = brush - 1;
  if (n < 1 || n > 17) return null;
  return 'assets/marks/${n.toString().padLeft(2, '0')}.png';
}

class CardStyle {
  const CardStyle({
    required this.raw,
    required this.bg,
    required this.logo,
    required this.textColor,
    required this.textX,
    required this.textY,
    required this.brush,
    required this.brushColor,
    required this.brushScale,
    required this.brushX,
    required this.brushY,
    required this.photoScale,
    required this.photoX,
    required this.photoY,
    required this.mode,
  });

  factory CardStyle.fromJson(Map<String, dynamic> json) {
    // 🔴 `num` 이라는 이름을 쓰지 않는다 — Dart 코어 타입과 겹쳐 아래
    //    `v is num` 이 이 함수를 가리키게 된다.
    double dbl(String key, double fallback) {
      final v = json[key];
      return v is num ? v.toDouble() : fallback;
    }

    final textColor = colorOrDefault(json['text_color'], kCardFg);
    return CardStyle(
      raw: json,
      bg: colorOrDefault(json['bg'], kCardBg),
      // 🔴 안 주면 text_color 를 따른다 — 한 값이 여러 곳을 움직인다.
      logo: colorOrDefault(json['logo'], textColor),
      textColor: textColor,
      textX: dbl('text_x', 50),
      textY: dbl('text_y', 34),
      brush: json['brush'] is int ? json['brush'] as int : 0,
      brushColor: colorOrDefault(json['brush_color'], textColor),
      brushScale: dbl('brush_scale', 1),
      brushX: dbl('brush_x', 0),
      brushY: dbl('brush_y', 0),
      photoScale: dbl('photo_scale', 1),
      photoX: dbl('photo_x', 0),
      photoY: dbl('photo_y', 0),
      mode: json['mode'] == 'full' ? CardMode.full : CardMode.cutout,
    );
  }

  /// 🔴 **원본도 들고 있는다** — 서버가 칸을 늘려도 앱이 그대로 실어 나를 수
  /// 있어야 한다(편집기가 생기면 안 읽은 칸까지 되돌려 보내야 한다).
  final Map<String, dynamic> raw;

  final Color bg;

  /// 위 워드마크 색 **하나만** 정한다.
  final Color logo;

  /// 🔴 **별명 + 획 + 머리글(70%) + (logo 없을 때)워드마크 + 기본 붓자국**을
  /// 한꺼번에 정한다. 자리마다 따로 칠하면 반드시 빠지는 곳이 생긴다.
  final Color textColor;

  /// 별명의 **중심** 좌표 — 카드 폭 380 · 높이 519.33 대비 %.
  final double textX;
  final double textY;

  final int brush;
  final Color brushColor;

  /// 🔴 자국 변환은 **translate → scale**, 원점 center.
  final double brushScale;
  final double brushX;
  final double brushY;

  /// 🔴 사진 변환도 translate → scale 이지만 원점이 **center bottom** 이다.
  final double photoScale;
  final double photoX;
  final double photoY;

  final CardMode mode;
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
    this.userId,
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
      // 🔴 **카드 주인의 사용자 id.** 판에서 ⊗ 로 뺄 때 팀에서도 내보내야
      //    하는데(`DELETE /teams/{id}/members/{user_id}`), 판이 들고 있는 것은
      //    카드 슬러그뿐이라 **카드를 한 번 읽어 주인을 알아낸다**(웹과 같다).
      userId: user?['id'] as String?,
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

  /// 카드 주인의 사용자 id. 공개 응답에도 실린다(`user.id`).
  final String? userId;

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
