import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/dev/data_source.dart';
import '../../../core/mock/mock_db.dart';
import 'auth_repository.dart';
import 'auth_repository_api.dart';
import 'auth_repository_mock.dart';

/// 백엔드 교체 지점.
///
/// 기본은 `fastapi/`(계약: `fastapi/docs/api-contract.md`)에 붙는다. 서버 없이
/// 돌릴 때만 목업이다 — [useMockProvider] 참고(`USE_MOCK` · 「개발자 전용」).
/// 화면·위젯·컨트롤러는 수정하지 않는다.
final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => ref.watch(useMockProvider)
      ? MockAuthRepository(ref.watch(mockDbProvider))
      : ApiAuthRepository(),
);
