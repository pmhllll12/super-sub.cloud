import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/router/app_router.dart';
import 'core/theme/app_theme.dart';
import 'features/intro/presentation/intro_gate.dart';

class SuperSubApp extends ConsumerWidget {
  const SuperSubApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp.router(
      title: 'Super-Sub',
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      routerConfig: ref.watch(routerProvider),
      // 인트로는 라우트가 아니라 모든 라우트 위에 얹는 겹이다 —
      // 이유는 IntroGate의 주석 참고.
      builder: (context, child) {
        final content = child ?? const SizedBox();
        if (!ref.watch(introEnabledProvider)) return content;
        return IntroGate(child: content);
      },
    );
  }
}
