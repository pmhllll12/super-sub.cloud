import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../auth/presentation/session_controller.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionControllerProvider);

    if (session is! SessionLoggedIn) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    final user = session.user;

    return Scaffold(
      appBar: AppBar(
        title: const Text('프로필'),
        actions: [
          IconButton(
            key: const Key('profile-edit'),
            icon: const Icon(Icons.edit),
            tooltip: '프로필 수정',
            onPressed: () => _showEditSheet(context, ref, user.nickname),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          ListTile(
            title: Text(
              user.nickname,
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            subtitle: Text(user.email),
          ),
          const Divider(),
          ListTile(
            title: const Text('가입일'),
            trailing: Text(
              '${user.createdAt.year}.${user.createdAt.month}.${user.createdAt.day}',
            ),
          ),
        ],
      ),
    );
  }

  void _showEditSheet(BuildContext context, WidgetRef ref, String current) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (sheetContext) => _EditNicknameSheet(current: current, ref: ref),
    );
  }
}

class _EditNicknameSheet extends StatefulWidget {
  const _EditNicknameSheet({required this.current, required this.ref});

  final String current;
  final WidgetRef ref;

  @override
  State<_EditNicknameSheet> createState() => _EditNicknameSheetState();
}

class _EditNicknameSheetState extends State<_EditNicknameSheet> {
  late final TextEditingController _controller =
      TextEditingController(text: widget.current);

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
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
            decoration: const InputDecoration(labelText: '닉네임'),
          ),
          const SizedBox(height: 16),
          FilledButton(
            key: const Key('profile-save'),
            onPressed: () {
              widget.ref
                  .read(sessionControllerProvider.notifier)
                  .updateNickname(_controller.text);
              Navigator.of(context).pop();
            },
            child: const Text('저장'),
          ),
        ],
      ),
    );
  }
}
