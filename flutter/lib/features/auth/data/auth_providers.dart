import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth_repository.dart';
import 'auth_repository_api.dart';

/// 백엔드 교체 지점.
///
/// `fastapi/`(계약: `fastapi/docs/api-contract.md`)에 붙는다.
/// 화면·위젯·컨트롤러는 수정하지 않는다.
final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => ApiAuthRepository(),
);
