import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/features/video/presentation/chat_controller.dart';
import 'package:super_sub/features/video/presentation/chat_pane.dart';

Widget _wrap() => const ProviderScope(
      child: MaterialApp(home: Scaffold(body: ChatPane())),
    );

void main() {
  testWidgets('처음에는 안내만 있다', (tester) async {
    await tester.pumpWidget(_wrap());
    expect(find.textContaining('궁금한 것을 물어보세요'), findsOneWidget);
  });

  testWidgets('보내면 내 말이 붙고 답이 돌아온다', (tester) async {
    await tester.pumpWidget(_wrap());

    await tester.enterText(find.byKey(const Key('chat-input')), '포지션 알려줘');
    await tester.tap(find.byKey(const Key('chat-send')));
    await tester.pump();

    // 답을 기다리는 동안에도 보낸 말은 화면에 남는다.
    expect(find.text('포지션 알려줘'), findsOneWidget);

    // Mock의 700ms 지연을 흘려보낸다. pumpAndSettle은 쓰지 않는다 —
    // 기다리는 동안 도는 인디케이터가 무한 애니메이션이다.
    await tester.pump(const Duration(milliseconds: 900));
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.textContaining('측면'), findsOneWidget);
  });

  testWidgets('빈 줄은 보내지지 않는다', (tester) async {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    await tester.pumpWidget(UncontrolledProviderScope(
      container: container,
      child: const MaterialApp(home: Scaffold(body: ChatPane())),
    ));

    await tester.enterText(find.byKey(const Key('chat-input')), '   ');
    await tester.tap(find.byKey(const Key('chat-send')));
    await tester.pump(const Duration(milliseconds: 900));

    expect(container.read(chatControllerProvider).messages, isEmpty);
  });
}
