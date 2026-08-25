import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/core/widgets/async_view.dart';

Widget _wrap(Widget child) => MaterialApp(home: Scaffold(body: child));

void main() {
  testWidgets('로딩이면 인디케이터를 보여준다', (tester) async {
    await tester.pumpWidget(_wrap(
      AsyncView<List<String>>(
        value: const AsyncValue.loading(),
        data: (d) => Text(d.join()),
      ),
    ));
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });

  testWidgets('성공이면 내용을 보여준다', (tester) async {
    await tester.pumpWidget(_wrap(
      AsyncView<List<String>>(
        value: const AsyncValue.data(['가', '나']),
        data: (d) => Text(d.join()),
      ),
    ));
    expect(find.text('가나'), findsOneWidget);
  });

  testWidgets('빈 결과면 안내 문구를 보여준다', (tester) async {
    await tester.pumpWidget(_wrap(
      AsyncView<List<String>>(
        value: const AsyncValue.data([]),
        isEmpty: (d) => d.isEmpty,
        emptyMessage: '아직 영상이 없습니다',
        data: (d) => Text(d.join()),
      ),
    ));
    expect(find.text('아직 영상이 없습니다'), findsOneWidget);
  });

  testWidgets('오류면 사유와 재시도 버튼을 보여준다', (tester) async {
    var retried = false;
    await tester.pumpWidget(_wrap(
      AsyncView<List<String>>(
        value: AsyncValue.error('불러오지 못했습니다', StackTrace.empty),
        onRetry: () => retried = true,
        data: (d) => Text(d.join()),
      ),
    ));
    expect(find.text('불러오지 못했습니다'), findsOneWidget);
    await tester.tap(find.text('다시 시도'));
    expect(retried, isTrue);
  });
}
