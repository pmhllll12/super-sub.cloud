import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/mock/mock_db.dart';
import 'auth_repository.dart';
import 'auth_repository_mock.dart';

/// 백엔드 교체 지점.
///
/// API가 나오면 이 한 줄을 ApiAuthRepository로 바꾼다.
/// 화면·위젯·컨트롤러는 수정하지 않는다.
final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => MockAuthRepository(ref.watch(mockDbProvider)),
);
