import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/widgets/ink_bleed.dart';

void main() {
  group('inkProgress', () {
    test('순백 구간에서는 0이다', () {
      expect(inkProgress(0), 0);
      expect(inkProgress(0.06), 0);
    });

    test('머묾 구간에서는 1이다', () {
      expect(inkProgress(0.84), 1);
      expect(inkProgress(1.0), 1);
    });

    test('번짐 구간에서 단조 증가한다', () {
      var prev = -1.0;
      for (var i = 0; i <= 100; i++) {
        final p = inkProgress(i / 100);
        expect(p, greaterThanOrEqualTo(prev), reason: 't=${i / 100}에서 뒷걸음');
        prev = p;
      }
    });

    test('번짐 절반 지점에 65%가 젖는다', () {
      // 참조 영상에서 잰 값이다. 선형(50%)도 easeOutCubic(88%)도 아니다.
      const dry = 0.20 / 3.1;
      const wet = 2.60 / 3.1;
      expect(inkProgress(dry + (wet - dry) * 0.5), closeTo(0.65, 0.005));
    });

    test('p=0.60이 1.28초 언저리다', () {
      // 글리치가 여기서 시작한다. 너무 이르면 글자가 아직 안 읽히고,
      // 너무 늦으면 머묾 구간을 침범한다. 3100은 kIntroDuration과 묶여 있다.
      var hit = -1.0;
      for (var i = 0; i <= 3100; i++) {
        if (inkProgress(i / 3100) >= 0.60) {
          hit = i / 1000;
          break;
        }
      }
      expect(hit, closeTo(1.28, 0.06));
    });
  });

  group('InkPeel.split', () {
    test('덮는 구간이 없으면 처음부터 다 덮여 있다', () {
      final s = InkPeel.split(0, 0);
      expect(s.cover, 1);
      expect(s.peeled, 0);
    });

    test('덮는 구간이 있으면 그 안에서 덮이고 그 뒤에 걷힌다', () {
      expect(InkPeel.split(0.1, 0.2).cover, closeTo(0.5, 1e-9));
      expect(InkPeel.split(0.1, 0.2).peeled, 0);
      expect(InkPeel.split(0.6, 0.2).cover, 1);
      expect(InkPeel.split(0.6, 0.2).peeled, closeTo(0.5, 1e-9));
    });
  });

  testWidgets('셰이더가 없어도 페인터가 안 터진다', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: CustomPaint(
          painter: InkBleedPainter(
            progress: 0.5,
            seed: 3,
            ink: Color(0xFF0E2A14),
          ),
          child: SizedBox(width: 100, height: 200),
        ),
      ),
    );
    expect(tester.takeException(), isNull);
  });
}
