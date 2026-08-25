import 'package:flutter/foundation.dart' show kDebugMode;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/mock/mock_db.dart';
import '../session_controller.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();

  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

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
    final controller = ref.read(sessionControllerProvider.notifier);

    return Scaffold(
      appBar: AppBar(title: const Text('로그인')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              key: const Key('login-email'),
              controller: _email,
              decoration: const InputDecoration(labelText: '이메일'),
              keyboardType: TextInputType.emailAddress,
            ),
            const SizedBox(height: 12),
            TextField(
              key: const Key('login-password'),
              controller: _password,
              decoration: const InputDecoration(labelText: '비밀번호'),
              obscureText: true,
            ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
            const SizedBox(height: 20),
            FilledButton(
              key: const Key('login-submit'),
              onPressed: _busy
                  ? null
                  : () => _run(
                        () => controller.login(_email.text, _password.text),
                      ),
              child: _busy
                  ? const SizedBox(
                      height: 18,
                      width: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('로그인'),
            ),
            if (kDebugMode) ...[
              const SizedBox(height: 32),
              const Divider(),
              const SizedBox(height: 8),
              Text(
                '개발용 바로 진입',
                style: Theme.of(context).textTheme.labelLarge,
              ),
              const SizedBox(height: 8),
              _DevLoginButton(
                label: '개인 사용자 (데이터 있음)',
                userId: MockDb.playerId,
                busy: _busy,
                onTap: (id) => _run(() => controller.loginAs(id)),
              ),
              _DevLoginButton(
                label: '팀 관리자',
                userId: MockDb.managerId,
                busy: _busy,
                onTap: (id) => _run(() => controller.loginAs(id)),
              ),
              _DevLoginButton(
                label: '신규 가입자 (데이터 0건)',
                userId: MockDb.newbieId,
                busy: _busy,
                onTap: (id) => _run(() => controller.loginAs(id)),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _DevLoginButton extends StatelessWidget {
  const _DevLoginButton({
    required this.label,
    required this.userId,
    required this.busy,
    required this.onTap,
  });

  final String label;
  final String userId;
  final bool busy;
  final void Function(String userId) onTap;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton(
      onPressed: busy ? null : () => onTap(userId),
      child: Text(label),
    );
  }
}
