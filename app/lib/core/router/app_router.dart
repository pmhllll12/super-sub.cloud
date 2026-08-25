import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/presentation/screens/login_screen.dart';
import '../../features/auth/presentation/session_controller.dart';
import '../../features/home/presentation/screens/home_screen.dart';
import '../../features/intro/presentation/screens/glitch_intro_screen.dart'
    show kIntroInkColor;
import '../widgets/ink_bleed.dart';
import '../../features/profile/presentation/screens/profile_screen.dart';

/// GoRouter를 provider가 매번 다시 만들면 내비게이션 스택이 날아간다.
/// 그래서 라우터는 한 번만 만들고, 세션 변화는 ValueNotifier로 흘려보내
/// refreshListenable이 redirect를 다시 돌리게 한다.
///
/// 로그인에서 홈으로 넘어가는 데 걸리는 시간. 로고가 하단 바 알약까지
/// 날아가는 시간이기도 하다 — 가로지르는 거리가 길어 짧으면 눈이 못 따라간다.
const Duration _kHomeTransition = Duration(milliseconds: 2500);

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
        // **로그인에서 홈으로 갈 때 잉크가 걷힌다.** 인트로가 나올 때 쓴 것과
        // 같은 지도·같은 알갱이라 두 전환이 한 재질로 읽힌다.
        //
        // 로고는 이 전환 위에 Hero로 얹혀 로그인 한가운데에서 하단 바의
        // 알약으로 날아간다 — 라우트 애니메이션이 그대로 비행 시간이 된다.
        pageBuilder: (context, state) => CustomTransitionPage<void>(
          key: state.pageKey,
          transitionDuration: _kHomeTransition,
          child: const HomeScreen(),
          // 로그인 화면은 잉크로 덮여 있지 않다 — 앞을 조금 떼어 그 사이에
          // 잉크가 배어들게 한다. 0으로 두면 첫 프레임에 화면이 통째로
          // 잉크색으로 뚝 바뀐다(ink_bleed.dart의 InkPeel 주석).
          transitionsBuilder: (_, animation, _, child) => InkPeel(
            animation: animation,
            ink: kIntroInkColor,
            coverUntil: 0.35,
            child: child,
          ),
        ),
      ),
      GoRoute(
        path: '/profile',
        builder: (_, _) => const ProfileScreen(),
      ),
    ],
  );
});
