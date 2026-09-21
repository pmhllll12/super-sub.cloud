import 'dart:convert';

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

  /// 저장소의 토큰을 메모리로 올린다(앱을 켤 때 한 번). 없으면 `null`.
  Future<String?> loadToken() async => _token = await _tokens.read();

  /// 토큰을 메모리와 저장소 **둘 다**에 둔다 — 지금 요청에도 써야 하고,
  /// 다음에 켤 때도 있어야 한다.
  Future<void> useToken(String token) async {
    _token = token;
    await _tokens.write(token);
  }

  /// 🔴 저장소에서도 지운다 — 안 지우면 다음에 켤 때 로그아웃한 계정으로
  /// 되돌아간다.
  Future<void> clearToken() async {
    _token = null;
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

  Future<http.Response> _send(Future<http.Response> Function() request) async {
    try {
      return await request();
    } on http.ClientException catch (e) {
      throw ApiException('서버에 연결할 수 없습니다: ${e.message}');
    }
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
    final error = decoded['error'] as Map<String, dynamic>?;
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

/// 🔴 세 리포지토리(인증 · 카드 · 스쿼드)가 **같은 한 벌**을 나눠 쓴다 —
/// 로그인이 저장한 토큰을 나머지가 그대로 써야 하기 때문이다. 따로 만들면
/// 카드·스쿼드 요청에 토큰이 안 실려 전부 401 이 된다.
final apiClientProvider = Provider<ApiClient>((ref) => ApiClient());
