import 'models/app_user.dart';
import 'models/session.dart';

class AuthException implements Exception {
  const AuthException(this.message, {this.code, this.retryAfter});

  final String message;

  /// 서버 에러 `code` (계약: `{"error": {"code", "message"}}`) — 분기는 이걸로
  /// 한다. Mock 은 서버가 없어 늘 `null`이다.
  final String? code;

  /// 429 일 때 몇 초 기다려야 하는가(서버가 준 `Retry-After`, 정수 초).
  /// 429 가 아니거나 헤더가 없으면 `null` — 웹(`www/`)의 `ApiCallError.retryAfter`와
  /// 같은 성질이다.
  final int? retryAfter;

  @override
  String toString() => message;
}

/// 화면이 아는 유일한 인증 계약.
///
/// 구현체가 Mock인지 API인지 화면은 모른다. 교체는 authRepositoryProvider
/// 한 줄이다. 모든 메서드가 Future인 이유는, 동기 반환이 하나라도 있으면
/// API 전환 시 그 화면을 다시 짜야 하기 때문이다.
abstract class AuthRepository {
  Future<Session> login({required String email, required String password});

  /// 가입하고 **그 계정으로 로그인된 세션**을 돌려준다(계약 `POST /auth/signup`).
  ///
  /// 가입만 하고 끝내면 방금 친 비밀번호를 로그인 화면에서 한 번 더 치게 된다.
  /// 이미 있는 이메일이면 [AuthException](`EMAIL_ALREADY_EXISTS`)을 던진다.
  Future<Session> signup({
    required String email,
    required String password,
    required String nickname,
  });

  /// 구글이 준 **ID 토큰**으로 로그인한다(계약 `POST /auth/google`). 처음 보는
  /// 구글 계정이면 서버가 그 자리에서 가입까지 한다 — 가입 경로가 따로 없다.
  Future<Session> loginWithGoogle({required String idToken});

  /// 시험이 로그인된 화면을 준비할 때 쓰는 바로 진입. 앱 화면에는 버튼이 없다.
  Future<Session> loginAs(String userId);

  Future<void> logout();

  /// 로그인한 사용자의 프로필을 수정하고 **서버가 확정한 사용자**를 돌려준다.
  ///
  /// 호출부는 자기가 보낸 값이 아니라 돌려받은 값을 쓴다 — id·생성 시각 같은
  /// 서버 소유 필드가 응답에만 있기 때문이다(스펙 4.1 규칙 3).
  /// 프로필을 고치고 **서버가 확정한 사용자**를 돌려준다(`PATCH /me`).
  ///
  /// 🔴 **보낸 칸만 바뀐다** — 둘 다 선택이고, 안 보내면 그대로다.
  /// 닉네임이 겹치면 409 `NICKNAME_ALREADY_EXISTS` 다.
  Future<AppUser> updateProfile({String? nickname, bool? nicknameSearchable});

  Future<Session?> restoreSession();
}
