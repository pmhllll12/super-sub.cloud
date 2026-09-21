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
  Future<Session> signup({
    required String email,
    required String password,
    required String nickname,
  }) async {
    await Future<void>.delayed(_delay);
    if (_db.findUserByEmail(email) != null) {
      throw const AuthException(
        '이미 가입된 이메일입니다',
        code: 'EMAIL_ALREADY_EXISTS',
      );
    }
    final user = AppUser(
      id: 'u-${DateTime.now().microsecondsSinceEpoch}',
      email: email,
      nickname: nickname,
      createdAt: DateTime.now(),
    );
    // 저장소에 실제로 써넣는다 — 로그아웃 뒤 같은 이메일로 다시 들어올 수 있어야 한다.
    _db.users.add(user);
    return _current = Session(user: user);
  }

  /// 서버가 없어 토큰을 검증할 수 없다 — 빈 토큰만 거절하고, 나머지는
  /// 데이터가 있는 개인 사용자로 들인다.
  @override
  Future<Session> loginWithGoogle({required String idToken}) async {
    await Future<void>.delayed(_delay);
    if (idToken.isEmpty) {
      throw const AuthException(
        '구글 토큰을 확인할 수 없습니다',
        code: 'INVALID_GOOGLE_TOKEN',
      );
    }
    return _current = Session(user: _db.findUserById(MockDb.playerId)!);
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
  Future<AppUser> updateProfile({
    String? nickname,
    bool? nicknameSearchable,
  }) async {
    await Future<void>.delayed(_delay);
    final session = _current;
    if (session == null) {
      throw const AuthException('로그인이 필요합니다');
    }
    final index = _db.users.indexWhere((u) => u.id == session.user.id);
    if (index < 0) {
      throw const AuthException('존재하지 않는 사용자입니다');
    }
    /* 🔴 **겹치는 닉네임은 거절한다** — 서버가 409 NICKNAME_ALREADY_EXISTS
       를 낸다(유일 제약). Mock 이 받아 주면 그 화면을 안 만들게 된다. */
    if (nickname != null &&
        _db.users.any((u) => u.id != session.user.id && u.nickname == nickname)) {
      throw const AuthException(
        '이미 쓰는 닉네임입니다',
        code: 'NICKNAME_ALREADY_EXISTS',
      );
    }
    // 저장소에 실제로 써넣는다. 세션 상태만 바꾸면 로그아웃 후 다시
    // 로그인했을 때 이전 닉네임이 돌아온다.
    // 🔴 보낸 칸만 바뀐다 — copyWith 가 null 을 「안 바꿈」으로 다룬다.
    final updated = _db.users[index].copyWith(
      nickname: nickname,
      isNicknameSearchable: nicknameSearchable,
    );
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
