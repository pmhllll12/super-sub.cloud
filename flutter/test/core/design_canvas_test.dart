import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/widgets/design_canvas.dart';

/* 🔴 **도면 한 장을 통째로 늘였다 줄인다** (2026-09-29 사용자 요청: 「내
   휴대폰에서 보는 그 비율대로 다른 사용자의 휴대폰에도 비율이 동일하게」).

   ⛔ **화면마다 따로 줄이는 방식으로 되돌리지 말 것** — 그렇게 해 봤더니
   요소마다 비율이 갈려서 사용자가 물렸다(「글자나 버튼 판들이 휴대폰
   길이마다 다 달라져서 별로」). */
void main() {
  group('배율', () {
    test('기준 기기에서는 1 이다', () {
      expect(scaleFor(kDesignSize), closeTo(1, 0.0001));
    });

    /// 🔴 **둘 중 작은 쪽**이라야 다 들어간다 — 큰 쪽을 쓰면 반대편이 잘린다.
    test('세로가 짧으면 세로에 맞춘다', () {
      // 360×640(9:16). 폭 0.876 · 세로 0.718 → 작은 쪽인 세로.
      final s = scaleFor(const Size(360, 640));
      expect(s, closeTo(640 / kDesignSize.height, 0.0001));
      expect(s, lessThan(360 / kDesignSize.width));
    });

    test('폭이 좁으면 폭에 맞춘다', () {
      // 320×1000 — 세로는 남고 폭이 모자라다.
      final s = scaleFor(const Size(320, 1000));
      expect(s, closeTo(320 / kDesignSize.width, 0.0001));
    });

    /// 🔴 **기준보다 크면 키운다**(태블릿) — 안 키우면 둘레가 통째로 빈다.
    test('큰 화면에서는 1 보다 크다', () {
      expect(scaleFor(const Size(822, 1782)), closeTo(2, 0.0001));
    });
  });

  /* 🔴 **안쪽은 자기가 도면 크기라고 믿는다.** 안 갈아 끼우면 `SafeArea` 와
     `MediaQuery.sizeOf` 를 쓰는 화면들이 **실제 기기 값**을 보고 도면과
     어긋난 자리를 잡는다. */
  testWidgets('안쪽이 보는 크기는 늘 도면 크기다', (tester) async {
    tester.view.physicalSize = const Size(720, 1280);
    tester.view.devicePixelRatio = 2;
    addTearDown(tester.view.reset);

    late Size seen;
    await tester.pumpWidget(
      DesignCanvas(
        child: Builder(
          builder: (context) {
            seen = MediaQuery.sizeOf(context);
            return const SizedBox.shrink();
          },
        ),
      ),
    );

    expect(seen, kDesignSize);
  });

  /// 🔴 **상태 바 자리도 도면 좌표로 옮긴다** — 곱하지 말고 나눈다.
  testWidgets('여백도 도면 좌표로 온다', (tester) async {
    tester.view.physicalSize = const Size(720, 1280);
    tester.view.devicePixelRatio = 2;
    // 논리 40 의 상태 바.
    tester.view.padding = const FakeViewPadding(top: 80);
    tester.view.viewPadding = const FakeViewPadding(top: 80);
    addTearDown(tester.view.reset);

    late double top;
    await tester.pumpWidget(
      DesignCanvas(
        child: Builder(
          builder: (context) {
            top = MediaQuery.paddingOf(context).top;
            return const SizedBox.shrink();
          },
        ),
      ),
    );

    // 배율 640/891 로 줄어드니, 도면 좌표에서는 그만큼 **커 보여야** 한다.
    final scale = scaleFor(const Size(360, 640));
    expect(top, closeTo(40 / scale, 0.5));
  });
}
