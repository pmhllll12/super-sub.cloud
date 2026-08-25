import '../../../core/mock/mock_db.dart';
import 'auth_repository.dart';
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
  Future<Session?> restoreSession() async {
    await Future<void>.delayed(_delay);
    return _current;
  }
}
