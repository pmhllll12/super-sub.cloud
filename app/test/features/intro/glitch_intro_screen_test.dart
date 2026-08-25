import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/widgets/ink_bleed.dart';
import 'package:super_sub/features/intro/presentation/screens/glitch_intro_screen.dart';

void main() {
  testWidgets('첫 프레임부터 로고가 바탕과 다른 색으로 떠 있다', (tester) async {
    await tester.pumpWidget(
      MaterialApp(home: GlitchIntroScreen(onDone: () {})),
    );
    await tester.pump();

    final scaffold = tester.widget<Scaffold>(find.byType(Scaffold));
    expect(scaffold.backgroundColor, kIntroPaper);

    final text = tester.widget<Text>(find.text('SUPERSUB').first);
    // 로고는 한순간도 사라지면 안 된다 — 바탕색과 같으면 잉크가 덮기 전까지
    // 보이지 않는다.
    expect(text.style?.color, kIntroInk);
    expect(kIntroInk, isNot(kIntroPaper));

    // 컨트롤러가 아직 돌고 있다 — 끝까지 흘려보내야 티커가 안 남는다.
    await tester.pump(const Duration(milliseconds: 3200));
  });

  testWidgets('잉크 페인터가 화면에 있다', (tester) async {
    await tester.pumpWidget(
      MaterialApp(home: GlitchIntroScreen(onDone: () {})),
    );
    await tester.pump();

    final painters = tester
        .widgetList<CustomPaint>(find.byType(CustomPaint))
        .map((w) => w.painter);
    expect(painters, contains(isA<InkBleedPainter>()));

    await tester.pump(const Duration(milliseconds: 3200));
  });

  testWidgets('다 흐르면 onDone이 불린다', (tester) async {
    var done = false;
    await tester.pumpWidget(
      MaterialApp(home: GlitchIntroScreen(onDone: () => done = true)),
    );
    await tester.pump();
    expect(done, isFalse);

    await tester.pump(const Duration(milliseconds: 3200));
    expect(done, isTrue);
  });

  group('글리치 창', () {
    test('잉크가 6할 젖기 전에는 흔들리지 않는다', () {
      for (var i = 0; i <= 60; i++) {
        expect(glitchAmplitudeAt(i / 100), 0, reason: 'p=${i / 100}');
      }
    });

    test('잉크가 다 젖은 뒤에는 흔들리지 않는다', () {
      for (var i = 95; i <= 100; i++) {
        expect(glitchAmplitudeAt(i / 100), 0, reason: 'p=${i / 100}');
      }
    });

    test('창 안에서는 흔들리는 구간이 있다', () {
      var maxAmp = 0.0;
      for (var i = 60; i <= 95; i++) {
        final a = glitchAmplitudeAt(i / 100);
        if (a > maxAmp) maxAmp = a;
      }
      expect(maxAmp, greaterThan(0.5));
    });

    test('버스트 사이에 정적이 있다', () {
      // 내내 흔들면 눈이 적응해 아무 일도 안 일어나는 것처럼 보인다.
      var quiet = 0;
      for (var i = 60; i <= 95; i++) {
        if (glitchAmplitudeAt(i / 100) == 0) quiet++;
      }
      expect(quiet, greaterThan(5));
    });
  });
}
