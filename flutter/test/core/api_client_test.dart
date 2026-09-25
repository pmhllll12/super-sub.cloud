import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:super_sub/core/network/api_client.dart';
import 'package:super_sub/features/auth/data/token_store.dart';

/// 🔴 **`http.Response(문자열, …)` 을 쓰지 않는다** — 헤더에 `charset` 이 없으면
/// `http` 가 latin1 로 인코딩해서 한글 본문은 만들 때부터 터진다. 진짜 FastAPI 도
/// charset 을 안 붙이므로 바이트로 주고받는 쪽이 실제와 같다
/// (`auth_repository_api_test.dart` 머리말과 같은 이유).
http.Response jsonRes(Map<String, dynamic> body, int status,
        {Map<String, String>? headers}) =>
    http.Response.bytes(utf8.encode(jsonEncode(body)), status, headers: headers ?? const {});

ApiClient clientWith(
  Future<http.Response> Function(http.Request) handler, {
  TokenStore? tokens,
  Duration? timeout,
}) =>
    ApiClient(
      tokens: tokens ?? InMemoryTokenStore(),
      client: MockClient(handler),
      // 🔴 시험은 **짧게** 준다 — 기본값(20초)으로 재면 시험이 20초를 쉰다.
      timeout: timeout ?? kApiTimeout,
    );

void main() {
  _putTests();
  _timeoutTests();

  test('본문을 UTF-8 로 푼다 — 서버가 charset 을 안 줘도', () async {
    final api = clientWith((_) async => jsonRes({'nickname': '홍길동'}, 200));

    final body = await api.get('/me');

    expect(body['nickname'], equals('홍길동'));
  });

  test('토큰이 있으면 Authorization 헤더를 싣는다', () async {
    String? seen;
    final api = clientWith((req) async {
      seen = req.headers['Authorization'];
      return jsonRes({}, 200);
    });
    await api.useToken('t-123');

    await api.get('/me');

    expect(seen, equals('Bearer t-123'));
  });

  test('authorized: false 면 토큰이 있어도 헤더를 안 싣는다', () async {
    // 🔴 공개 경로(`GET /cards/{slug}`)는 인증하지 않는다 — 슬러그 자체가
    //    접근 통제라 토큰을 실을 이유가 없다.
    String? seen;
    final api = clientWith((req) async {
      seen = req.headers['Authorization'];
      return jsonRes({}, 200);
    });
    await api.useToken('t-123');

    await api.get('/cards/abc', authorized: false);

    expect(seen, isNull);
  });

  test('실패 응답의 code 와 status 를 함께 싣는다', () async {
    // 🔴 status 가 필요한 이유: 404 를 「오류」가 아니라 「없음」으로 다뤄야
    //    하는 자리가 있다(GET /me/card · GET /teams/{id}/squad).
    final api = clientWith(
      (_) async => jsonRes({
        'error': {'code': 'CARD_NOT_FOUND', 'message': '카드가 없습니다'},
      }, 404),
    );

    await expectLater(
      api.get('/me/card'),
      throwsA(isA<ApiException>()
          .having((e) => e.code, 'code', 'CARD_NOT_FOUND')
          .having((e) => e.status, 'status', 404)
          .having((e) => e.message, 'message', '카드가 없습니다')),
    );
  });

  test('Retry-After 가 0 이면 최소 1초로 올린다', () async {
    // 🔴 0 이면 잠금이 곧바로 풀려 "429 직후 재요청이 안 나간다"가 깨진다.
    final api = clientWith(
      (_) async => jsonRes(
        {
          'error': {'code': 'TOO_MANY_REQUESTS', 'message': '곧 다시'},
        },
        429,
        headers: {'retry-after': '0'},
      ),
    );

    await expectLater(
      api.get('/me'),
      throwsA(isA<ApiException>().having((e) => e.retryAfter, 'retryAfter', 1)),
    );
  });

  test('Retry-After 헤더가 없으면 null 이다', () async {
    final api = clientWith(
      (_) async => jsonRes({
        'error': {'code': 'INVALID_CREDENTIALS', 'message': '틀렸습니다'},
      }, 401),
    );

    await expectLater(
      api.get('/me'),
      throwsA(isA<ApiException>().having((e) => e.retryAfter, 'retryAfter', isNull)),
    );
  });

  test('본문이 빈 204 여도 터지지 않는다', () async {
    final api = clientWith((_) async => http.Response.bytes(const [], 204));

    await expectLater(api.delete('/me/card'), completes);
  });

  test('연결이 안 되면 ApiException 으로 옮긴다', () async {
    final api = clientWith((_) async => throw http.ClientException('끊김'));

    await expectLater(api.get('/me'), throwsA(isA<ApiException>()));
  });

  test('useToken 은 저장소에도 남긴다 — 다음에 켤 때 있어야 한다', () async {
    final store = InMemoryTokenStore();
    final api = clientWith((_) async => jsonRes({}, 200), tokens: store);

    await api.useToken('tok-저장됨');

    expect(await store.read(), equals('tok-저장됨'));
  });

  test('clearToken 은 저장소까지 비운다', () async {
    final store = InMemoryTokenStore();
    final api = clientWith((_) async => jsonRes({}, 200), tokens: store);
    await api.useToken('tok-1');

    await api.clearToken();

    expect(await store.read(), isNull);
  });

  test('loadToken 은 저장소의 토큰을 올려 다음 요청에 싣는다', () async {
    final store = InMemoryTokenStore();
    await store.write('tok-저장됨');
    String? seen;
    final api = clientWith((req) async {
      seen = req.headers['Authorization'];
      return jsonRes({}, 200);
    }, tokens: store);

    expect(await api.loadToken(), equals('tok-저장됨'));
    await api.get('/me');

    expect(seen, equals('Bearer tok-저장됨'));
  });
}

/// 🔴 **`PUT` 은 경기 조건이 처음 쓴다**(계약 3-13절) — 그쪽은 **통째로
/// 교체**라 `PATCH`(보낸 칸만 바뀜)로 대신할 수 없다.
void _putTests() {
  test('PUT 은 본문을 싣고 그 메서드로 나간다', () async {
    String? method;
    String? body;
    final api = clientWith((req) async {
      method = req.method;
      body = req.body;
      return jsonRes({'ok': true}, 200);
    });

    await api.put('/teams/t-1/match-preferences', {'region_ids': <String>[]});

    expect(method, 'PUT');
    expect(body, contains('region_ids'));
  });
}

/// 🔴 **서버가 멈추면 앱도 멈춘다** (2026-09-25, 실서버에서 실제로 겪었다 —
/// `/regions` 가 20초를 넘겨도 답이 없었다).
///
/// 제한 시간이 없으면 화면은 **영원히 기다리며 아무 오류도 안 낸다** —
/// 사용자에게는 「그냥 안 나온다」로 보이고, 서버 탓인지 앱 탓인지도 안
/// 드러난다. 끊고 **말해 주는** 것이 낫다.
void _timeoutTests() {
  test('오래 걸리면 끊고 알린다', () async {
    final api = clientWith(
      (_) async {
        // 제한 시간보다 길게 끈다 — 영원히 안 오는 서버를 흉내낸다.
        await Future<void>.delayed(const Duration(seconds: 5));
        return jsonRes({}, 200);
      },
      timeout: const Duration(milliseconds: 50),
    );

    await expectLater(
      api.get('/regions'),
      throwsA(
        isA<ApiException>().having(
          (e) => e.message,
          'message',
          contains('응답'),
        ),
      ),
    );
  });

  /// 🔴 **제때 오는 것은 그대로 통과한다** — 끊는 것이 목적이 아니다.
  test('제때 오면 그대로 온다', () async {
    final api = clientWith((_) async => jsonRes({'nickname': '홍길동'}, 200));

    expect((await api.get('/me'))['nickname'], '홍길동');
  });
}
