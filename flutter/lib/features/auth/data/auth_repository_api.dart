import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/network/api_config.dart';
import 'auth_repository.dart';
import 'models/app_user.dart';
import 'models/session.dart';
import 'token_store.dart';

/// `fastapi/` 백엔드에 붙는 실제 구현.
///
/// 계약은 `fastapi/docs/api-contract.md` — 실패 응답은 전부
/// `{"error": {"code", "message"}}` 형태이고, `code`와 `Retry-After` 헤더를
/// 함께 [AuthException]에 담는다 — 429 `TOO_MANY_REQUESTS` 를 다른 실패와
/// 가르는 유일한 수단이다(미결 `jin` 2번, 웹의 `ApiCallError`와 같은 모양).
///
/// 🔴 **정정 (2026-09-17, 미결 `min` 25번 해소).** 앞서 이 자리에 「세션은
/// 메모리에만 둔다 — 앱을 새로 켜면 다시 로그인해야 한다」고 적혀 있었다.
/// 이제 **토큰을 [TokenStore] 에 남긴다**(기본은 Keystore·Keychain) — 앱을
/// 완전히 종료했다 열어도 로그인 상태가 이어진다.
///
/// 🔴 **남기는 것은 토큰뿐이고 사용자는 안 남긴다.** 켤 때마다 `/me` 로 다시
/// 받는다 — 그래야 닉네임·프로필이 딴 데서 바뀌어도 낡은 값을 안 보여 주고,
/// **토큰이 만료·폐기됐으면 그 자리에서 드러난다**(저장한 사용자를 믿으면
/// 로그인된 것처럼 보이다가 첫 요청에서 튕긴다).
class ApiAuthRepository implements AuthRepository {
  ApiAuthRepository({TokenStore? tokens, http.Client? client})
      : _tokens = tokens ?? const SecureTokenStore(),
        _client = client ?? http.Client();

  final TokenStore _tokens;
  final http.Client _client;
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
    await _remember(tokenBody['access_token'] as String);
    return _current = Session(user: await _fetchMe());
  }

  @override
  Future<Session> signup({
    required String email,
    required String password,
    required String nickname,
  }) async {
    // 가입 응답은 사용자만 주고 토큰은 안 준다(계약) — 이어서 로그인한다.
    await _post('/auth/signup', {
      'email': email,
      'password': password,
      'nickname': nickname,
    });
    return login(email: email, password: password);
  }

  @override
  Future<Session> loginWithGoogle({required String idToken}) async {
    // 🔴 access_token 이 아니라 id_token 이다 — 바꿔 보내면 서명 검증에서 401.
    // 응답이 비밀번호 로그인과 같아 이후 흐름을 그대로 잇는다.
    final tokenBody = await _post('/auth/google', {'id_token': idToken});
    await _remember(tokenBody['access_token'] as String);
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
    // 🔴 저장소에서도 지운다 — 안 지우면 다음에 켤 때 로그아웃한 계정으로
    //    되돌아간다(「로그아웃했는데 왜 로그인돼 있냐」가 된다).
    await _tokens.clear();
  }

  @override
  Future<AppUser> updateProfile({required String nickname}) {
    // 계약 문서 5절: PATCH /me는 아직 범위 밖이다.
    throw const AuthException('닉네임 수정은 아직 지원되지 않습니다');
  }

  @override
  Future<Session?> restoreSession() async {
    if (_current != null) return _current;
    final saved = await _tokens.read();
    if (saved == null) return null;
    _token = saved;
    try {
      return _current = Session(user: await _fetchMe());
    } on AuthException catch (e) {
      _token = null;
      /* 🔴 **토큰을 버리는 것은 「이 토큰이 못 쓴다」고 서버가 말했을 때뿐이다.**
         계약의 그 대답은 `UNAUTHORIZED`(헤더 자체가 틀림)와
         `INVALID_TOKEN`(만료·서명 불일치·`logout-all` 로 폐기) 둘이다.

         🔴 **비행기 모드나 서버가 잠깐 죽은 것으로는 안 버린다.** 그때도
         버리면 **잠깐 끊긴 것 때문에 사람이 로그아웃된다** — 지하철에서 앱을
         켰다는 이유로 다시 로그인하게 만드는 셈이다. 이번 실행만 로그인 안 된
         상태로 두고, 토큰은 그대로 남겨 다음 기회에 다시 시도한다. */
      if (e.code == 'UNAUTHORIZED' || e.code == 'INVALID_TOKEN') {
        await _tokens.clear();
      }
      return null;
    }
  }

  /// 토큰을 메모리와 저장소 **둘 다**에 둔다 — 지금 요청에도 써야 하고,
  /// 다음에 켤 때도 있어야 한다.
  Future<void> _remember(String token) async {
    _token = token;
    await _tokens.write(token);
  }

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
      () => _client.post(
        Uri.parse('$apiBaseUrl$path'),
        headers: _headers(),
        body: jsonEncode(body),
      ),
    );
    return _decode(response);
  }

  Future<Map<String, dynamic>> _get(String path) async {
    final response = await _send(
      () => _client.get(Uri.parse('$apiBaseUrl$path'), headers: _headers()),
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
    /* 🔴 **`response.body` 를 쓰지 않는다**(2026-09-17). `http` 는 헤더에
       `charset` 이 없으면 **latin1 로** 푼다. FastAPI 는 `application/json` 만
       주고 charset 을 안 붙이므로, 한글 닉네임과 오류 문구가 깨져서 들어온다
       (「이메일 또는 비밀번호가…」가 뭉개진 글자로 보인다). 바이트를 직접
       UTF-8 로 푼다 — 서버가 charset 을 주든 안 주든 맞는 방식이다. */
    final decoded = response.bodyBytes.isEmpty
        ? <String, dynamic>{}
        : jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return decoded;
    }
    final error = decoded['error'] as Map<String, dynamic>?;
    // 🔴 서버가 값을 안 주면 0 이 아니라 최소 1초 — 0 이면 잠금이 곧바로
    // 풀려 "429 직후 재요청이 안 나간다"가 깨진다(웹과 같은 판단).
    final rawRetryAfter = response.headers['retry-after'];
    final parsedRetryAfter = rawRetryAfter == null
        ? null
        : int.tryParse(rawRetryAfter);
    throw AuthException(
      (error?['message'] as String?) ?? '알 수 없는 오류 (${response.statusCode})',
      code: error?['code'] as String?,
      retryAfter: parsedRetryAfter == null
          ? null
          : (parsedRetryAfter > 0 ? parsedRetryAfter : 1),
    );
  }
}
