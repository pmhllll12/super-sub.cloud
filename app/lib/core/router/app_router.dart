import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/presentation/screens/login_screen.dart';
import '../../features/auth/presentation/session_controller.dart';
import '../../features/home/presentation/screens/home_screen.dart';
import '../../features/profile/presentation/screens/profile_screen.dart';

/// GoRouter를 provider가 매번 다시 만들면 내비게이션 스택이 날아간다.
/// 그래서 라우터는 한 번만 만들고, 세션 변화는 ValueNotifier로 흘려보내
/// refreshListenable이 redirect를 다시 돌리게 한다.
///
/// **종목은 진입 조건이 아니다.** 예전에는 종목을 안 고르면 온보딩 화면으로
/// 보냈는데, 첫 화면이 질문 하나로 채워지는 것이 이상해 홈의 칩으로 옮겼다.
final routerProvider = Provider<GoRouter>((ref) {
  final refresh = ValueNotifier<int>(0);
  ref.onDispose(refresh.dispose);

  SessionState session = const SessionUnknown();

  ref.listen<SessionState>(sessionControllerProvider, (_, next) {
    session = next;
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

      if (path == '/login') return '/home';
      return null;
    },
    routes: [
      GoRoute(
        path: '/login',
        builder: (_, _) => const LoginScreen(),
      ),
      GoRoute(
        path: '/home',
        builder: (_, _) => const HomeScreen(),
      ),
      GoRoute(
        path: '/profile',
        builder: (_, _) => const ProfileScreen(),
      ),
    ],
  );
});
