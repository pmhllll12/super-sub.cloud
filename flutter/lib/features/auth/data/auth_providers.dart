import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/dev/data_source.dart';
import '../../../core/mock/mock_db.dart';
import 'auth_repository.dart';
import 'auth_repository_api.dart';
import 'auth_repository_mock.dart';
import 'token_store.dart';

/// 백엔드 교체 지점.
///
/// 기본은 `fastapi/`(계약: `fastapi/docs/api-contract.md`)에 붙는다. 서버 없이
/// 돌릴 때만 목업이다 — [useMockProvider] 참고(`USE_MOCK` · 「개발자 전용」).
/// 화면·위젯·컨트롤러는 수정하지 않는다.
final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => ref.watch(useMockProvider)
      ? MockAuthRepository(ref.watch(mockDbProvider))
      : ApiAuthRepository(tokens: ref.watch(tokenStoreProvider)),
);

/// 로그인 토큰을 어디에 남길지 — 기본은 Keystore·Keychain(미결 `min` 25번).
///
/// 🔴 **위젯 시험은 이것을 갈아 끼운다.** 진짜 저장소는 플랫폼 채널로 오가는데
/// 위젯 시험의 **가짜 시계에서는 그 응답이 영영 안 온다** — 세션 복원이 안
/// 끝나서 라우터가 첫 화면에 멈춘다(2026-09-17에 스모크 시험이 그렇게 깨졌다).
/// 예외가 아니라 **안 오는 것**이라 `try/catch` 로는 못 푼다.
final tokenStoreProvider = Provider<TokenStore>(
  (ref) => const SecureTokenStore(),
);
