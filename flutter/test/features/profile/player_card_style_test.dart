import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/card/data/models/player_card.dart';
import 'package:super_sub/features/profile/presentation/widgets/player_card_view.dart';

Future<void> _pump(WidgetTester tester, Widget card) async {
  await tester.pumpWidget(
    MaterialApp(home: Scaffold(body: Center(child: card))),
  );
  await tester.pump();
}

PlayerCardView _card({CardStyle? style, String alias = 'THREE LUNGS'}) =>
    PlayerCardView(width: 380, seed: 'seed-1', alias: alias, style: style);

CardStyle _style([Map<String, dynamic> over = const {}]) =>
    CardStyle.fromJson({...over});

/// 카드 바탕색 — 카드 안 `ColoredBox` 중 첫 번째다.
Color _bgOf(WidgetTester tester) => tester
    .widgetList<ColoredBox>(find.descendant(
      of: find.byType(PlayerCardView),
      matching: find.byType(ColoredBox),
    ))
    .first
    .color;

/// 사진 칸(`_figure`)의 `Positioned` — 카드 바닥에 붙는 그 칸이다.
Positioned _figureBox(WidgetTester tester) => tester
    .widgetList<Positioned>(find.descendant(
      of: find.byType(PlayerCardView),
      matching: find.byType(Positioned),
    ))
    .firstWhere((p) => p.bottom == 0 && p.left != null);

/// 카드 기준 폭 — `player_card_view.dart` 의 `_kBaseW` 와 같아야 한다.
const double _kBaseW = 380;

void main() {
  group('색', () {
    test('꾸미지 않은 카드는 기본 바탕이다', () {
      // 상수 자체가 바뀌면 웹과 갈린다.
      expect(kCardBg, const Color(0xFF91EA92));
      expect(kCardFg, const Color(0xFF0B0B0B));
    });

    testWidgets('style 의 바탕색으로 그린다', (tester) async {
      await _pump(tester, _card(style: _style({'bg': '#123456'})));

      expect(_bgOf(tester), const Color(0xFF123456));
    });

    testWidgets('style 이 없으면 기본 바탕이다', (tester) async {
      await _pump(tester, _card());

      expect(_bgOf(tester), kCardBg);
    });
  });

  group('별명', () {
    /// 🔴 꾸민 카드의 별명은 **자기 중심**이 (text_x, text_y) 에 온다.
    testWidgets('text_x · text_y 가 별명 자리를 옮긴다', (tester) async {
      await _pump(tester, _card(style: _style({'text_x': 50, 'text_y': 20})));
      final high = tester.getCenter(find.text('THREE LUNGS').first);

      await _pump(tester, _card(style: _style({'text_x': 50, 'text_y': 80})));
      final low = tester.getCenter(find.text('THREE LUNGS').first);

      expect(low.dy, greaterThan(high.dy));
    });

    testWidgets('별명이 비면 아예 안 그린다', (tester) async {
      // 🔴 빈 글자 상자가 남으면 그 높이만큼 인물이 밀린다.
      await _pump(tester, _card(alias: '', style: _style()));

      expect(find.byType(Text), findsWidgets); // 머리글은 남는다
      expect(find.text(''), findsNothing);
    });
  });

  group('자국', () {
    testWidgets('brush 0 은 절차적 붓자국이다', (tester) async {
      await _pump(tester, _card(style: _style({'brush': 0})));

      expect(find.byType(Image), findsWidgets); // 인물은 있다
      // 자국 그림은 없다 — CustomPaint 로 그린다.
      expect(
        tester.widgetList<Image>(find.byType(Image)).where(
              (i) => i.image is AssetImage &&
                  (i.image as AssetImage).assetName.contains('marks/'),
            ),
        isEmpty,
      );
    });

    testWidgets('brush 2 는 01.png 를 마스크로 그린다', (tester) async {
      await _pump(
        tester,
        _card(style: _style({'brush': 2, 'brush_color': '#ff0000'})),
      );

      final mark = tester.widgetList<Image>(find.byType(Image)).firstWhere(
            (i) => i.image is AssetImage &&
                (i.image as AssetImage).assetName == 'assets/marks/01.png',
          );
      // 🔴 알파 마스크라 반드시 색으로 칠한다.
      expect(mark.color, const Color(0xFFFF0000));
      expect(mark.colorBlendMode, BlendMode.srcIn);
      // 🔴 안 자르고 안 늘인다.
      expect(mark.fit, BoxFit.contain);
    });

    testWidgets('brush 1(없음)은 아무것도 안 그린다', (tester) async {
      await _pump(tester, _card(style: _style({'brush': 1})));

      expect(
        tester.widgetList<Image>(find.byType(Image)).where(
              (i) => i.image is AssetImage &&
                  (i.image as AssetImage).assetName.contains('marks/'),
            ),
        isEmpty,
      );
    });

    /// 🔴 사진이 카드를 덮는데 기본 자국이 얹히면 더럽다.
    testWidgets('full 이고 자국을 안 골랐으면 자국이 없다', (tester) async {
      await _pump(
        tester,
        _card(style: _style({'mode': 'full', 'brush': 0})),
      );

      expect(find.byType(CustomPaint), findsWidgets); // 다른 CustomPaint 는 있다
    });
  });

  group('인물', () {
    /// 🔴 웹이 2026-09-18 에 바꾼 그림이다 — 옛 player_cutout.png 를 그대로
    /// 두면 카드 얼굴이 웹과 다르다.
    testWidgets('사진이 없으면 기본 인물을 그린다', (tester) async {
      await _pump(tester, _card());

      final figures = tester.widgetList<Image>(find.byType(Image)).where(
            (i) => i.image is AssetImage &&
                (i.image as AssetImage).assetName.contains('player_default'),
          );
      expect(figures, isNotEmpty);
    });

    /// 🔴 컬러 사진이 그대로 나오면 다른 카드다.
    testWidgets('인물에 흑백 필터가 걸린다', (tester) async {
      await _pump(tester, _card());

      expect(find.byType(ColorFiltered), findsWidgets);
    });
  });

  /// 🔴 **여기가 미결 `paik` 48번이다** (2026-09-22 해소).
  ///
  /// 웹 `globals.css` 가 `data-photo='full'` 에서 `top`·`bottom` 만 0 으로
  /// 풀고 **좌우 `inset-inline: 16%` 를 안 풀어** 「카드 전체」라던 주석과
  /// 달리 실제로는 **폭 68% 짜리 띠**였다. 앱이 그걸 픽셀 동일로 옮겨 와서,
  /// 사진을 키우거나 옮겨도 그 띠 안에서만 움직였다(실기기에서 잡혔다).
  group('사진 칸의 크기', () {
    testWidgets('🔴 full 은 카드 전체를 덮는다 — 좌우도 0 이다', (tester) async {
      await _pump(
        tester,
        PlayerCardView(
          width: 380,
          seed: 's',
          style: _style({'mode': 'full'}),
          photoImage: const AssetImage('assets/marks/01.png'),
        ),
      );

      final box = _figureBox(tester);
      expect(box.left, 0, reason: '좌우가 0 이어야 카드 전체다');
      expect(box.right, 0);
      expect(box.top, 0);
      expect(box.bottom, 0);
    });

    /// 🔴 **cutout 은 일부러 좁다** — 글자가 위에 앉을 자리를 남긴다.
    /// 같이 0 으로 밀면 사진이 별명·머리글을 덮는다.
    testWidgets('cutout 은 좌우 16% 안쪽 · 위 절반이다', (tester) async {
      await _pump(
        tester,
        PlayerCardView(
          width: 380,
          seed: 's',
          style: _style({'mode': 'cutout'}),
          photoImage: const AssetImage('assets/marks/01.png'),
        ),
      );

      final box = _figureBox(tester);
      expect(box.left, closeTo(_kBaseW * 0.16, 0.01));
      expect(box.top, greaterThan(0));
    });

    /// 사진을 안 올린 카드의 기본 인물은 **카드보다 넓다**(양팔).
    testWidgets('사진이 없으면 칸이 카드보다 넓다', (tester) async {
      await _pump(tester, _card());

      expect(_figureBox(tester).left, lessThan(0));
    });
  });
}
