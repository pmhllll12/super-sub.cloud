import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/dev/data_source.dart';
import '../../../core/mock/mock_db.dart';
import '../../../core/network/api_client.dart';
import '../../auth/presentation/session_controller.dart';
import 'models/skeleton.dart';
import 'models/video_report.dart';
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

/// 누군가 공개해 둔 영상 목록 — 홈의 영상 줄이 쓴다.
///
/// 🔴 **내 것만이 아니다.** 앱에서 올리든 웹에서 올리든 **공개로 돌린 것**이
/// 여기 다 온다(서버 질의가 `is_public && kept`).
///
/// 🔴 **홈을 열 때 한 번 받는다.** 웹에서 방금 공개로 바꿔도 이미 떠 있는
/// 화면에는 안 나타난다 — 다시 들어와야 보인다.
///
/// retry 를 끈 까닭은 아래 [videoReportProvider] 와 같다.
final publicVideosProvider = FutureProvider(
  (ref) => ref.watch(videoRepositoryProvider).publicVideos(),
  retry: (_, _) => null,
);

/// 카드에 깔 **한 장면**(JPEG).
///
/// 🔴 **재생 주소와 달리 캐시해도 된다** — 사전 서명이 아니라 그림 자체라
/// 만료가 없다. Riverpod 이 들고 있으므로 되감아 와도 다시 안 받는다.
/// 🔴 **여기만 재시도를 켠다** (2026-09-25 사용자 지적: 「아직도 썸네일
/// 안나오는것들 있어」). 다른 목록 provider 들은 꺼 두는 것이 맞지만 —
/// 사람이 다시 당기면 되고, 무한 재시도가 느린 서버를 더 때린다 — 포스터는
/// 다르다:
///
/// - **사람이 다시 시킬 방법이 없다.** 카드는 그냥 검게 남고, 누르면 그 영상이
///   열릴 뿐 포스터를 다시 받지 않는다
/// - **한 번 끊기기 아주 쉽다.** 서버가 캐시에 없는 장면을 뜰 때 **50~60초**가
///   걸린다(2026-09-25 실측). 그동안 끊기면 그 영상은 **앱을 끌 때까지** 검다
/// - **화면이 오류를 못 알아본다.** `.value` 는 오류일 때도 `null` 이라
///   「아직 오는 중」과 구별이 안 된다(1.23 때 카드가 비어 보이던 그 함정)
///
/// 🔴 **404 는 여기로 안 온다** — 리포지토리가 「포스터 없음」을 `null` **값**
/// 으로 바꾼다. 그래서 이 재시도는 **끊김·5xx 에만** 걸리고, 못 뜨는 영상을
/// 되풀이해 묻지 않는다.
final videoPosterProvider = FutureProvider.family<Uint8List?, String>(
  (ref, videoId) => ref.watch(videoRepositoryProvider).poster(videoId),
  retry: posterRetry,
);

/// 포스터를 몇 번, 얼마 뒤에 다시 받을 것인가. **세 번까지만.**
///
/// 🔴 **따로 이름을 둔 것은 시험 때문이다.** provider 에 물린 채로는 재시도가
/// 진짜 타이머를 타서, 시험이 초 단위로 기다리거나 가짜 시계에 걸린다. 규칙만
/// 떼어 두면 **결정이 맞는지**를 즉시 확인할 수 있다.
///
/// 끝없이 매달리지 않는 까닭: 느린 서버를 더 때리고 배터리를 먹는다.
Duration? posterRetry(int count, Object error) =>
    count >= 3 ? null : Duration(milliseconds: 300 * (count + 1));

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

/// 그 영상의 **관절 시계열** (2026-09-25).
///
/// 🔴 **캐시해도 된다** — 분석이 끝난 영상의 관절은 안 바뀐다. 다만 응답이
/// 크다(실측 316KB) — 여러 영상 것을 한꺼번에 들고 있지 않게, 보는 영상
/// 하나만 `watch` 한다.
final skeletonProvider = FutureProvider.family<SkeletonResult, String>(
  (ref, videoId) => ref.watch(videoRepositoryProvider).skeleton(videoId),
  retry: (_, _) => null,
);

/// 그 영상의 분석 리포트.
///
/// 🔴 **실패도 값으로 온다**(`ReportResult`) — 「아직」·「실패」·「없다」를
/// `AsyncError` 로 뭉치면 화면이 그 셋을 못 가른다. 여기서 `AsyncError` 인
/// 것은 **읽기 자체가 안 된 경우**(네트워크·401)뿐이다.
///
/// retry 를 끈 이유는 `myCardProvider` 와 같다 — Riverpod 3 는 실패한
/// provider 를 백오프로 자동 재시도하고 그동안 `AsyncLoading` 을 유지해서,
/// 화면이 오류 대신 로딩만 계속 보여준다.
final videoReportProvider = FutureProvider.family<ReportResult, String>(
  (ref, videoId) => ref.watch(videoRepositoryProvider).report(videoId),
  retry: (_, _) => null,
);
