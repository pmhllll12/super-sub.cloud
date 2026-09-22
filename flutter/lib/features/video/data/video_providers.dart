import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/dev/data_source.dart';
import '../../../core/mock/mock_db.dart';
import '../../../core/network/api_client.dart';
import '../../auth/presentation/session_controller.dart';
import 'video_repository.dart';
import 'video_repository_api.dart';
import 'video_repository_mock.dart';

/// 🔴 **백엔드 교체 지점 — 여기 한 줄이다.** 화면·위젯·컨트롤러는 수정하지
/// 않는다. 한 곳이라도 화면에서 구현체를 직접 만들면 그 화면만 provider 를
/// 안 따라가고, 「교체했는데 일부만 바뀌는」 상태가 된다.
final videoRepositoryProvider = Provider<VideoRepository>((ref) {
  if (ref.watch(useMockProvider)) {
    // Mock 은 「내 영상」이 누구 것인지 알아야 한다 — 로그인한 사람을 따른다.
    final session = ref.watch(sessionControllerProvider);
    return MockVideoRepository(
      ref.watch(mockDbProvider),
      userId: session is SessionLoggedIn ? session.user.id : MockDb.playerId,
    );
  }
  return ApiVideoRepository(ref.watch(apiClientProvider));
});

/// 지금 보고 있는 영상의 **재생 주소**.
///
/// 🔴 **캐시하지 않는다** — 사전 서명 주소는 `expires_in`(900초) 뒤 만료된다.
/// 영상을 넘길 때마다 새로 받는다. `family` 로 둔 것도 그래서다 — 목록 전체의
/// 주소를 미리 받아 두면 뒤쪽 것은 볼 때쯤 이미 죽어 있다.
///
/// 🔴 **`null` 은 정상이다** — 저장소가 안 붙은 배포에서 그렇다. 화면은 그때
/// 플레이어 자리를 비워 두고 나머지를 그대로 그린다.
final playbackUrlProvider = FutureProvider.family<String?, String>(
  (ref, videoId) => ref.watch(videoRepositoryProvider).playbackUrl(videoId),
  retry: (_, _) => null,
);
