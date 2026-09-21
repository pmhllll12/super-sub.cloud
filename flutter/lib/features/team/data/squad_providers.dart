import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/dev/data_source.dart';
import '../../../core/mock/mock_db.dart';
import '../../../core/network/api_client.dart';
import 'models/squad.dart';
import 'squad_repository.dart';
import 'squad_repository_api.dart';
import 'squad_repository_mock.dart';

/// 🔴 **백엔드 교체 지점.** `sport_providers.dart` 와 **따로 둔다** — 한 파일에
/// 모으면 종목 provider 를 무효화할 때 스쿼드까지 함께 다시 만들어진다.
final squadRepositoryProvider = Provider<SquadRepository>((ref) {
  if (ref.watch(useMockProvider)) {
    return MockSquadRepository(ref.watch(mockDbProvider));
  }
  return ApiSquadRepository(ref.watch(apiClientProvider));
});

/// 팀 하나의 스쿼드. 🔴 **`null` 은 정상** — 아직 안 만든 것이다.
///
/// retry 를 끈 이유는 `sportsProvider` 와 같다 — 자동 재시도가 돌면 화면이
/// 오류 대신 로딩만 계속 보여준다.
final squadProvider = FutureProvider.family<Squad?, String>(
  (ref, teamId) => ref.watch(squadRepositoryProvider).squadOf(teamId),
  retry: (_, _) => null,
);
