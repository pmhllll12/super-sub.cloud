import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/sport/current_sport.dart';
import '../data/auth_providers.dart';
import '../data/models/app_user.dart';

sealed class SessionState {
  const SessionState();
}

/// 앱 시작 직후, 복원 시도가 끝나기 전 상태.
class SessionUnknown extends SessionState {
  const SessionUnknown();
}

class SessionLoggedOut extends SessionState {
  const SessionLoggedOut();
}

class SessionLoggedIn extends SessionState {
  const SessionLoggedIn(this.user);

  final AppUser user;
}

class SessionController extends Notifier<SessionState> {
  @override
  SessionState build() {
    _restore();
    return const SessionUnknown();
  }

  Future<void> _restore() async {
    final session = await ref.read(authRepositoryProvider).restoreSession();
    // 복원을 기다리는 동안 컨테이너가 폐기되었거나(테스트·화면 이탈),
    // 로그인·로그아웃이 상태를 이미 바꿨다면 아무것도 하지 않는다.
    if (!ref.mounted || state is! SessionUnknown) return;
    state = session == null
        ? const SessionLoggedOut()
        : SessionLoggedIn(session.user);
  }

  Future<void> login(String email, String password) async {
    try {
      final session = await ref
          .read(authRepositoryProvider)
          .login(email: email, password: password);
      state = SessionLoggedIn(session.user);
    } catch (_) {
      state = const SessionLoggedOut();
      rethrow;
    }
  }

  Future<void> loginAs(String userId) async {
    final session = await ref.read(authRepositoryProvider).loginAs(userId);
    state = SessionLoggedIn(session.user);
  }

  Future<void> logout() async {
    await ref.read(authRepositoryProvider).logout();
    // 종목은 사용자에게 매달린 컨텍스트다. 지우지 않으면 다른 계정으로
    // 로그인했을 때 이전 사용자의 종목으로 홈에 착지하고, 단계 2부터는
    // 모든 리포지토리 호출이 sportCode로 키잉되므로(스펙 3절) 잘못된
    // 데이터를 부르게 된다.
    ref.read(currentSportProvider.notifier).clear();
    state = const SessionLoggedOut();
  }

  Future<void> updateNickname(String nickname) async {
    final updated = await ref
        .read(authRepositoryProvider)
        .updateProfile(nickname: nickname);
    if (!ref.mounted) return;
    // 보낸 값이 아니라 돌려받은 사용자로 상태를 채운다(스펙 4.1 규칙 3).
    state = SessionLoggedIn(updated);
  }
}

final sessionControllerProvider =
    NotifierProvider<SessionController, SessionState>(SessionController.new);
