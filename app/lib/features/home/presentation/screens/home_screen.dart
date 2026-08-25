import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../../core/mock/mock_db.dart';
import '../../../../core/sport/current_sport.dart';
import '../../../../core/sport/sport.dart';
import '../../../auth/presentation/session_controller.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final session = ref.watch(sessionControllerProvider);
    final sportCode = ref.watch(currentSportProvider);
    final sports = ref.watch(mockDbProvider).sports;

    final nickname =
        session is SessionLoggedIn ? session.user.nickname : '';
    final sportName = sports
        .where((s) => s.code == sportCode)
        .map((s) => s.name)
        .join();

    return Scaffold(
      appBar: AppBar(
        title: const Text('홈'),
        actions: [
          IconButton(
            key: const Key('home-logout'),
            icon: const Icon(Icons.logout),
            tooltip: '로그아웃',
            onPressed: () =>
                ref.read(sessionControllerProvider.notifier).logout(),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            '$nickname 님, 안녕하세요',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 16),
          Card(
            child: ListTile(
              key: const Key('home-sport-switch'),
              title: Text(sportName),
              subtitle: const Text('종목 전환'),
              trailing: const Icon(Icons.swap_horiz),
              onTap: () => _showSportSheet(context, ref, sports),
            ),
          ),
          const SizedBox(height: 8),
          Card(
            child: ListTile(
              title: const Text('내 프로필'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => context.go('/profile'),
            ),
          ),
        ],
      ),
    );
  }

  void _showSportSheet(
    BuildContext context,
    WidgetRef ref,
    List<Sport> sports,
  ) {
    showModalBottomSheet<void>(
      context: context,
      builder: (sheetContext) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            for (final sport in sports)
              ListTile(
                title: Text(sport.name),
                onTap: () {
                  ref
                      .read(currentSportProvider.notifier)
                      .select(sport.code);
                  Navigator.of(sheetContext).pop();
                },
              ),
          ],
        ),
      ),
    );
  }
}
