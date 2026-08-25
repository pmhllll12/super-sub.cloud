import 'package:flutter_riverpod/flutter_riverpod.dart';

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
    state = const SessionLoggedOut();
  }

  void updateNickname(String nickname) {
    final current = state;
    if (current is! SessionLoggedIn) return;
    state = SessionLoggedIn(current.user.copyWith(nickname: nickname));
  }
}

final sessionControllerProvider =
    NotifierProvider<SessionController, SessionState>(SessionController.new);
