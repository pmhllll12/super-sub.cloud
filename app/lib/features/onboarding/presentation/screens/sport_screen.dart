import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/sport/current_sport.dart';
import '../../../../core/widgets/async_view.dart';
import '../../../team/data/models/sport.dart';
import '../../../team/data/sport_providers.dart';

class SportScreen extends ConsumerWidget {
  const SportScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: const Text('종목 선택')),
      body: AsyncView<List<Sport>>(
        value: ref.watch(sportsProvider),
        isEmpty: (sports) => sports.isEmpty,
        emptyMessage: '선택할 수 있는 종목이 없습니다',
        onRetry: () => ref.invalidate(sportsProvider),
        data: (sports) => ListView(
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
      ),
    );
  }
}
