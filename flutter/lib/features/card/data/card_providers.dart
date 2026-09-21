import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/dev/data_source.dart';
import '../../../core/mock/mock_db.dart';
import '../../../core/network/api_client.dart';
import '../../auth/presentation/session_controller.dart';
import 'card_repository.dart';
import 'card_repository_api.dart';
import 'card_repository_mock.dart';
import '../../profile/presentation/widgets/player_card_view.dart'
    show kDefaultCardAlias;
import 'models/player_card.dart';

/// 🔴 **백엔드 교체 지점 — 여기 한 줄이다.** 화면·위젯·컨트롤러는 수정하지
/// 않는다. 한 곳이라도 화면에서 구현체를 직접 만들면 그 화면만 provider 를
/// 안 따라가고, 「교체했는데 일부만 바뀌는」 상태가 된다.
final cardRepositoryProvider = Provider<CardRepository>((ref) {
  if (ref.watch(useMockProvider)) {
    // Mock 은 「내 카드」가 누구 것인지 알아야 한다 — 로그인한 사람을 따른다.
    final session = ref.watch(sessionControllerProvider);
    return MockCardRepository(
      ref.watch(mockDbProvider),
      userId: session is SessionLoggedIn ? session.user.id : MockDb.playerId,
    );
  }
  return ApiCardRepository(ref.watch(apiClientProvider));
});

/// 내 카드. 🔴 **`null` 은 정상이다** — 아직 안 만든 것이고, 화면은 그때 빈
/// 카드를 그린다.
///
/// retry 를 끈 이유는 `sportsProvider` 와 같다 — Riverpod 3 는 실패한 provider 를
/// 백오프로 자동 재시도하고 그동안 상태를 `AsyncLoading` 으로 유지한다. 그러면
/// 화면이 오류 대신 로딩만 계속 보여주게 된다.
final myCardProvider = FutureProvider<PlayerCard?>(
  (ref) => ref.watch(cardRepositoryProvider).myCard(),
  retry: (_, _) => null,
);

/// 카드를 만들고 **첫 모습까지 저장한다**(웹 `saveFirstLook`).
///
/// 🔴 **첫 모습을 저장하지 않으면 앱에서 만든 카드가 웹에서 만든 것과 다르게
/// 보인다** — 웹은 만든 직후 한 번 꾸며 준다(붓 「오려낸 X」·검정·1.4배).
///
/// 🔴 **글자도 같이 싣는다.** `style` 만 저장하면 `aliasOf` 가 「꾸민 적이
/// 있는데 글자가 비었다 = 일부러 지웠다」로 읽어 **기본 별명이 사라진다**
/// (웹이 헤드리스로 겪은 것).
///
/// 🔴 **첫 모습 저장이 실패해도 던지지 않는다** — 카드는 이미 생겼다. 모습만
/// 기본으로 남을 뿐이고, 꾸미기 화면에서 고치면 된다.
Future<PlayerCard> createCardWithFirstLook(CardRepository repo) async {
  final card = await repo.createMyCard();
  try {
    return await repo.updateCard(
      tagline: kDefaultCardAlias,
      style: firstCardStyle,
    );
  } catch (_) {
    return card;
  }
}
