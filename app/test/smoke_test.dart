import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/app.dart';

void main() {
  testWidgets('앱이 뜨고 앱 이름이 보인다', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: SuperSubApp()));
    await tester.pumpAndSettle();
    expect(find.text('Super-Sub'), findsOneWidget);
  });
}
