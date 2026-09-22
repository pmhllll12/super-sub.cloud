import 'package:http/http.dart' as http;

import '../../../core/network/api_client.dart';
import 'auth_repository.dart';
import 'models/app_user.dart';
import 'models/session.dart';
import 'models/team_membership.dart';
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
/// 🔴 **HTTP 공통은 [ApiClient] 로 옮겼다 (2026-09-21).** 토큰 보관 · UTF-8
/// 디코딩 · 에러 `code` · `Retry-After` 가 여기 갇혀 있었는데, 카드·스쿼드
/// 리포지토리가 같은 것을 필요로 해서 복붙하면 세 벌이 된다. 특히 「`response.body`
/// 를 쓰면 한글이 깨진다」를 한 곳이라도 빠뜨리면 거기서만 글자가 깨진다.
///
/// ⚠️ **생성자는 일부러 안 바꿨다** — `tokens:`·`client:` 를 쓰는 기존 시험
/// 여덟 개가 그대로 돌아야 이 리팩터가 동작을 안 바꿨다는 증거가 된다.
class ApiAuthRepository implements AuthRepository {
  ApiAuthRepository({TokenStore? tokens, http.Client? client, ApiClient? api})
      : _api = api ?? ApiClient(tokens: tokens, client: client);

  final ApiClient _api;
  Session? _current;

  @override
  Future<Session> login({
    required String email,
    required String password,
  }) async {
    final tokenBody = await _call(
      () => _api.post('/auth/login', {'email': email, 'password': password}),
    );
    await _api.useToken(tokenBody['access_token'] as String);
    return _current = Session(user: await _fetchMe());
  }

  @override
  Future<Session> signup({
    required String email,
    required String password,
    required String nickname,
  }) async {
    // 가입 응답은 사용자만 주고 토큰은 안 준다(계약) — 이어서 로그인한다.
    await _call(
      () => _api.post('/auth/signup', {
        'email': email,
        'password': password,
        'nickname': nickname,
      }),
    );
    return login(email: email, password: password);
  }

  @override
  Future<Session> loginWithGoogle({required String idToken}) async {
    // 🔴 access_token 이 아니라 id_token 이다 — 바꿔 보내면 서명 검증에서 401.
    // 응답이 비밀번호 로그인과 같아 이후 흐름을 그대로 잇는다.
    final tokenBody =
        await _call(() => _api.post('/auth/google', {'id_token': idToken}));
    await _api.useToken(tokenBody['access_token'] as String);
    return _current = Session(user: await _fetchMe());
  }

  @override
  Future<Session> loginAs(String userId) {
    throw const AuthException('개발용 바로 진입은 API 모드에서 지원하지 않습니다');
  }

  @override
  Future<void> logout() async {
    _current = null;
    // 🔴 저장소에서도 지운다 — 안 지우면 다음에 켤 때 로그아웃한 계정으로
    //    되돌아간다(「로그아웃했는데 왜 로그인돼 있냐」가 된다).
    await _api.clearToken();
  }

  @override
  Future<void> deleteAccount({String? password}) async {
    /* 🔴 **빈 값이면 본문을 통째로 안 보낸다** — 구글로만 가입한 계정에는
       확인할 비밀번호가 없다. 빈 문자열을 실으면 서버가 틀린 비밀번호로 읽어
       **탈퇴할 방법이 사라진다**(계약 2장, 웹도 같은 처리). */
    final hasPassword = password != null && password.isNotEmpty;
    /* `_call` 은 본문이 있는 응답을 감싸는 도우미라 여기엔 안 맞는다
       (`DELETE /me` 는 204 다). `ApiException` → `AuthException` 변환만
       같은 모양으로 한다. */
    try {
      await _api.deleteWithBody(
        '/me',
        hasPassword ? {'password': password} : null,
      );
    } on ApiException catch (e) {
      throw AuthException(e.message, code: e.code, retryAfter: e.retryAfter);
    }
    // 🔴 계정이 사라졌다 — 토큰을 안 지우면 다음에 켤 때 401 만 돈다.
    await _api.clearToken();
  }

  @override
  Future<AppUser> updateProfile({
    String? nickname,
    bool? nicknameSearchable,
  }) async {
    /* 🔴 **보낸 칸만 바뀐다.** 안 보낸 칸은 서버가 안 건드리므로, `null` 을
       그대로 실어 보내면 안 된다 — 그러면 「지우라」는 뜻이 된다. */
    final body = <String, dynamic>{
      'nickname': ?nickname,
      'is_nickname_searchable': ?nicknameSearchable,
    };
    // 응답이 `GET /me` 와 완전히 같아 파서를 하나만 든다.
    return _userFrom(await _call(() => _api.patch('/me', body)));
  }

  @override
  Future<Session?> restoreSession() async {
    if (_current != null) return _current;
    // 토큰이 없으면 서버를 아예 안 부른다 — 부를 것이 없다.
    if (await _api.loadToken() == null) return null;
    try {
      return _current = Session(user: await _fetchMe());
    } on AuthException catch (e) {
      /* 🔴 **토큰을 버리는 것은 「이 토큰이 못 쓴다」고 서버가 말했을 때뿐이다.**
         계약의 그 대답은 `UNAUTHORIZED`(헤더 자체가 틀림)와
         `INVALID_TOKEN`(만료·서명 불일치·`logout-all` 로 폐기) 둘이다.

         🔴 **비행기 모드나 서버가 잠깐 죽은 것으로는 안 버린다.** 그때도
         버리면 **잠깐 끊긴 것 때문에 사람이 로그아웃된다** — 지하철에서 앱을
         켰다는 이유로 다시 로그인하게 만드는 셈이다. 이번 실행만 로그인 안 된
         상태로 두고, 토큰은 그대로 남겨 다음 기회에 다시 시도한다. */
      if (e.code == 'UNAUTHORIZED' || e.code == 'INVALID_TOKEN') {
        await _api.clearToken();
      }
      return null;
    }
  }

  Future<AppUser> _fetchMe() async =>
      _userFrom(await _call(() => _api.get('/me')));

  /// `GET /me` · `PATCH /me` 의 응답은 **완전히 같다** — 파서가 하나다.
  AppUser _userFrom(Map<String, dynamic> body) {
    return AppUser(
      id: body['id'] as String,
      email: body['email'] as String,
      nickname: body['nickname'] as String,
      createdAt: DateTime.parse(body['created_at'] as String),
      // 🔴 **내 팀은 여기서 온다** — 따로 부를 경로가 없다. 옛 서버는 이 칸을
      //    안 줄 수 있어 없으면 빈 목록이다.
      teams: ((body['teams'] as List<dynamic>?) ?? const [])
          .map((e) => TeamMembership.fromJson(e as Map<String, dynamic>))
          .toList(growable: false),
      // 옛 서버가 이 칸을 안 주면 「보인다」로 본다(기존 동작).
      isNicknameSearchable: body['is_nickname_searchable'] as bool? ?? true,
    );
  }

  /// [ApiException] 을 이 컨텍스트의 [AuthException] 으로 옮긴다.
  ///
  /// 🔴 **화면과 계약 시험이 보는 타입을 안 바꾸려는 것이다** — 로그인 화면의
  /// 429 잠금이 `AuthException.retryAfter` 를 보고 있어서, 여기서 타입이 바뀌면
  /// 잠금이 조용히 안 걸린다.
  Future<Map<String, dynamic>> _call(
    Future<Map<String, dynamic>> Function() request,
  ) async {
    try {
      return await request();
    } on ApiException catch (e) {
      throw AuthException(e.message, code: e.code, retryAfter: e.retryAfter);
    }
  }
}
