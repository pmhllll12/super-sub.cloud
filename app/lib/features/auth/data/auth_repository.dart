import 'models/session.dart';

class AuthException implements Exception {
  const AuthException(this.message);

  final String message;

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

  /// 개발용 바로 진입. 릴리즈 빌드의 UI에서는 호출되지 않는다.
  Future<Session> loginAs(String userId);

  Future<void> logout();

  Future<Session?> restoreSession();
}
