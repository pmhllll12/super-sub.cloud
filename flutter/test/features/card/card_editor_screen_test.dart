import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/card/data/card_providers.dart';
import 'package:super_sub/features/card/data/card_repository.dart';
import 'package:super_sub/features/card/data/models/player_card.dart';
import 'package:super_sub/features/card/presentation/card_editor_screen.dart';

/// 저장으로 **무엇이 갔는지**를 기록하는 대역.
class _SpyRepo implements CardRepository {
  String? tagline;
  bool? cleared;
  CardStyle? style;
  var saves = 0;

  @override
  Future<PlayerCard> updateCard({
    String? tagline,
    bool clearTagline = false,
    CardStyle? style,
  }) async {
    saves += 1;
    this.tagline = tagline;
    cleared = clearTagline;
    this.style = style;
    return const PlayerCard(publicSlug: 'mine', nickname: '나');
  }

  @override
  Future<PlayerCard?> myCard() async => null;
  @override
  Future<PlayerCard> createMyCard() => throw UnimplementedError();
  @override
  Future<PlayerCard?> cardBySlug(String slug) async => null;
}

Future<_SpyRepo> _pump(WidgetTester tester, {PlayerCard? card}) async {
  final repo = _SpyRepo();
  tester.view.physicalSize = const Size(1080, 2340);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    ProviderScope(
      overrides: [cardRepositoryProvider.overrideWithValue(repo)],
      child: MaterialApp(
        home: CardEditorScreen(
          card: card ??
              const PlayerCard(
                publicSlug: 'mine',
                nickname: '나',
                tagline: 'THREE LUNGS',
              ),
        ),
      ),
    ),
  );
  await tester.pump();
  return repo;
}

void main() {
  testWidgets('탭 셋이 선다', (tester) async {
    await _pump(tester);

    for (final k in const ['colors', 'text', 'mark']) {
      expect(find.byKey(Key('card-editor-tab-$k')), findsOneWidget, reason: k);
    }
  });

  testWidgets('지금 글자가 칸에 들어와 있다', (tester) async {
    await _pump(tester);
    await tester.tap(find.byKey(const Key('card-editor-tab-text')));
    await tester.pumpAndSettle();

    final field = tester.widget<TextField>(
      find.byKey(const Key('card-editor-tagline')),
    );
    expect(field.controller!.text, 'THREE LUNGS');
  });

  /// 🔴 20자까지다 — 넘기면 서버가 422 다. 화면에서 먼저 막는다.
  testWidgets('한 줄은 20자까지만 쳐진다', (tester) async {
    await _pump(tester);
    await tester.tap(find.byKey(const Key('card-editor-tab-text')));
    await tester.pumpAndSettle();

    final field = tester.widget<TextField>(
      find.byKey(const Key('card-editor-tagline')),
    );
    expect(field.maxLength, 20);
  });

  testWidgets('저장하면 글자와 꾸미기가 함께 간다', (tester) async {
    final repo = await _pump(tester);

    await tester.tap(find.byKey(const Key('card-editor-save')));
    await tester.pump();

    expect(repo.saves, 1);
    expect(repo.tagline, 'THREE LUNGS');
    expect(repo.style, isNotNull);
  });

  /// 🔴 비우면 「안 정함」이 아니라 **「일부러 지웠다」**다 — 그 둘을
  /// `clearTagline` 이 가른다(서버는 null 과 공백을 똑같이 다룬다).
  testWidgets('글자를 비우면 지운다고 보낸다', (tester) async {
    final repo = await _pump(tester);
    await tester.tap(find.byKey(const Key('card-editor-tab-text')));
    await tester.pumpAndSettle();

    await tester.enterText(find.byKey(const Key('card-editor-tagline')), '');
    await tester.tap(find.byKey(const Key('card-editor-save')));
    await tester.pump();

    expect(repo.cleared, isTrue);
    expect(repo.tagline, isNull);
  });

  group('자국 고르기', () {
    /// 🔴 배열에서 빼면 뒤 번호가 당겨져 **그 자국을 쓰던 카드가 말없이 다른
    /// 그림**이 된다 — 자리를 남기고 고르는 칸에서만 숨긴다.
    test('숨긴 자국(7·8)은 고르는 칸에 없지만 번호는 남아 있다', () {
      expect(kPickableMarks, isNot(contains(7)));
      expect(kPickableMarks, isNot(contains(8)));
      // 그 뒤 번호가 당겨지지 않았다.
      expect(kPickableMarks, contains(9));
      expect(kPickableMarks.last, 18);
    });

    test('기본(0)과 없음(1)도 고를 수 있다', () {
      expect(kPickableMarks.take(2), [0, 1]);
    });

    testWidgets('자국을 고르면 저장에 그 번호가 실린다', (tester) async {
      final repo = await _pump(tester);
      await tester.tap(find.byKey(const Key('card-editor-tab-mark')));
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('card-editor-mark-12')));
      await tester.pump();
      await tester.tap(find.byKey(const Key('card-editor-save')));
      await tester.pump();

      expect(repo.style!.brush, 12);
    });

    /// 🔴 「없음」을 골랐으면 조정할 것이 없다 — 웹도 이때 칸을 감춘다.
    testWidgets('없음을 고르면 색·크기 칸이 사라진다', (tester) async {
      await _pump(tester);
      await tester.tap(find.byKey(const Key('card-editor-tab-mark')));
      await tester.pumpAndSettle();

      expect(find.text('자국 색'), findsOneWidget);

      await tester.tap(find.byKey(const Key('card-editor-mark-1')));
      await tester.pumpAndSettle();

      expect(find.text('자국 색'), findsNothing);
    });
  });
}
