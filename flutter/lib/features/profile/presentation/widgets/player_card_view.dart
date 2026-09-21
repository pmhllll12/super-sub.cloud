import 'package:flutter/material.dart';

import '../../../card/data/models/player_card.dart';
import '../../../intro/presentation/brand_mark.dart';
import 'player_card_brush.dart';

/// 카드를 안 꾸몄을 때 가운데 큰 글자. 웹 `PlayerCardView.tsx` 의 `ALIAS` 와 같다.
const String kDefaultCardAlias = 'THREE LUNGS';

/// 카드 바탕 · 글자색 — 웹 `.ss-pcard` 의 `--ss-pcard-bg` · `--ss-pcard-fg`.
///
/// 🔴 앱 전체가 어두운데 카드만 밝다. 의도한 것이다 — 카드는 밖으로 공유되는
/// 물건이라 어디에 놓여도 같은 얼굴이어야 한다(웹과 같은 판단).
const Color kCardBg = Color(0xFF91EA92);
const Color kCardFg = Color(0xFF0B0B0B);

/// 웹 카드가 제 크기로 그려질 때의 폭(`--ss-pcard-base-w`). 비율은 3 : 4.1.
const double _kBaseW = 380;
const double _kBaseH = _kBaseW * 4.1 / 3;

/// 세로 포스터형 선수 카드 — 웹 `PlayerCardView` 의 **꾸미지 않은 기본 모습**을
/// 옮긴 것이다. 워드마크 · PLAYER CARD · 큰 별명 · 붓자국 · 흑백 누끼 인물.
///
/// **제 크기(380)로 짠 뒤 통째로 줄인다**(`FittedBox`). 웹의 작은 카드
/// (`.ss-pcard-mini`)가 transform 으로 줄이는 것과 같은 이유다 — 폭만 줄이면
/// 안쪽 글자가 제 크기로 남아 짜임이 깨진다.
///
/// 🔴 **수치를 그리지 않는다**(부록 D.5) — 점수 · 등급 · 진행률을 여기 넣지 않는다.
///
/// [style] 을 주면 꾸민 모습으로 그린다(색 · 별명 자리 · 자국 · 사진).
/// `null` 이면 **한 번도 안 꾸민 카드**의 기본 모습이다.
class PlayerCardView extends StatelessWidget {
  const PlayerCardView({
    super.key,
    required this.width,
    required this.seed,
    this.alias = kDefaultCardAlias,
    this.style,
    this.photoUrl,
  });

  /// 화면에 그려질 폭. 높이는 비율로 정해진다.
  final double width;

  /// 붓자국 모양을 정하는 씨앗. 🔴 웹과 같은 무늬가 나오려면 **카드의
  /// `public_slug`** 를 넘겨야 한다.
  final String seed;

  final String alias;

  /// 꾸미기. `null` 이면 한 번도 안 꾸민 카드다.
  final CardStyle? style;

  /// 🔴 **그릴 사진 주소** — `style.photo_key` 가 아니라 응답의 `photo_url`
  /// 이다(사전 서명이고 만료가 있다).
  final String? photoUrl;

  Color get _bg => style?.bg ?? kCardBg;
  Color get _fg => style?.textColor ?? kCardFg;

  @override
  Widget build(BuildContext context) => _ScaledCard(width: width, child: _card());

  Widget _card() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(24),
      child: ColoredBox(
        color: _bg,
        child: Stack(
          fit: StackFit.expand,
          children: [
            _mark(),
            _figure(),
            // 글자는 인물보다 위다 — 별명이 어깨와 겹치면 글자가 이긴다.
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 18),
              child: Column(
                children: [
                  BrandMark(fontSize: 22, color: style?.logo ?? kCardFg),
                  const SizedBox(height: 12),
                  Text(
                    'PLAYER CARD',
                    style: TextStyle(
                      fontFamily: 'YoungSerif',
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 11 * 0.14,
                      color: _fg.withValues(alpha: 0.7),
                    ),
                  ),
                  // 🔴 꾸미지 않은 카드만 흐름 배치다 — 꾸민 카드의 별명은
                  //    아래 _alias() 가 절대 좌표로 놓는다.
                  if (style == null) ...[
                    const SizedBox(height: 52),
                    if (alias.isNotEmpty) _Alias(alias, color: _fg),
                  ],
                ],
              ),
            ),
            if (style != null && alias.isNotEmpty) _alias(),
          ],
        ),
      ),
    );
  }

  /// 인물 뒤 자국 — 절차적 붓자국(0) · 없음(1) · 그림(2~18).
  Widget _mark() {
    final s = style;
    if (s == null) {
      // 안 꾸민 카드는 절차적 붓자국을 **그대로, 아무 변형 없이** 그린다.
      return CustomPaint(
        painter: PlayerCardBrushPainter(seed: seed, color: kCardFg),
      );
    }
    /* 🔴 **사진이 카드를 덮는데 기본 자국이 얹히면 더럽다** — full 이고
       고르지 않은 자국(0)이면 아무것도 안 그린다. 사람이 **고른** 자국은
       full 에서도 그린다(웹과 같은 규칙). */
    if (s.mode == CardMode.full && s.brush == 0) return const SizedBox.shrink();

    final Widget? drawn = switch (s.brush) {
      0 => CustomPaint(
          painter: PlayerCardBrushPainter(seed: seed, color: s.brushColor),
        ),
      _ => switch (markAssetFor(s.brush)) {
          final String asset => Image.asset(
              asset,
              // 🔴 **PNG 는 그림이 아니라 알파 마스크다**(8-bit gray+alpha).
              //    반드시 brush_color 로 칠한다.
              color: s.brushColor,
              colorBlendMode: BlendMode.srcIn,
              // 🔴 안 자르고 안 늘인다 — 가운데 맞춤.
              fit: BoxFit.contain,
            ),
          _ => null,
        },
    };
    if (drawn == null) return const SizedBox.shrink();

    /* 🔴 **translate → scale 이고 원점은 가운데다.** translate 의 %는 카드
       크기 기준이며 **배율에 곱해지지 않는다** — 순서를 뒤집으면 자국이
       엉뚱한 데로 간다. */
    return Transform.translate(
      offset: Offset(_kBaseW * s.brushX / 100, _kBaseH * s.brushY / 100),
      child: Transform.scale(scale: s.brushScale, child: drawn),
    );
  }

  /// 사진 또는 기본 인물.
  Widget _figure() {
    final s = style;
    final photo = photoUrl;
    final image = photo == null
        ? const AssetImage(_kDefaultFigure) as ImageProvider
        : NetworkImage(photo);
    final full = s?.mode == CardMode.full;

    /* **사진 없음 + cutout** — 칸이 좌우로 25%씩 넘어가고(폭 150%), 위는 38%,
       그림은 자르지 않고(`contain`) 카드 바닥에 앉는다. 넘친 팔 끝은 카드가
       자른다. 사진이 있으면 좌우 16% 안쪽 · 위 50% · `cover` 다. */
    final bare = photo == null && !full;
    final left = bare ? -_kBaseW * 0.25 : _kBaseW * 0.16;
    final right = left;
    final top = full
        ? 0.0
        : bare
            ? _kBaseH * 0.38
            : _kBaseH / 2;

    return Positioned(
      left: left,
      right: right,
      top: top,
      bottom: 0,
      child: ClipRect(
        child: ColorFiltered(
          colorFilter: _kGrayscaleContrast,
          /* 🔴 **변환은 칸이 아니라 그림에만 건다.** 칸에 걸면 잘리는 범위까지
             움직여 카드 밖으로 넘친다. 원점은 **아래 가운데**다. */
          child: Transform.translate(
            offset: Offset(
              (s?.photoX ?? 0) / 100 * (_kBaseW - left * 2),
              (s?.photoY ?? 0) / 100 * (_kBaseH - top),
            ),
            child: Transform.scale(
              scale: s?.photoScale ?? 1,
              alignment: Alignment.bottomCenter,
              child: Image(
                image: image,
                fit: bare ? BoxFit.contain : BoxFit.cover,
                alignment:
                    bare ? Alignment.bottomCenter : Alignment.topCenter,
                // 사진이 안 오면 카드가 깨지지 않게 조용히 비운다.
                errorBuilder: (_, _, _) => const SizedBox.shrink(),
              ),
            ),
          ),
        ),
      ),
    );
  }

  /// 꾸민 카드의 별명 — **자기 중심**이 (`text_x`, `text_y`) 에 온다.
  Widget _alias() {
    final s = style!;
    return Positioned(
      left: _kBaseW * s.textX / 100,
      top: _kBaseH * s.textY / 100,
      child: FractionalTranslation(
        translation: const Offset(-0.5, -0.5),
        child: ConstrainedBox(
          // 웹 `max-width: 86%`.
          constraints: const BoxConstraints(maxWidth: _kBaseW * 0.86),
          child: _Alias(alias, color: s.textColor),
        ),
      ),
    );
  }
}

/// 사진을 안 올린 카드에 그리는 기본 인물.
///
/// 🔴 **웹이 2026-09-18 에 바꾼 그림이다**(얼굴 가운데 · 양팔 · 워터마크 없음).
/// 옛 `player_cutout.png` 를 그대로 두면 **카드 얼굴이 웹과 다르다.**
const String _kDefaultFigure = 'assets/images/player_default.webp';

/// 웹 `filter: grayscale(1) contrast(1.06)`.
const ColorFilter _kGrayscaleContrast = ColorFilter.matrix(<double>[
  0.2126 * 1.06, 0.7152 * 1.06, 0.0722 * 1.06, 0, -0.03 * 255, //
  0.2126 * 1.06, 0.7152 * 1.06, 0.0722 * 1.06, 0, -0.03 * 255, //
  0.2126 * 1.06, 0.7152 * 1.06, 0.0722 * 1.06, 0, -0.03 * 255, //
  0, 0, 0, 1, 0,
]);

/// 가운데 큰 별명. 웹처럼 **같은 색 테두리를 글자 아래에 덧그려** 획을 불린다
/// (`-webkit-text-stroke: 1.5px` + `paint-order: stroke fill`) — Young Serif 는
/// 굵기가 하나뿐이라 가짜 굵게 대신 이렇게 무게를 얹는다.
class _Alias extends StatelessWidget {
  const _Alias(this.text, {this.color = kCardFg});

  final String text;
  final Color color;

  // 웹 `clamp(1.75rem, 15cqw, 3.25rem)` — 안쪽 폭 344 의 15% = 51.6.
  static const double _size = (_kBaseW - 36) * 0.15;

  TextStyle _style({Paint? foreground, Color? color}) => TextStyle(
        fontFamily: 'YoungSerif',
        fontSize: _size,
        height: 1.02,
        letterSpacing: _size * -0.01,
        foreground: foreground,
        color: color,
      );

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Text(
          text,
          textAlign: TextAlign.center,
          style: _style(
            foreground: Paint()
              ..style = PaintingStyle.stroke
              ..strokeWidth = 1.5
              ..strokeJoin = StrokeJoin.round
              ..color = color,
          ),
        ),
        Text(text, textAlign: TextAlign.center, style: _style(color: color)),
      ],
    );
  }
}

/// 카드 한 장을 **제 크기(380)로 짠 뒤 [width] 로 통째로 줄인다.** 채워진 카드와
/// 빈 카드가 같은 틀을 쓴다 — 따로 줄이면 둘의 비율 · 모서리가 따로 늙는다.
class _ScaledCard extends StatelessWidget {
  const _ScaledCard({required this.width, required this.child});

  final double width;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: width,
      height: width * _kBaseH / _kBaseW,
      // 기기 글자 크기 설정이 카드 안까지 번지면 짜임이 깨진다 — 카드는 그림이다.
      child: MediaQuery.withNoTextScaling(
        child: FittedBox(
          child: SizedBox(width: _kBaseW, height: _kBaseH, child: child),
        ),
      ),
    );
  }
}

/// 아직 사람이 안 들어간 카드의 틀 — 웹 `BlankPlayerCard.tsx`. 흰 바탕에
/// 머리글(SUPERSUB · PLAYER CARD)만 있고 가운데는 [child] 자리다(스쿼드 판의
/// 빈 자리는 `+`).
///
/// 워드마크는 **브랜드 민트**다 — 바탕이 희어서 검게 찍을 이유가 없다(채워진
/// 카드는 연두 바탕이라 반대로 검정). 웹과 같은 판단이다.
class BlankPlayerCardView extends StatelessWidget {
  const BlankPlayerCardView({super.key, required this.width, this.child});

  final double width;

  /// 제 크기(380 폭) 기준으로 짠 가운데 내용.
  final Widget? child;

  @override
  Widget build(BuildContext context) {
    return _ScaledCard(
      width: width,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: ColoredBox(
          color: const Color(0xFFFFFFFF),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 18),
            child: Column(
              children: [
                const BrandMark(fontSize: 22),
                const SizedBox(height: 12),
                Text(
                  'PLAYER CARD',
                  style: TextStyle(
                    fontFamily: 'YoungSerif',
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 11 * 0.14,
                    color: kCardFg.withValues(alpha: 0.7),
                  ),
                ),
                Expanded(child: Center(child: child)),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
