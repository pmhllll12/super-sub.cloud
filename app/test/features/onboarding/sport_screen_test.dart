import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/core/sport/current_sport.dart';
import 'package:super_sub/features/onboarding/presentation/screens/sport_screen.dart';

void main() {
  testWidgets('종목 2개가 보인다', (tester) async {
    await tester.pumpWidget(const ProviderScope(
      child: MaterialApp(home: SportScreen()),
    ));
    expect(find.text('풋살'), findsOneWidget);
    expect(find.text('야구'), findsOneWidget);
  });

  testWidgets('종목을 고르면 전역 컨텍스트에 반영된다', (tester) async {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    await tester.pumpWidget(UncontrolledProviderScope(
      container: container,
      child: const MaterialApp(home: SportScreen()),
    ));

    expect(container.read(currentSportProvider), isNull);
    await tester.tap(find.text('야구'));
    await tester.pump();
    expect(container.read(currentSportProvider), equals('baseball'));
  });
}
