import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/sport/current_sport.dart';
import '../data/auth_providers.dart';
import '../data/google_id_token.dart';
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

  Future<void> signup(String email, String password, String nickname) async {
    final session = await ref
        .read(authRepositoryProvider)
        .signup(email: email, password: password, nickname: nickname);
    state = SessionLoggedIn(session.user);
  }

  /// 구글 창을 띄우고, 토큰을 받으면 서버에 로그인한다. 창을 닫았으면 아무 일도
  /// 없던 것으로 한다 — 오류가 아니다.
  Future<void> loginWithGoogle() async {
    final idToken = await ref.read(googleIdTokenSourceProvider).fetchIdToken();
    if (idToken == null || !ref.mounted) return;
    final session = await ref
        .read(authRepositoryProvider)
        .loginWithGoogle(idToken: idToken);
    state = SessionLoggedIn(session.user);
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

  /// **탈퇴한다** — 계정과 파생 데이터가 함께 지워진다. 되돌릴 수 없다.
  ///
  /// 🔴 **서버가 지운 뒤에 로그아웃 상태로 간다.** 먼저 상태를 바꾸면
  /// 실패했을 때 **계정은 살아 있는데 로그인 화면에 서 있게** 된다 — 사람은
  /// 탈퇴된 줄 안다. 실패는 그대로 올려 화면이 사유를 보여 준다.
  ///
  /// 🔴 [password] 가 비어 있으면 리포지토리가 **아예 안 보낸다** — 구글로만
  /// 가입한 계정에는 확인할 비밀번호가 없다.
  Future<void> deleteAccount({String? password}) async {
    await ref.read(authRepositoryProvider).deleteAccount(password: password);
    // 로그아웃과 같은 뒷정리 — 종목은 사용자에게 매달린 컨텍스트다.
    ref.read(currentSportProvider.notifier).clear();
    state = const SessionLoggedOut();
  }

  Future<void> updateNickname(String nickname) =>
      _patch(nickname: nickname);

  /// 🔴 **지인 검색 노출** — 닉네임으로 나를 찾을 수 있는가. 용병 매칭의
  /// `is_searchable` 과는 **다른 값이다**(계약).
  Future<void> setNicknameSearchable(bool value) =>
      _patch(nicknameSearchable: value);

  Future<void> _patch({String? nickname, bool? nicknameSearchable}) async {
    final updated = await ref.read(authRepositoryProvider).updateProfile(
          nickname: nickname,
          nicknameSearchable: nicknameSearchable,
        );
    if (!ref.mounted) return;
    // 보낸 값이 아니라 돌려받은 사용자로 상태를 채운다(스펙 4.1 규칙 3).
    state = SessionLoggedIn(updated);
  }
}

final sessionControllerProvider =
    NotifierProvider<SessionController, SessionState>(SessionController.new);
