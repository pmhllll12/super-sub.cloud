import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../auth/presentation/session_controller.dart';

void showDeleteAccountSheet(BuildContext context) {
  showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    builder: (_) => const _DeleteAccountSheet(),
  );
}

/// 회원 탈퇴 — **되돌릴 수 없다.**
///
/// 🔴 **무엇이 사라지는지 먼저 말한다.** 계약(2장)이 지우는 것은 계정만이
/// 아니다 — 카드·호칭·소속, 그리고 영상 → 분석 작업 → 지표 → 리포트 체인이
/// 함께 간다(SEC-006). 「정말 탈퇴하시겠습니까?」만 물으면 사람은 계정 하나
/// 지우는 줄 안다.
///
/// 🔴 **비밀번호 칸을 비워 둘 수 있다** — 구글로만 가입한 계정에는 확인할
/// 비밀번호가 **없다.** 필수로 만들면 그 사람은 탈퇴할 방법이 사라진다
/// (계약 2장). 빈 값이면 리포지토리가 아예 안 보낸다.
class _DeleteAccountSheet extends ConsumerStatefulWidget {
  const _DeleteAccountSheet();

  @override
  ConsumerState<_DeleteAccountSheet> createState() =>
      _DeleteAccountSheetState();
}

class _DeleteAccountSheetState extends ConsumerState<_DeleteAccountSheet> {
  final _password = TextEditingController();

  /// 🔴 **한 번 더 확인한다** — 되돌릴 수 없는 일이다. 단추 하나로 끝나면
  /// 잘못 눌러서 계정이 사라진다(영상 지우기와 같은 처리).
  bool _armed = false;

  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _password.dispose();
    super.dispose();
  }

  Future<void> _delete() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref
          .read(sessionControllerProvider.notifier)
          .deleteAccount(password: _password.text);
      /* 계정이 없어졌다 — 라우터의 redirect 가 로그인으로 보낸다. 시트만
         닫으면 된다. 🔴 **실패하면 여기까지 안 온다** — 아래 catch 가 잡아
         사유를 보여 주고 시트는 열린 채로 남는다. */
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = '$e';
          // 🔴 실패했으면 **확인 단계를 되돌린다** — 「정말 탈퇴합니다」가
          //    눌린 채로 남으면 다음 한 번에 또 나간다.
          _armed = false;
        });
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final danger = Theme.of(context).colorScheme.error;
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
          Text(
            '회원 탈퇴',
            style: TextStyle(
              color: danger,
              fontSize: 16,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 10),
          const Text(
            '계정과 함께 선수 카드 · 호칭 · 팀 소속, 그리고 올린 영상과 그 분석 '
            '리포트가 모두 지워집니다. 되돌릴 수 없습니다.',
            style: TextStyle(fontSize: 13, height: 1.5),
          ),
          const SizedBox(height: 16),
          TextField(
            key: const Key('profile-delete-password'),
            controller: _password,
            enabled: !_busy,
            obscureText: true,
            decoration: const InputDecoration(
              labelText: '비밀번호',
              // 🔴 구글로만 가입한 사람에게 「왜 비어 있어도 되는지」를 말해 준다.
              helperText: '구글로 가입했다면 비워 두세요',
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(
              _error!,
              key: const Key('profile-delete-error'),
              style: TextStyle(color: danger),
            ),
          ],
          const SizedBox(height: 16),
          if (!_armed)
            OutlinedButton(
              key: const Key('profile-delete-arm'),
              onPressed: _busy ? null : () => setState(() => _armed = true),
              style: OutlinedButton.styleFrom(
                foregroundColor: danger,
                side: BorderSide(color: danger),
              ),
              child: const Text('탈퇴하기'),
            )
          else
            Row(
              children: [
                Expanded(
                  child: FilledButton(
                    key: const Key('profile-delete-confirm'),
                    onPressed: _busy ? null : _delete,
                    style: FilledButton.styleFrom(backgroundColor: danger),
                    child: Text(_busy ? '탈퇴하는 중…' : '정말 탈퇴합니다'),
                  ),
                ),
                const SizedBox(width: 8),
                TextButton(
                  key: const Key('profile-delete-cancel'),
                  onPressed: _busy ? null : () => setState(() => _armed = false),
                  child: const Text('취소'),
                ),
              ],
            ),
        ],
      ),
    );
  }
}
