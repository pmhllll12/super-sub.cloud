import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/mock/mock_db.dart';
import 'models/sport.dart';
import 'sport_repository.dart';
import 'sport_repository_mock.dart';

/// 백엔드 교체 지점.
///
/// API가 나오면 이 한 줄을 ApiSportRepository로 바꾼다.
/// 화면·위젯·컨트롤러는 수정하지 않는다.
final sportRepositoryProvider = Provider<SportRepository>(
  (ref) => MockSportRepository(ref.watch(mockDbProvider)),
);

/// 화면이 watch하는 종목 목록. 로딩·오류·빈 목록이 AsyncValue로 들어온다.
///
/// retry를 끈 이유: Riverpod 3는 실패한 provider를 백오프로 자동 재시도하고
/// 그동안 상태를 AsyncLoading으로 유지한다. 그러면 화면이 오류 대신 로딩만
/// 계속 보여주게 되어 스펙 6절이 요구하는 "사유 + 재시도 버튼"이 영영
/// 나타나지 않는다. 재시도는 사용자가 누르는 것으로 둔다(invalidate).
final sportsProvider = FutureProvider<List<Sport>>(
  (ref) => ref.watch(sportRepositoryProvider).sports(),
  retry: (_, _) => null,
);
