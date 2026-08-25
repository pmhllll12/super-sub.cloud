import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/core/sport/current_sport.dart';
import 'package:super_sub/features/onboarding/presentation/screens/sport_screen.dart';
import 'package:super_sub/features/team/data/models/sport.dart';
import 'package:super_sub/features/team/data/sport_providers.dart';
import 'package:super_sub/features/team/data/sport_repository.dart';

/// 화면이 리포지토리 인터페이스만 안다는 것을 실제로 확인하는 장치.
/// 구현체를 바꿔 끼워도 화면은 그대로다.
class _FailingSportRepository implements SportRepository {
  @override
  Future<List<Sport>> sports() async => throw Exception('불러오지 못했습니다');
}

class _EmptySportRepository implements SportRepository {
  @override
  Future<List<Sport>> sports() async => const [];
}

void main() {
  testWidgets('불러오는 동안 로딩을 보여준다', (tester) async {
    await tester.pumpWidget(const ProviderScope(
      child: MaterialApp(home: SportScreen()),
    ));
    // Mock은 300ms 지연을 흉내낸다 — 첫 프레임은 아직 로딩이다.
    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    await tester.pump(const Duration(milliseconds: 500));
    expect(find.byType(CircularProgressIndicator), findsNothing);
  });

  testWidgets('종목 2개가 보인다', (tester) async {
    await tester.pumpWidget(const ProviderScope(
      child: MaterialApp(home: SportScreen()),
    ));
    await tester.pump(const Duration(milliseconds: 500));

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
    await tester.pump(const Duration(milliseconds: 500));

    expect(container.read(currentSportProvider), isNull);
    await tester.tap(find.text('야구'));
    await tester.pump();
    expect(container.read(currentSportProvider), equals('baseball'));
  });

  testWidgets('조회에 실패하면 사유와 재시도 버튼을 보여준다', (tester) async {
    await tester.pumpWidget(ProviderScope(
      overrides: [
        sportRepositoryProvider.overrideWithValue(_FailingSportRepository()),
      ],
      child: const MaterialApp(home: SportScreen()),
    ));
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.textContaining('불러오지 못했습니다'), findsOneWidget);
    expect(find.text('다시 시도'), findsOneWidget);
  });

  testWidgets('종목이 하나도 없으면 빈 상태를 보여준다', (tester) async {
    await tester.pumpWidget(ProviderScope(
      overrides: [
        sportRepositoryProvider.overrideWithValue(_EmptySportRepository()),
      ],
      child: const MaterialApp(home: SportScreen()),
    ));
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.text('선택할 수 있는 종목이 없습니다'), findsOneWidget);
  });
}
