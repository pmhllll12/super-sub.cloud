import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/app.dart';

void main() {
  testWidgets('로그인하지 않았으면 로그인 화면으로 간다', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: SuperSubApp()));
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pumpAndSettle();
    expect(find.text('로그인'), findsWidgets);
  });
}
