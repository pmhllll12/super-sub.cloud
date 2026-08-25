import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/video/data/chat_repository.dart';

/// ChatRepository의 모든 구현체가 지켜야 하는 계약.
///
/// 지금은 Mock에 물려 돌리고, 진짜 에이전트가 나오면 같은 파일을 그쪽에
/// 물린다.
void runChatRepositoryContract(
  String name,
  ChatRepository Function() build,
) {
  group('$name — ChatRepository 계약', () {
    late ChatRepository repo;

    setUp(() => repo = build());

    test('물음에 빈 답을 주지 않는다', () async {
      final answer = await repo.ask('포지션이 어디에 맞나요');
      expect(answer.trim(), isNotEmpty);
    });

    test('빈 물음은 ChatException을 던진다', () async {
      expect(() => repo.ask('   '), throwsA(isA<ChatException>()));
    });

    test('모르는 것을 물어도 답은 돌아온다', () async {
      final answer = await repo.ask('오늘 점심 뭐 먹지');
      expect(answer.trim(), isNotEmpty);
    });
  });
}
