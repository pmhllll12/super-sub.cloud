import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/network/api_config.dart';
import 'auth_repository.dart';
import 'models/app_user.dart';
import 'models/session.dart';

/// `fastapi/` 백엔드에 붙는 실제 구현.
///
/// 계약은 `fastapi/docs/api-contract.md` — 실패 응답은 전부
/// `{"error": {"code", "message"}}` 형태이고, 여기서는 `message`를 그대로
/// [AuthException]에 담는다(코드는 화면 쪽에서 필요해지면 그때 노출한다).
///
/// 세션은 [MockAuthRepository]와 마찬가지로 **메모리에만** 둔다 — 앱을
/// 새로 켜면 다시 로그인해야 한다. 기기 재시작 후에도 로그인 상태를
/// 유지하려면 토큰을 영속 저장소(shared_preferences 등)에 옮겨야 한다.
class ApiAuthRepository implements AuthRepository {
  String? _token;
  Session? _current;

  @override
  Future<Session> login({
    required String email,
    required String password,
  }) async {
    final tokenBody = await _post('/auth/login', {
      'email': email,
      'password': password,
    });
    _token = tokenBody['access_token'] as String;
    return _current = Session(user: await _fetchMe());
  }

  @override
  Future<Session> loginAs(String userId) {
    throw const AuthException('개발용 바로 진입은 API 모드에서 지원하지 않습니다');
  }

  @override
  Future<void> logout() async {
    _token = null;
    _current = null;
  }

  @override
  Future<AppUser> updateProfile({required String nickname}) {
    // 계약 문서 5절: PATCH /me는 아직 범위 밖이다.
    throw const AuthException('닉네임 수정은 아직 지원되지 않습니다');
  }

  @override
  Future<Session?> restoreSession() async => _current;

  Future<AppUser> _fetchMe() async {
    final body = await _get('/me');
    return AppUser(
      id: body['id'] as String,
      email: body['email'] as String,
      nickname: body['nickname'] as String,
      createdAt: DateTime.parse(body['created_at'] as String),
    );
  }

  Future<Map<String, dynamic>> _post(
    String path,
    Map<String, dynamic> body,
  ) async {
    final response = await _send(
      () => http.post(
        Uri.parse('$apiBaseUrl$path'),
        headers: _headers(),
        body: jsonEncode(body),
      ),
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> _get(String path) async {
    final response = await _send(
      () => http.get(Uri.parse('$apiBaseUrl$path'), headers: _headers()),
    );
    return _decode(response);
  }

  Future<http.Response> _send(
    Future<http.Response> Function() request,
  ) async {
    try {
      return await request();
    } on http.ClientException catch (e) {
      throw AuthException('서버에 연결할 수 없습니다: ${e.message}');
    }
  }

  Map<String, String> _headers() => {
        'Content-Type': 'application/json',
        if (_token != null) 'Authorization': 'Bearer $_token',
      };

  Map<String, dynamic> _decode(http.Response response) {
    final decoded = response.body.isEmpty
        ? <String, dynamic>{}
        : jsonDecode(response.body) as Map<String, dynamic>;
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return decoded;
    }
    final error = decoded['error'] as Map<String, dynamic>?;
    throw AuthException(
      (error?['message'] as String?) ?? '알 수 없는 오류 (${response.statusCode})',
    );
  }
}
