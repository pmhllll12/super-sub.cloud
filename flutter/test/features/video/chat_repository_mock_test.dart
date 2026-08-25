import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/video/data/chat_repository_mock.dart';

import '../../contract/chat_repository_contract.dart';

void main() {
  runChatRepositoryContract('MockChatRepository', MockChatRepository.new);

  test('MockChatRepository 고유 규칙 — 응답은 즉시 오지 않는다', () async {
    final sw = Stopwatch()..start();
    await MockChatRepository().ask('안녕');
    sw.stop();
    expect(sw.elapsedMilliseconds, greaterThanOrEqualTo(300));
  });
}
