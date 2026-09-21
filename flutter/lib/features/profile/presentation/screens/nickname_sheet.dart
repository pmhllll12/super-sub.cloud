import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../auth/presentation/session_controller.dart';

void showNicknameSheet(BuildContext context, String current) {
  showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (_) => _EditNicknameSheet(current: current),
  );
}

/// 서브뷰는 부모의 [WidgetRef]를 생성자로 받지 않는다.
///
/// 부모 ref를 넘기는 방식은 부모가 시트보다 오래 살아 있을 때만 우연히
/// 동작하므로, 시트가 스스로 자기 ref를 갖는 것을 기본형으로 둔다.
class _EditNicknameSheet extends ConsumerStatefulWidget {
  const _EditNicknameSheet({required this.current});

  final String current;

  @override
  ConsumerState<_EditNicknameSheet> createState() => _EditNicknameSheetState();
}

class _EditNicknameSheetState extends ConsumerState<_EditNicknameSheet> {
  late final TextEditingController _controller =
      TextEditingController(text: widget.current);

  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  /// login_screen.dart와 같은 관용구다. 저장은 리포지토리를 거치므로
  /// 지연·실패가 실제로 발생한다.
  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('닉네임 수정'),
          const SizedBox(height: 12),
          TextField(
            key: const Key('profile-nickname'),
            controller: _controller,
            enabled: !_busy,
            decoration: const InputDecoration(labelText: '닉네임'),
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            /* 🔴 **겹치는 닉네임은 서버가 막는다**(409
               `NICKNAME_ALREADY_EXISTS`) — 유일 제약이 붙어 있다. 그 문구를
               그대로 보여 준다. */
            Text(
              _error!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ],
          const SizedBox(height: 16),
          FilledButton(
            key: const Key('profile-save'),
            onPressed: _busy
                ? null
                : () => _run(() async {
                      await ref
                          .read(sessionControllerProvider.notifier)
                          .updateNickname(_controller.text);
                      // 실패하면 _run이 예외를 잡아 오류를 띄우므로
                      // 여기까지 오지 않는다 — 시트는 성공했을 때만 닫힌다.
                      if (context.mounted) Navigator.of(context).pop();
                    }),
            child: _busy
                ? const SizedBox(
                    height: 18,
                    width: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('저장'),
          ),
        ],
      ),
    );
  }
}
