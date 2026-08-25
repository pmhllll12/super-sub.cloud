import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/mock/mock_db.dart';
import '../../../../core/sport/current_sport.dart';

class SportScreen extends ConsumerWidget {
  const SportScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sports = ref.watch(mockDbProvider).sports;

    return Scaffold(
      appBar: AppBar(title: const Text('종목 선택')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Text(
            '어떤 종목을 하시나요?',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 16),
          for (final sport in sports)
            Card(
              child: ListTile(
                title: Text(sport.name),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => ref
                    .read(currentSportProvider.notifier)
                    .select(sport.code),
              ),
            ),
        ],
      ),
    );
  }
}
