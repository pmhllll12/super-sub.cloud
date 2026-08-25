import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'chat_repository.dart';
import 'chat_repository_mock.dart';

/// 백엔드 교체 지점.
///
/// 진짜 에이전트가 나오면 이 한 줄을 ApiChatRepository로 바꾼다.
/// 화면·컨트롤러는 수정하지 않는다.
final chatRepositoryProvider = Provider<ChatRepository>(
  (ref) => MockChatRepository(),
);
