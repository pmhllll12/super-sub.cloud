import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/match_prefs.dart';
import 'package:super_sub/features/team/presentation/widgets/slot_editor.dart';

Future<TimeSlot?> _pump(WidgetTester tester, TimeSlot slot) async {
  tester.view.physicalSize = const Size(1080, 2340);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);

  TimeSlot? changed;
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        // 🔴 실제 쓰임과 같게 **폭을 준다** — 칸들이 남는 폭을 나눠 갖는다.
        body: SizedBox(width: 360, child: SlotEditor(
          slot: slot,
          onChanged: (s) => changed = s,
          onRemove: () {},
        )),
      ),
    ),
  );
  await tester.pump();
  return changed;
}

void main() {
  _defaultSlotTests();

  /// 🔴 **요일·시각을 사람이 고른다** (2026-09-25, 사용자: 「대체 왜 시간이랑
  /// 날짜를 선택할 수 없게 해놓은거야? 왜 토요일과 시간대가 고정이야」).
  /// 한쪽 폼에는 고를 칸을 아예 안 넣고 값을 박아 뒀었다 — 두 폼이 **같은
  /// 칸**을 나눠 써야 그런 일이 다시 안 난다.
  testWidgets('요일·시작·끝이 모두 고르는 칸이다', (tester) async {
    await _pump(tester, const TimeSlot(day: 6, from: '09:00', to: '11:00'));

    expect(find.byKey(const Key('slot-day')), findsOneWidget);
    expect(find.byKey(const Key('slot-from')), findsOneWidget);
    expect(find.byKey(const Key('slot-to')), findsOneWidget);
  });

  testWidgets('요일을 바꾸면 알린다', (tester) async {
    TimeSlot? got;
    tester.view.physicalSize = const Size(1080, 2340);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          // 🔴 실제 쓰임과 같게 **폭을 준다** — 칸들이 남는 폭을 나눠 갖는다.
        body: SizedBox(width: 360, child: SlotEditor(
            slot: const TimeSlot(day: 6, from: '09:00', to: '11:00'),
            onChanged: (s) => got = s,
            onRemove: () {},
          )),
        ),
      ),
    );

    await tester.tap(find.byKey(const Key('slot-day')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('수').last);
    await tester.pumpAndSettle();

    expect(got?.day, 3, reason: '수요일은 3 이다(0=일)');
  });

  /// 🔴 **끝은 시작보다 뒤만 고를 수 있다** — 뒤집힌 시간은 겹침 계산에서 늘
  /// 거짓이라 조용히 아무것도 안 걸린다(서버도 422 로 막는다).
  testWidgets('끝 목록에는 시작 이전이 없다', (tester) async {
    tester.view.physicalSize = const Size(1080, 2340);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          // 🔴 실제 쓰임과 같게 **폭을 준다** — 칸들이 남는 폭을 나눠 갖는다.
        body: SizedBox(width: 360, child: SlotEditor(
            slot: const TimeSlot(day: 6, from: '12:00', to: '14:00'),
            onChanged: (_) {},
            onRemove: () {},
          )),
        ),
      ),
    );

    await tester.tap(find.byKey(const Key('slot-to')));
    await tester.pumpAndSettle();

    expect(find.text('06:00'), findsNothing);
    expect(find.text('14:30'), findsWidgets);
  });

  /// 🔴 **시작을 끝 뒤로 밀면 끝도 함께 민다** — 안 그러면 뒤집힌 채로 저장돼
  /// 서버가 422 를 낸다.
  testWidgets('시작이 끝을 넘으면 끝도 따라 밀린다', (tester) async {
    TimeSlot? got;
    tester.view.physicalSize = const Size(1080, 2340);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          // 🔴 실제 쓰임과 같게 **폭을 준다** — 칸들이 남는 폭을 나눠 갖는다.
        body: SizedBox(width: 360, child: SlotEditor(
            slot: const TimeSlot(day: 6, from: '09:00', to: '10:00'),
            onChanged: (s) => got = s,
            onRemove: () {},
          )),
        ),
      ),
    );

    await tester.tap(find.byKey(const Key('slot-from')));
    await tester.pumpAndSettle();
    // 🔴 가까운 값을 고른다 — 목록이 길어 먼 값은 메뉴에서 스크롤해야 한다.
    await tester.tap(find.text('11:00').last);
    await tester.pumpAndSettle();

    expect(got!.from.compareTo(got!.to) < 0, isTrue,
        reason: '${got!.from}~${got!.to}');
  });
}

/// 🔴 **첫 값이 오늘 요일이다** — 토요일을 박아 두면 「왜 토요일 고정이냐」가
/// 된다(2026-09-25 사용자 지적).
void _defaultSlotTests() {
  test('첫 값은 오늘 요일이다', () {
    // 2026-09-25 는 금요일 → 화면 기준 5.
    final s = defaultSlot(DateTime(2026, 9, 25, 10, 10));

    expect(s.day, 5);
  });

  test('첫 값은 다음 30분 칸부터 두 시간이다', () {
    final s = defaultSlot(DateTime(2026, 9, 25, 10, 10));

    expect(s.from, '10:30');
    expect(s.to, '12:30');
  });

  /// 🔴 목록 끝을 넘지 않는다 — 넘으면 고를 수 없는 값이 박힌다.
  test('늦은 시각이어도 목록 안에 머문다', () {
    final s = defaultSlot(DateTime(2026, 9, 25, 23, 50));

    expect(kHours.contains(s.from), isTrue, reason: s.from);
    expect(kHours.contains(s.to), isTrue, reason: s.to);
    expect(s.from.compareTo(s.to) < 0, isTrue, reason: '${s.from}~${s.to}');
  });
}
