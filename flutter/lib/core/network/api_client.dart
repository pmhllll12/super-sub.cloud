import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;

import '../../features/auth/data/token_store.dart';
import 'api_config.dart';

/// 서버가 준 실패. 계약의 실패 본문은 늘 `{"error": {"code", "message"}}` 다.
///
/// 🔴 **[status] 를 싣는 이유**: 404 를 「오류」가 아니라 「없음(null)」으로
/// 다뤄야 하는 자리가 있다(`GET /me/card` 의 `CARD_NOT_FOUND`,
/// `GET /teams/{id}/squad` 의 `SQUAD_NOT_FOUND`). `code` 만 보고 가르면 서버가
/// code 를 안 주는 응답에서 못 가르고, 그렇다고 모든 실패를 「없음」으로 삼키면
/// 로그인이 풀린 것과 카드가 없는 것이 같아 보인다.
class ApiException implements Exception {
  const ApiException(this.message, {this.code, this.retryAfter, this.status});

  final String message;

  /// 서버 에러 `code` — 분기는 이걸로 한다. `message` 는 바뀔 수 있어도
  /// `code` 는 계약이다.
  final String? code;

  /// 429 일 때 몇 초 기다려야 하는가(서버가 준 `Retry-After`, 정수 초).
  /// 429 가 아니거나 헤더가 없으면 `null`.
  final int? retryAfter;

  /// HTTP 상태 코드.
  final int? status;

  @override
  String toString() => message;
}

/// 백엔드를 부르는 공통 창구 — 토큰 보관 · 헤더 · 디코딩 · 오류 변환.
///
/// 🔴 **리포지토리마다 `http` 를 직접 부르지 않는다.** 아래 두 함정이 한 곳이라도
/// 빠지면 **거기서만** 글자가 깨지거나 429 잠금이 안 걸린다 — 그런 종류의 결함은
/// 화면 한 곳에서만 드러나서 원인을 엉뚱한 데서 찾게 된다.
///
/// 🔴 **앱은 FastAPI 를 직접 부른다**(웹은 Next BFF 를 거친다). 그래서 `Retry-After`
/// 헤더도 프록시를 안 거치고 그대로 온다.
class ApiClient {
  ApiClient({TokenStore? tokens, http.Client? client})
      : _tokens = tokens ?? const SecureTokenStore(),
        _client = client ?? http.Client();

  final TokenStore _tokens;
  final http.Client _client;
  String? _token;

  /// 저장소 읽기는 **한 번만** 한다 — 여러 요청이 동시에 나가도 같은 것을
  /// 기다린다.
  Future<void>? _loading;

  /// 🔴 **요청이 스스로 토큰을 챙긴다 (2026-09-23).**
  ///
  /// 전에는 [loadToken] 을 **세션 복원이 부를 때만** 메모리에 올렸다. 그래서
  /// 그보다 먼저 나간 요청(홈이 켜지며 보는 `GET /me/card`)이 **토큰 없이
  /// 나가 401** 이었다 — 실기기 로그가 그 순서였다:
  ///
  ///     🔎API→ /me/card (tok=없음)
  ///     🔎API→ /me      (tok=있음)
  ///     🔎API✗ 401
  ///
  /// `myCardProvider` 는 `retry` 를 꺼 뒀으므로 그 401 이 **영구히 남고**,
  /// 화면은 그것을 「카드가 없다」로 그렸다. 지킴이:
  /// `test/core/shared_api_client_test.dart`.
  Future<void> _ensureLoaded() {
    if (_token != null) return Future<void>.value();
    return _loading ??= _tokens.read().then((t) => _token ??= t);
  }

  /// 저장소의 토큰을 메모리로 올린다(앱을 켤 때 한 번). 없으면 `null`.
  Future<String?> loadToken() async {
    await _ensureLoaded();
    return _token;
  }

  /// 토큰을 메모리와 저장소 **둘 다**에 둔다 — 지금 요청에도 써야 하고,
  /// 다음에 켤 때도 있어야 한다.
  Future<void> useToken(String token) async {
    _token = token;
    // 저장소를 다시 읽을 이유가 없어졌다 — 캐시한 읽기를 버린다.
    _loading = null;
    await _tokens.write(token);
  }

  /// 🔴 저장소에서도 지운다 — 안 지우면 다음에 켤 때 로그아웃한 계정으로
  /// 되돌아간다.
  Future<void> clearToken() async {
    _token = null;
    /* 🔴 캐시한 읽기도 버린다 — 안 버리면 로그아웃 뒤에도 [_ensureLoaded] 가
       **지우기 전에 읽어 둔 토큰**을 돌려줘 그대로 로그인 상태가 된다. */
    _loading = null;
    await _tokens.clear();
  }

  Future<Map<String, dynamic>> get(
    String path, {
    bool authorized = true,
  }) async {
    final res = await _send(
      () => _client.get(_uri(path), headers: _headers(authorized: authorized)),
    );
    return _decode(res);
  }

  /// 목록을 주는 경로 — `GET /videos` 처럼 **최상위가 배열**인 응답.
  ///
  /// 🔴 [get] 과 따로 두는 이유: `jsonDecode` 결과를 `Map` 으로 단정하는 곳이
  /// 한 군데라야 한다. 한쪽에서 `as Map` 이 배열을 만나면 그 자리에서 터지는데,
  /// 메시지가 `type 'List<dynamic>' is not a subtype of Map` 이라 **계약을
  /// 잘못 읽은 것인지 서버가 바뀐 것인지 안 드러난다.**
  Future<List<Map<String, dynamic>>> getList(String path) async {
    final res = await _send(
      () => _client.get(_uri(path), headers: _headers()),
    );
    return _decodeList(res);
  }

  /// 본문이 **JSON 이 아닌** 경로 — 지금은 포스터 JPEG 하나다.
  ///
  /// 🔴 [get] 으로 못 받는다: 그쪽은 본문을 UTF-8 글자로 읽고 `jsonDecode` 를
  /// 거는데, JPEG 바이트를 그렇게 다루면 **본문을 망가뜨리고** 터지는 자리도
  /// 엉뚱하다(「JSON 이 아니다」가 아니라 「글자가 아니다」로 난다).
  ///
  /// 🔴 **실패는 그대로 올린다** — 404(없음·못 뜸)를 `null` 로 삼키는 판단은
  /// 부르는 쪽(리포지토리)에서 한다. 여기서 삼키면 401·500 도 같이 묻힌다.
  Future<Uint8List> getBytes(String path) async {
    final res = await _send(
      () => _client.get(_uri(path), headers: _headers()),
    );
    if (res.statusCode >= 400) _throwFor(res);
    return res.bodyBytes;
  }

  Future<Map<String, dynamic>> post(
    String path, [
    Map<String, dynamic>? body,
  ]) async {
    final res = await _send(
      () => _client.post(
        _uri(path),
        headers: _headers(),
        body: body == null ? null : jsonEncode(body),
      ),
    );
    return _decode(res);
  }

  Future<Map<String, dynamic>> patch(
    String path,
    Map<String, dynamic> body,
  ) async {
    final res = await _send(
      () => _client.patch(
        _uri(path),
        headers: _headers(),
        body: jsonEncode(body),
      ),
    );
    return _decode(res);
  }

  /// 지우고 **바뀐 것을 돌려받는다** — 스쿼드 등재 빼기가 그렇다(계약이
  /// 바뀐 스쿼드 전체를 준다).
  Future<Map<String, dynamic>> deleteReturning(String path) async {
    final res = await _send(
      () => _client.delete(_uri(path), headers: _headers()),
    );
    return _decode(res);
  }

  /// **본문이 있는 DELETE** — 탈퇴(`DELETE /me`)가 비밀번호를 싣는다.
  ///
  /// 🔴 [body] 가 `null` 이면 **본문을 아예 안 보낸다.** 빈 맵(`{}`)을 보내는
  /// 것과 다르다 — 구글로만 가입한 계정은 비밀번호 칸 자체가 없어야 한다
  /// (`{"password": ""}` 이나 `{}` 를 보내면 서버가 그것을 「틀렸다」로 읽는
  /// 갈래가 생긴다).
  Future<void> deleteWithBody(
    String path, [
    Map<String, dynamic>? body,
  ]) async {
    final res = await _send(
      () => _client.delete(
        _uri(path),
        headers: _headers(),
        body: body == null ? null : jsonEncode(body),
      ),
    );
    // 성공이면 본문이 비어 있고(204), 실패면 _decode 가 던진다.
    _decode(res);
  }

  Future<void> delete(String path) async {
    final res = await _send(
      () => _client.delete(_uri(path), headers: _headers()),
    );
    // 성공이면 본문이 비어 있고(204), 실패면 _decode 가 던진다.
    _decode(res);
  }

  Uri _uri(String path) => Uri.parse('$apiBaseUrl$path');

  Map<String, String> _headers({bool authorized = true}) => {
        'Content-Type': 'application/json',
        if (authorized && _token != null) 'Authorization': 'Bearer $_token',
      };

  /// 🔴 **여기 한 곳에서 토큰을 보장한다.** [request] 는 닫힘(closure)이라
  /// 헤더를 **이 `await` 뒤에** 만든다 — 그래서 모든 경로(get·post·patch·
  /// delete·getList)가 한 번의 수정으로 같이 고쳐진다.
  Future<http.Response> _send(Future<http.Response> Function() request) async {
    await _ensureLoaded();
    try {
      return await request();
    } on http.ClientException catch (e) {
      throw ApiException('서버에 연결할 수 없습니다: ${e.message}');
    }
  }

  /// 배열 응답. 실패 본문은 배열이 아니라 `{"error": …}` 라 [_decode] 에
  /// 맡겨 예외로 올린다 — 오류 처리를 두 벌로 두지 않는다.
  List<Map<String, dynamic>> _decodeList(http.Response response) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      _decode(response); // 늘 던진다.
    }
    if (response.bodyBytes.isEmpty) return const [];
    // 🔴 `response.body` 를 쓰지 않는다 — 아래 _decode 와 같은 이유(latin1).
    final decoded = jsonDecode(utf8.decode(response.bodyBytes)) as List<dynamic>;
    return decoded.cast<Map<String, dynamic>>();
  }

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
    _throwFor(response);
  }

  /// 실패 응답을 [ApiException] 으로 올린다.
  ///
  /// 🔴 **[_decode] 에서 떼어 낸 것이다**(2026-09-24). 본문이 JSON 이 아닌
  /// 경로([getBytes])가 생기면서 **오류를 푸는 자리는 같아야** 했다 — 둘로
  /// 나뉘면 한쪽만 `Retry-After` 를 읽거나 한쪽만 `code` 를 싣게 된다.
  ///
  /// 🔴 **오류 본문은 언제나 JSON 이다** — 성공 본문이 JPEG 이어도 그렇다.
  Never _throwFor(http.Response response) {
    Map<String, dynamic>? body;
    try {
      body = response.bodyBytes.isEmpty
          ? null
          : jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    } catch (_) {
      body = null; // 오류 본문이 JSON 이 아닐 수도 있다(프록시·게이트웨이).
    }
    final error = body?['error'] as Map<String, dynamic>?;
    // 🔴 서버가 값을 안 주면 0 이 아니라 최소 1초 — 0 이면 잠금이 곧바로
    // 풀려 "429 직후 재요청이 안 나간다"가 깨진다(웹과 같은 판단).
    final rawRetryAfter = response.headers['retry-after'];
    final parsedRetryAfter =
        rawRetryAfter == null ? null : int.tryParse(rawRetryAfter);
    throw ApiException(
      (error?['message'] as String?) ?? '알 수 없는 오류 (${response.statusCode})',
      code: error?['code'] as String?,
      retryAfter: parsedRetryAfter == null
          ? null
          : (parsedRetryAfter > 0 ? parsedRetryAfter : 1),
      status: response.statusCode,
    );
  }
}

/// 로그인 토큰을 어디에 남길지 — 기본은 Keystore·Keychain(미결 `min` 25번).
///
/// 🔴 **위젯 시험은 이것을 갈아 끼운다.** 진짜 저장소는 플랫폼 채널로 오가는데
/// 위젯 시험의 **가짜 시계에서는 그 응답이 영영 안 온다** — 세션 복원이 안
/// 끝나서 라우터가 첫 화면에 멈춘다(2026-09-17에 스모크 시험이 그렇게 깨졌다).
/// 예외가 아니라 **안 오는 것**이라 `try/catch` 로는 못 푼다.
///
/// 🔴 **[apiClientProvider] 옆에 둔다 (2026-09-23).** 전에는
/// `features/auth/data/auth_providers.dart` 에 있었는데, 그러면 공유
/// [ApiClient] 가 이 저장소를 못 읽어 **자기 기본값을 따로 만들었다** —
/// 시험이 갈아 끼운 저장소가 안 먹혔다. `auth_providers.dart` 가 이름을
/// 그대로 다시 내보내므로 부르는 쪽은 안 고쳐도 된다.
final tokenStoreProvider = Provider<TokenStore>(
  (ref) => const SecureTokenStore(),
);

/// 🔴 리포지토리들이 **같은 한 벌**을 나눠 쓴다 — 로그인이 저장한 토큰을
/// 나머지가 그대로 써야 하기 때문이다. 따로 만들면 카드·영상·스쿼드 요청에
/// 토큰이 안 실려 전부 401 이 된다.
///
/// 🔴 **2026-09-23 에 실제로 그렇게 됐다.** `authRepositoryProvider` 가 이
/// 공유본을 안 넘겨서 `ApiAuthRepository` 가 자기 [ApiClient] 를 만들었고,
/// `/me` 만 토큰이 실리고 `/me/card`·`/videos`·`/teams/{id}/squad` 는 전부
/// 토큰 없이 나가 401 이었다. 화면은 그 401 을 **「카드가 없다」로** 그렸다
/// (`.value` 가 오류와 없음을 같은 `null` 로 만든다).
/// 지킴이: `test/core/shared_api_client_test.dart`.
final apiClientProvider = Provider<ApiClient>(
  (ref) => ApiClient(tokens: ref.watch(tokenStoreProvider)),
);
