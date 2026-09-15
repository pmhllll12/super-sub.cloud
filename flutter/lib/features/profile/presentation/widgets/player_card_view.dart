import 'package:flutter/material.dart';

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
/// ⚠️ 아직 옮기지 않은 것: 카드 꾸미기(`card.style` — 색 · 자국 그림 · 사진
/// 자리)와 서버 카드(`GET /me/card`) 연결. 둘 다 붙으면 [alias] · [seed] 를
/// 서버 값으로 넘기면 된다.
class PlayerCardView extends StatelessWidget {
  const PlayerCardView({
    super.key,
    required this.width,
    required this.seed,
    this.alias = kDefaultCardAlias,
  });

  /// 화면에 그려질 폭. 높이는 비율로 정해진다.
  final double width;

  /// 붓자국 모양을 정하는 씨앗. 🔴 웹과 같은 무늬가 나오려면 **카드의
  /// `public_slug`** 를 넘겨야 한다.
  final String seed;

  final String alias;

  @override
  Widget build(BuildContext context) => _ScaledCard(width: width, child: _card());

  Widget _card() {
    return ClipRRect(
      borderRadius: BorderRadius.circular(24),
      child: ColoredBox(
        color: kCardBg,
        child: Stack(
          fit: StackFit.expand,
          children: [
            // 인물 뒤 검은 붓자국.
            CustomPaint(
              painter: PlayerCardBrushPainter(seed: seed, color: kCardFg),
            ),
            // 누끼 인물 — 카드 **아래 절반만**(웹 `.ss-pcard-figure`: 좌우 16%
            // 안쪽, 위는 세로 가운데). 아래로 넘치는 만큼은 카드가 자른다.
            Positioned(
              left: _kBaseW * 0.16,
              right: _kBaseW * 0.16,
              top: _kBaseH / 2,
              bottom: 0,
              child: const ColorFiltered(
                colorFilter: _kGrayscaleContrast,
                child: Image(
                  image: AssetImage('assets/images/player_cutout.png'),
                  fit: BoxFit.cover,
                  alignment: Alignment.topCenter,
                ),
              ),
            ),
            // 글자는 인물보다 위다 — 별명이 어깨와 겹치면 글자가 이긴다.
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 18),
              child: Column(
                children: [
                  const BrandMark(fontSize: 22, color: kCardFg),
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
                  const SizedBox(height: 52),
                  if (alias.isNotEmpty) _Alias(alias),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

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
  const _Alias(this.text);

  final String text;

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
              ..color = kCardFg,
          ),
        ),
        Text(text, textAlign: TextAlign.center, style: _style(color: kCardFg)),
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
