import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/chat_providers.dart';
import '../data/chat_repository.dart';

/// 대화창의 상태.
class ChatState {
  const ChatState({this.messages = const [], this.waiting = false, this.error});

  final List<ChatMessage> messages;

  /// 답을 기다리는 중인가. 화면이 이때 표시를 낸다.
  final bool waiting;

  final String? error;

  ChatState copyWith({
    List<ChatMessage>? messages,
    bool? waiting,
    String? error,
  }) =>
      ChatState(
        messages: messages ?? this.messages,
        waiting: waiting ?? this.waiting,
        error: error,
      );
}

class ChatController extends Notifier<ChatState> {
  @override
  ChatState build() => const ChatState();

  Future<void> send(String text) async {
    final question = text.trim();
    if (question.isEmpty) return;

    // 보낸 말은 먼저 붙인다 — 답을 기다리는 동안에도 화면에 남아야 한다.
    state = state.copyWith(
      messages: [...state.messages, ChatMessage(fromUser: true, text: question)],
      waiting: true,
    );
    try {
      final answer = await ref.read(chatRepositoryProvider).ask(question);
      state = state.copyWith(
        messages: [
          ...state.messages,
          ChatMessage(fromUser: false, text: answer),
        ],
        waiting: false,
      );
    } catch (e) {
      state = state.copyWith(waiting: false, error: '$e');
    }
  }
}

final chatControllerProvider =
    NotifierProvider<ChatController, ChatState>(ChatController.new);
