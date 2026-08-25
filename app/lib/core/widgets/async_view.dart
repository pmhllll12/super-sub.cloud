import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 비동기 화면의 네 가지 상태를 한 곳에서 처리한다.
///
/// Mock이 지연·실패·빈 목록을 실제로 만들어내므로(스펙 4.3) 이 네 상태는
/// 개발 중에 계속 눈에 띈다. 그것이 Mock을 진짜처럼 만드는 이유다.
class AsyncView<T> extends StatelessWidget {
  const AsyncView({
    super.key,
    required this.value,
    required this.data,
    this.isEmpty,
    this.emptyMessage = '표시할 내용이 없습니다',
    this.onRetry,
  });

  final AsyncValue<T> value;
  final Widget Function(T data) data;
  final bool Function(T data)? isEmpty;
  final String emptyMessage;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return value.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('$e', textAlign: TextAlign.center),
            if (onRetry != null) ...[
              const SizedBox(height: 12),
              FilledButton(onPressed: onRetry, child: const Text('다시 시도')),
            ],
          ],
        ),
      ),
      data: (d) {
        if (isEmpty?.call(d) ?? false) {
          return Center(child: Text(emptyMessage));
        }
        return data(d);
      },
    );
  }
}
