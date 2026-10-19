import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/theme/app_theme.dart';
import 'package:super_sub/core/widgets/aurora_background.dart';

void main() {
  group('AuroraBackground', () {
    testWidgets('바탕색을 깐다', (tester) async {
      // Stack 이 Directionality 를 요구한다.
      await tester.pumpWidget(const Directionality(
        textDirection: TextDirection.ltr,
        child: AuroraBackground(
          base: Color(0xFF123456),
          child: SizedBox.shrink(),
        ),
      ));

      final box = tester.widget<ColoredBox>(
        find
            .descendant(
              of: find.byType(AuroraBackground),
              matching: find.byType(ColoredBox),
            )
            .first,
      );
      expect(box.color, const Color(0xFF123456));
    });

    /// 🔴 **색이 갈리면 다시 칠해야 한다.** `shouldRepaint` 가 붙박이로
    /// `false` 를 돌려주던 자리라, 안 고쳤으면 **프로필 배경이 영영 첫 색에
    /// 멈춘다.**
    testWidgets('색이 바뀌면 다시 칠한다', (tester) async {
      Future<CustomPainter> painterWith(({Color a, Color b})? tint) async {
        await tester.pumpWidget(Directionality(
          textDirection: TextDirection.ltr,
          child: AuroraBackground(
            tint: tint,
            child: const SizedBox.shrink(),
          ),
        ));
        return tester
            .widget<CustomPaint>(find
                .descendant(
                  of: find.byType(AuroraBackground),
                  matching: find.byType(CustomPaint),
                )
                .first)
            .painter!;
      }

      final first = await painterWith(
        (a: const Color(0xFFFF0000), b: const Color(0xFF00FF00)),
      );
      final second = await painterWith(
        (a: const Color(0xFF0000FF), b: const Color(0xFF00FF00)),
      );

      /* 🔴 **빛무리를 끈 동안에는 다시 칠할 것이 없다**(`kAuroraGlow`).
         켜면 색이 갈릴 때 다시 칠해야 한다 — 안 그러면 배경이 영영 첫 색에
         멈춘다. 스위치를 되돌리면 이 시험이 그것을 붙든다. */
      expect(second.shouldRepaint(first), kAuroraGlow);
      expect(second.shouldRepaint(second), isFalse);
    });

    test('기본 색 둘은 브랜드 민트와 진한 청이다', () {
      // 상수가 바뀌면 카드 없는 프로필이 홈과 달라 보인다.
      expect(kDefaultAuroraTint.a, AppTheme.seed);
      expect(kDefaultAuroraTint.b, const Color(0xFF1B7A8C));
    });
  });

  group('AnimatedAuroraBackground', () {
    /// 🔴 **두 번째로 바꿀 때 기본색으로 튕기면 안 된다.** 직접 `0→1` 을
    /// 감으면서 앞 색을 고정값으로 잡으면 그렇게 된다 — `ColorTween` 이
    /// 그리고 있던 값에서 이어 준다.
    testWidgets('색이 바뀌면 곧바로 목표색이 아니다 — 건너간다', (tester) async {
      Color paintedA() => ((tester
              .widget<CustomPaint>(find
                  .descendant(
                    of: find.byType(AuroraBackground),
                    matching: find.byType(CustomPaint),
                  )
                  .first)
              .painter!) as dynamic)
          .tint
          .a as Color;

      Future<void> show(Color a) => tester.pumpWidget(MaterialApp(
            home: AnimatedAuroraBackground(
              tint: (a: a, b: const Color(0xFF00FF00)),
              child: const SizedBox.shrink(),
            ),
          ));

      await show(const Color(0xFFFF0000));
      // 첫 프레임은 목표색 그대로다(건너갈 앞 색이 없다).
      await tester.pump(const Duration(seconds: 2));
      expect(paintedA(), const Color(0xFFFF0000));

      await show(const Color(0xFF0000FF));
      await tester.pump(const Duration(milliseconds: 200));

      // 200ms 에는 아직 도착하지 않았다 — 그게 「부드럽게」다.
      expect(paintedA(), isNot(const Color(0xFF0000FF)));

      await tester.pump(const Duration(seconds: 2));
      expect(paintedA(), const Color(0xFF0000FF));
    });
  });
}
