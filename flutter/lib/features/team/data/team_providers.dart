import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/dev/data_source.dart';
import '../../../core/mock/mock_db.dart';
import '../../../core/network/api_client.dart';
import '../../auth/presentation/session_controller.dart';
import 'team_repository.dart';
import 'team_repository_api.dart';
import 'team_repository_mock.dart';

/// 🔴 **백엔드 교체 지점 — 여기 한 줄이다.** 화면·컨트롤러는 수정하지 않는다.
///
/// 🔴 **둘 다 「나」가 누구인지 알아야 한다** — 나가기 경로가 내 멤버 id 를
/// URL 에 싣고(`/members/{id}`), 권한도 그것으로 갈린다.
final teamRepositoryProvider = Provider<TeamRepository>((ref) {
  final session = ref.watch(sessionControllerProvider);
  final userId = session is SessionLoggedIn ? session.user.id : MockDb.playerId;

  if (ref.watch(useMockProvider)) {
    return MockTeamRepository(ref.watch(mockDbProvider), userId: userId);
  }
  return ApiTeamRepository(ref.watch(apiClientProvider), myUserId: userId);
});
