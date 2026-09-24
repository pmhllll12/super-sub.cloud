import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/widgets/floating_nav_bar.dart';

/* 하단 바 — 2026-09-23 사용자 요청으로 **한 덩이 둥근 막대**가 됐다.
   전에는 윗변에서 로고 자리만 파낸 한 장(`_LogoNotch`)에 `SUPERSUB` 알약이
   **따로 떠 있었다.** 그 둘을 합친 것이 이 파일이 지키는 성질이다. */

Future<void> _pump(WidgetTester tester, {List<int>? taps}) async {
  tester.view.physicalSize = const Size(1080, 2340);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        bottomNavigationBar: FloatingNavBar(
          currentIndex: 0,
          onTap: (i) => taps?.add(i),
        ),
      ),
    ),
  );
}

Finder _bar() => find.byKey(const Key('navbar-bar'));

void main() {
  testWidgets('로고와 아이콘이 모두 한 막대 안에 있다', (tester) async {
    await _pump(tester);
    final bar = tester.getRect(_bar());

    for (final key in const [
      'navbar-icon-0',
      'navbar-icon-1',
      'navbar-icon-2',
      'navbar-icon-3',
      'navbar-icon-menu',
    ]) {
      final r = tester.getRect(find.byKey(Key(key)));
      expect(bar.top, lessThanOrEqualTo(r.top), reason: '$key 윗변');
      expect(bar.bottom, greaterThanOrEqualTo(r.bottom), reason: '$key 아랫변');
      expect(bar.left, lessThanOrEqualTo(r.left), reason: '$key 왼변');
      expect(bar.right, greaterThanOrEqualTo(r.right), reason: '$key 오른변');
    }
  });

  /* 🔴 **화면 양끝까지 안 간다**(사용자 요청: 「이 하단바는 양쪽 끝까지 굳이
     안 가도 됨」). 옛 바는 **일부러 화면 밖까지** 나가서 어깨가 안 보였다 —
     되살리지 말 것. */
  testWidgets('막대가 화면 양끝에서 떨어져 있다', (tester) async {
    await _pump(tester);
    final bar = tester.getRect(_bar());
    final screenW = tester.view.physicalSize.width / tester.view.devicePixelRatio;

    expect(bar.left, greaterThan(0));
    expect(bar.right, lessThan(screenW));
    // 양옆이 같아야 막대가 가운데 선다.
    expect(bar.left, closeTo(screenW - bar.right, 0.5));
  });

  testWidgets('홈은 0번, 메뉴는 메뉴 자리를 알린다', (tester) async {
    final taps = <int>[];
    await _pump(tester, taps: taps);

    await tester.tap(find.byKey(const Key('navbar-icon-0')));
    await tester.tap(find.byKey(const Key('navbar-icon-menu')));
    expect(taps, [0, FloatingNavBar.menuIndex]);
  });

  /* 칸이 다섯이면 사이는 넷이다 — 레퍼런스가 칸마다 선을 긋는다. */
  testWidgets('칸과 칸 사이마다 세로선이 선다', (tester) async {
    await _pump(tester);
    final dividers = find.byWidgetPredicate(
      (w) =>
          w.key is ValueKey<String> &&
          (w.key! as ValueKey<String>).value.startsWith('navbar-divider'),
    );
    expect(dividers, findsNWidgets(4));

    /* 🔴 **높이가 0 이 아니어야 한다 — 실제로 0 이었다(2026-09-23).**
       [SizedBox] 에 **폭만** 주었더니 [Row] 의 느슨한 세로 제약 아래
       [ColoredBox] 가 높이 0 으로 앉았다. 트리에는 있고 화면에는 없어서,
       개수만 세는 시험은 **통과하면서** 선이 안 보였다. */
    for (final e in dividers.evaluate()) {
      final size = (e.renderObject! as RenderBox).size;
      expect(size.height, greaterThan(0), reason: '세로선 높이');
      expect(size.width, greaterThan(0), reason: '세로선 굵기');
    }
  });
}
