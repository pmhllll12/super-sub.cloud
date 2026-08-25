import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/app.dart';
import 'package:super_sub/features/intro/presentation/intro_gate.dart';

void main() {
  testWidgets('로그인하지 않았으면 로그인 화면으로 간다', (tester) async {
    // 인트로를 끈다 — 이 테스트가 보는 것은 라우터의 착지지 연출이 아니다.
    await tester.pumpWidget(ProviderScope(
      overrides: [introEnabledProvider.overrideWithValue(false)],
      child: const SuperSubApp(),
    ));
    await tester.pump(const Duration(milliseconds: 500));
    expect(find.text('로그인'), findsWidgets);
  });
}
