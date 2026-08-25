import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../data/chat_repository.dart';
import 'chat_controller.dart';

const Color _kOnDark = Color(0xFFFFFFFF);

/// 영상 분석 에이전트와 나누는 대화.
///
/// 유리 판 **안에** 들어간다. 그래서 여기서는 유리를 또 쓰지 않는다 — 말풍선은
/// 흐림 없이 색만 얹은 한 겹이다(refractive_glass.dart 주석).
class ChatPane extends ConsumerStatefulWidget {
  const ChatPane({super.key});

  @override
  ConsumerState<ChatPane> createState() => _ChatPaneState();
}

class _ChatPaneState extends ConsumerState<ChatPane> {
  final _input = TextEditingController();
  final _scroll = ScrollController();

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final text = _input.text;
    if (text.trim().isEmpty) return;
    _input.clear();
    await ref.read(chatControllerProvider.notifier).send(text);
    if (!mounted) return;
    // 새 말이 붙으면 맨 아래로 내린다.
    if (_scroll.hasClients) {
      await _scroll.animateTo(
        _scroll.position.maxScrollExtent,
        duration: const Duration(milliseconds: 240),
        curve: Curves.easeOut,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final chat = ref.watch(chatControllerProvider);

    return Column(
      children: [
        Expanded(
          child: chat.messages.isEmpty && !chat.waiting
              ? const _Empty()
              : ListView.builder(
                  controller: _scroll,
                  padding: const EdgeInsets.fromLTRB(14, 16, 14, 8),
                  itemCount: chat.messages.length + (chat.waiting ? 1 : 0),
                  itemBuilder: (context, i) {
                    if (i == chat.messages.length) return const _Typing();
                    return _Bubble(message: chat.messages[i]);
                  },
                ),
        ),
        if (chat.error case final error?)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14),
            child: Text(
              error,
              style: const TextStyle(color: Color(0xFFFF8A80), fontSize: 12),
            ),
          ),
        _inputRow(chat.waiting),
      ],
    );
  }

  Widget _inputRow(bool waiting) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 4, 12, 12),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              key: const Key('chat-input'),
              controller: _input,
              enabled: !waiting,
              minLines: 1,
              maxLines: 3,
              textInputAction: TextInputAction.send,
              onSubmitted: (_) => _send(),
              style: const TextStyle(color: _kOnDark, fontSize: 14),
              cursorColor: _kOnDark,
              decoration: InputDecoration(
                isDense: true,
                hintText: '영상 분석에 대해 물어보세요',
                hintStyle: TextStyle(
                  color: _kOnDark.withValues(alpha: 0.45),
                  fontSize: 14,
                ),
                filled: true,
                fillColor: Colors.white.withValues(alpha: 0.08),
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(18),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            key: const Key('chat-send'),
            color: _kOnDark,
            icon: const Icon(Symbols.send, weight: 300),
            tooltip: '보내기',
            onPressed: waiting ? null : _send,
          ),
        ],
      ),
    );
  }
}

class _Empty extends StatelessWidget {
  const _Empty();

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 28),
          child: Text(
            '분석에 대해 궁금한 것을 물어보세요.\n포지션, 실력 축, 크레딧 같은 것들입니다.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: _kOnDark.withValues(alpha: 0.55),
              fontSize: 13,
              height: 1.6,
            ),
          ),
        ),
      );
}

class _Bubble extends StatelessWidget {
  const _Bubble({required this.message});

  final ChatMessage message;

  @override
  Widget build(BuildContext context) {
    final mine = message.fromUser;
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 5),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.sizeOf(context).width * 0.62,
        ),
        decoration: BoxDecoration(
          // 흐림 없이 색만 — 이 판은 이미 유리 안이다.
          color: Colors.white.withValues(alpha: mine ? 0.18 : 0.08),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Text(
          message.text,
          style: const TextStyle(color: _kOnDark, fontSize: 14, height: 1.5),
        ),
      ),
    );
  }
}

class _Typing extends StatelessWidget {
  const _Typing();

  @override
  Widget build(BuildContext context) => Align(
        alignment: Alignment.centerLeft,
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 5),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(14),
          ),
          child: SizedBox(
            width: 18,
            height: 18,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              color: _kOnDark.withValues(alpha: 0.7),
            ),
          ),
        ),
      );
}
