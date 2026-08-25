import '../../../core/mock/mock_db.dart';
import 'auth_repository.dart';
import 'models/app_user.dart';
import 'models/session.dart';

class MockAuthRepository implements AuthRepository {
  MockAuthRepository(this._db);

  final MockDb _db;

  Session? _current;

  static const _delay = Duration(milliseconds: 300);

  @override
  Future<Session> login({
    required String email,
    required String password,
  }) async {
    await Future<void>.delayed(_delay);
    final user = _db.findUserByEmail(email);
    if (user == null) {
      throw const AuthException('등록되지 않은 이메일입니다');
    }
    return _current = Session(user: user);
  }

  @override
  Future<Session> loginAs(String userId) async {
    await Future<void>.delayed(_delay);
    final user = _db.findUserById(userId);
    if (user == null) {
      throw const AuthException('존재하지 않는 사용자입니다');
    }
    return _current = Session(user: user);
  }

  @override
  Future<void> logout() async {
    await Future<void>.delayed(_delay);
    _current = null;
  }

  @override
  Future<AppUser> updateProfile({required String nickname}) async {
    await Future<void>.delayed(_delay);
    final session = _current;
    if (session == null) {
      throw const AuthException('로그인이 필요합니다');
    }
    final index = _db.users.indexWhere((u) => u.id == session.user.id);
    if (index < 0) {
      throw const AuthException('존재하지 않는 사용자입니다');
    }
    // 저장소에 실제로 써넣는다. 세션 상태만 바꾸면 로그아웃 후 다시
    // 로그인했을 때 이전 닉네임이 돌아온다.
    final updated = _db.users[index].copyWith(nickname: nickname);
    _db.users[index] = updated;
    _current = Session(user: updated);
    return updated;
  }

  @override
  Future<Session?> restoreSession() async {
    await Future<void>.delayed(_delay);
    return _current;
  }
}
