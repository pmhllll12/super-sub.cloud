import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/presentation/screens/login_screen.dart';
import '../../features/auth/presentation/session_controller.dart';
import '../../features/home/presentation/screens/home_screen.dart';
import '../../features/onboarding/presentation/screens/sport_screen.dart';
import '../sport/current_sport.dart';

/// GoRouter를 provider가 매번 다시 만들면 내비게이션 스택이 날아간다.
/// 그래서 라우터는 한 번만 만들고, 세션·종목 변화는 ValueNotifier로 흘려보내
/// refreshListenable이 redirect를 다시 돌리게 한다.
final routerProvider = Provider<GoRouter>((ref) {
  final refresh = ValueNotifier<int>(0);
  ref.onDispose(refresh.dispose);

  SessionState session = const SessionUnknown();
  String? sport;

  ref.listen<SessionState>(sessionControllerProvider, (_, next) {
    session = next;
    refresh.value++;
  }, fireImmediately: true);

  ref.listen<String?>(currentSportProvider, (_, next) {
    sport = next;
    refresh.value++;
  }, fireImmediately: true);

  return GoRouter(
    initialLocation: '/home',
    refreshListenable: refresh,
    redirect: (context, state) {
      final path = state.matchedLocation;

      // 복원 중에는 아무 데도 보내지 않는다.
      if (session is SessionUnknown) return null;

      final loggedIn = session is SessionLoggedIn;
      if (!loggedIn) return path == '/login' ? null : '/login';

      // 로그인은 했는데 종목을 아직 안 골랐으면 온보딩으로.
      if (sport == null) {
        return path == '/onboarding/sport' ? null : '/onboarding/sport';
      }

      if (path == '/login' || path == '/onboarding/sport') return '/home';
      return null;
    },
    routes: [
      GoRoute(
        path: '/login',
        builder: (_, _) => const LoginScreen(),
      ),
      GoRoute(
        path: '/onboarding/sport',
        builder: (_, _) => const SportScreen(),
      ),
      GoRoute(
        path: '/home',
        builder: (_, _) => const HomeScreen(),
      ),
      GoRoute(
        path: '/profile',
        builder: (_, _) => const _Placeholder('프로필'),
      ),
    ],
  );
});

class _Placeholder extends StatelessWidget {
  const _Placeholder(this.label);

  final String label;

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: Text(label)),
        body: Center(child: Text(label)),
      );
}
