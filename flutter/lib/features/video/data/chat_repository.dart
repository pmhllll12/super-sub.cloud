/// 대화 한 줄.
class ChatMessage {
  const ChatMessage({required this.fromUser, required this.text});

  final bool fromUser;
  final String text;

  @override
  bool operator ==(Object other) =>
      other is ChatMessage &&
      other.fromUser == fromUser &&
      other.text == text;

  @override
  int get hashCode => Object.hash(fromUser, text);
}

class ChatException implements Exception {
  const ChatException(this.message);

  final String message;

  @override
  String toString() => message;
}

/// 영상 분석 에이전트와의 대화.
///
/// 화면이 아는 유일한 계약이다. 지금은 Mock이 답하고, 나중에 진짜 에이전트가
/// 붙으면 [chatRepositoryProvider] 한 줄만 바꾼다.
abstract class ChatRepository {
  /// 물음에 대한 답. 빈 물음은 [ChatException]이다.
  Future<String> ask(String question);
}
