import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/dev/data_source.dart';
import '../../../core/mock/mock_db.dart';
import '../../../core/network/api_client.dart';
import '../../auth/presentation/session_controller.dart';
import 'card_repository.dart';
import 'card_repository_api.dart';
import 'card_repository_mock.dart';
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
