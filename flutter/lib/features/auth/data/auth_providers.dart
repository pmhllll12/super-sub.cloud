import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/dev/data_source.dart';
import '../../../core/mock/mock_db.dart';
import '../../../core/network/api_client.dart';
import 'auth_repository.dart';
import 'auth_repository_api.dart';
import 'auth_repository_mock.dart';

/// `tokenStoreProvider` 는 `core/network/api_client.dart` 로 옮겼다
/// (2026-09-23, 공유 [ApiClient] 가 같은 저장소를 읽어야 해서). 부르는 쪽이
/// 안 고쳐도 되도록 여기서 그대로 다시 내보낸다.
export '../../../core/network/api_client.dart' show tokenStoreProvider;

/// 백엔드 교체 지점.
///
/// 기본은 `fastapi/`(계약: `fastapi/docs/api-contract.md`)에 붙는다. 서버 없이
/// 돌릴 때만 목업이다 — [useMockProvider] 참고(`USE_MOCK` · 「개발자 전용」).
/// 화면·위젯·컨트롤러는 수정하지 않는다.
final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => ref.watch(useMockProvider)
      ? MockAuthRepository(ref.watch(mockDbProvider))
      /* 🔴 **공유 [apiClientProvider] 를 넘긴다.** 안 넘기면
         `ApiAuthRepository` 가 자기 [ApiClient] 를 만들어, 로그인이 저장한
         토큰이 카드·영상·스쿼드 쪽에 **안 건너간다** — 2026-09-23 에 실서버에서
         전부 401 이었다. 시험: `test/core/shared_api_client_test.dart`. */
      : ApiAuthRepository(api: ref.watch(apiClientProvider)),
);

