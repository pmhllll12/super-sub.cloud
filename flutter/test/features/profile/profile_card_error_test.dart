import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/core/dev/data_source.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/core/network/upload_file.dart';
import 'package:super_sub/features/auth/data/auth_providers.dart';
import 'package:super_sub/features/auth/data/auth_repository_mock.dart';
import 'package:super_sub/features/auth/presentation/session_controller.dart';
import 'package:super_sub/features/card/data/card_providers.dart';
import 'package:super_sub/features/card/data/card_repository.dart';
import 'package:super_sub/features/card/data/models/player_card.dart';
import 'package:super_sub/features/profile/presentation/screens/profile_screen.dart';

/// 🔴 **카드를 못 읽은 것과 카드가 없는 것은 다르다.**
///
/// `ref.watch(myCardProvider).value` 는 **오류일 때도 `null`** 이라 둘이
/// 화면에서 똑같이 보였다(2026-09-23 회차에서 401 을 세 시간 못 찾은 원인).
/// 그 자리에 「카드 만들기」가 떠서 **멀쩡한 카드가 있는데도 새로 만들** 수
/// 있었다 — 이 파일이 그것을 막는 지킴이다.
///
/// `pumpAndSettle` 을 안 쓰는 이유는 `profile_screen_test.dart` 와 같다.
Future<void> _settle(WidgetTester tester) async {
  for (var i = 0; i < 8; i += 1) {
    await tester.pump(const Duration(milliseconds: 250));
  }
}

/// 처음 [failTimes] 번은 던지고 그 뒤부터 카드를 내주는 가짜 저장소.
///
/// 🔴 **가짜 서버가 아니라 가짜 저장소다** — 「다시 시도」가 provider 를
/// 실제로 다시 돌리는지를 봐야 하므로, 호출 횟수가 세어지는 자리가 필요하다.
class _FlakyCardRepository implements CardRepository {
  _FlakyCardRepository({this.failTimes = 1});

  final int failTimes;
  int calls = 0;

  static const card = PlayerCard(
    publicSlug: 'slug-error-test',
    nickname: '백성검',
  );

  @override
  Future<PlayerCard?> myCard() async {
    calls += 1;
    if (calls <= failTimes) {
      throw Exception('불러오기 실패');
    }
    return card;
  }

  @override
  Future<PlayerCard> createMyCard() async => card;

  @override
  Future<PlayerCard?> cardBySlug(String slug) async => null;

  @override
  Future<PlayerCard> updateCard({
    String? tagline,
    bool clearTagline = false,
    CardStyle? style,
    List<String>? titles,
  }) async => card;

  @override
  Future<String> uploadCardPhoto(UploadFile file) async => 'key';
}

class _AlwaysMock extends DataSourceController {
  @override
  bool build() => true;
}

Future<ProviderContainer> _pump(
  WidgetTester tester,
  CardRepository cards,
) async {
  final container = ProviderContainer(
    overrides: [
      authRepositoryProvider.overrideWith(
        (ref) => MockAuthRepository(ref.watch(mockDbProvider)),
      ),
      useMockProvider.overrideWith(() => _AlwaysMock()),
      cardRepositoryProvider.overrideWithValue(cards),
    ],
  );
  addTearDown(container.dispose);

  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: const MaterialApp(home: ProfileScreen()),
    ),
  );
  unawaited(
    container.read(sessionControllerProvider.notifier).loginAs(MockDb.playerId),
  );
  await _settle(tester);
  return container;
}

void main() {
  testWidgets('카드를 못 읽으면 「카드 만들기」를 내밀지 않는다', (tester) async {
    await _pump(tester, _FlakyCardRepository());

    /* 🔴 **이것이 이 파일의 이유다.** 카드는 서버에 멀쩡히 있는데 읽기만
       실패한 상태에서 「만들기」를 누르면 사용자는 있는 것을 또 만들려 한다. */
    expect(find.text('카드 만들기'), findsNothing);
  });

  testWidgets('카드를 못 읽으면 실패했다고 말하고 다시 시도할 길을 준다', (tester) async {
    await _pump(tester, _FlakyCardRepository());

    expect(find.byKey(const Key('profile-card-retry')), findsOneWidget);
  });

  testWidgets('「다시 시도」를 누르면 다시 읽고, 성공하면 카드가 뜬다', (tester) async {
    final cards = _FlakyCardRepository();
    await _pump(tester, cards);
    expect(cards.calls, 1);

    await tester.tap(find.byKey(const Key('profile-card-retry')));
    await _settle(tester);

    expect(cards.calls, 2);
    expect(find.text('프로필 카드 수정'), findsOneWidget);
    expect(find.byKey(const Key('profile-card-retry')), findsNothing);
  });

  testWidgets('아직 읽는 중에도 「카드 만들기」를 내밀지 않는다', (tester) async {
    /* 🔴 **오류와 같은 뿌리다.** `.value` 는 로딩 중에도 `null` 이라,
       느린 망에서는 카드가 있는 사람에게도 「만들기」가 **먼저 한 번
       깜빡였다.** 그 순간에 눌리면 오류일 때와 똑같은 일이 난다. */
    await _pump(tester, _HangingCardRepository());

    expect(find.text('카드 만들기'), findsNothing);
    expect(find.text('프로필 카드 수정'), findsNothing);
  });

  testWidgets('카드가 정말 없을 때는 「카드 만들기」가 그대로 뜬다', (tester) async {
    // 🔴 **위 셋의 반대쪽이다** — 오류를 가리려다 정상적인 「아직 없음」까지
    //    막으면 카드를 처음 만들 길이 사라진다.
    await _pump(tester, _FlakyCardRepository(failTimes: 0));
    // failTimes 0 이면 카드를 내주므로, 「없음」은 별도 가짜로 본다.
    await _pump(tester, _EmptyCardRepository());

    expect(find.text('카드 만들기'), findsOneWidget);
    expect(find.byKey(const Key('profile-card-retry')), findsNothing);
  });
}

/// 영영 안 끝나는 읽기 — 「로딩 중」에 머무르게 한다.
class _HangingCardRepository extends _FlakyCardRepository {
  _HangingCardRepository() : super(failTimes: 0);

  @override
  Future<PlayerCard?> myCard() {
    calls += 1;
    return Completer<PlayerCard?>().future;
  }
}

class _EmptyCardRepository extends _FlakyCardRepository {
  _EmptyCardRepository() : super(failTimes: 0);

  @override
  Future<PlayerCard?> myCard() async {
    calls += 1;
    return null;
  }
}
