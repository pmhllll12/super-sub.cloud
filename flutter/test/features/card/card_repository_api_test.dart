import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:super_sub/core/network/api_client.dart';
import 'package:super_sub/features/auth/data/token_store.dart';
import 'package:super_sub/features/card/data/card_repository_api.dart';

import '../../contract/card_repository_contract.dart';

/// 🔴 바이트로 준다 — 문자열 생성자는 charset 이 없으면 latin1 로 인코딩해서
/// 한글이 든 본문이 만들 때부터 터진다.
http.Response jsonRes(Map<String, dynamic> body, int status) =>
    http.Response.bytes(utf8.encode(jsonEncode(body)), status);

http.Response notFound(String code) => jsonRes({
      'error': {'code': code, 'message': '없습니다'},
    }, 404);

Map<String, dynamic> cardBody(String slug, {String? id}) => {
      'id': ?id,
      'public_slug': slug,
      'user': {'id': 'u1', 'nickname': '홍길동'},
      'titles': <dynamic>[],
      'tagline': null,
      'style': null,
    };

/// 계약을 물릴 가짜 서버.
///
/// `POST /me/card` 전에는 `GET /me/card` 가 404 다 — **계약의 「없으면 null」과
/// 「멱등」을 둘 다 실제로 밟게** 하려는 것이다. 멱등은 이미 만든 슬러그를 그대로
/// 돌려주는 것으로 흉내 낸다.
ApiCardRepository buildRepo() {
  String? mySlug;
  final client = MockClient((req) async {
    final path = req.url.path;
    if (path.endsWith('/me/card')) {
      if (req.method == 'POST') {
        mySlug ??= 'my-card-slug';
        return jsonRes(cardBody(mySlug!, id: 'pc-1'), 201);
      }
      if (mySlug == null) return notFound('CARD_NOT_FOUND');
      return jsonRes(cardBody(mySlug!, id: 'pc-1'), 200);
    }
    if (path.contains('/cards/')) {
      final slug = Uri.decodeComponent(path.split('/cards/').last);
      if (slug == 'lee-gamdok-7f21' || slug == mySlug) {
        return jsonRes(cardBody(slug), 200);
      }
      return notFound('CARD_NOT_FOUND');
    }
    return notFound('NOT_FOUND');
  });
  return ApiCardRepository(
    ApiClient(tokens: InMemoryTokenStore(), client: client),
  );
}

void main() {
  runCardRepositoryContract(
    'ApiCardRepository',
    buildRepo,
    slugWithCard: 'lee-gamdok-7f21',
  );

  group('ApiCardRepository 고유 규칙', () {
    /// 🔴 404 **만** null 이다. 401 까지 삼키면 「로그인이 풀렸다」가 「카드가
    /// 없다」로 보여 화면이 조용히 잘못된 상태에 머문다.
    test('401 은 삼키지 않고 그대로 올린다', () async {
      final repo = ApiCardRepository(ApiClient(
        tokens: InMemoryTokenStore(),
        client: MockClient((_) async => jsonRes({
              'error': {'code': 'UNAUTHORIZED', 'message': '로그인이 필요합니다'},
            }, 401)),
      ));

      await expectLater(repo.myCard(), throwsA(isA<ApiException>()));
    });

    test('500 도 삼키지 않는다', () async {
      final repo = ApiCardRepository(ApiClient(
        tokens: InMemoryTokenStore(),
        client: MockClient((_) async => jsonRes({
              'error': {'code': 'INTERNAL', 'message': '서버 오류'},
            }, 500)),
      ));

      await expectLater(repo.myCard(), throwsA(isA<ApiException>()));
    });

    /// 🔴 공개 경로라 토큰을 안 싣는다.
    test('남의 카드를 읽을 때 Authorization 을 안 싣는다', () async {
      String? seen;
      final api = ApiClient(
        tokens: InMemoryTokenStore(),
        client: MockClient((req) async {
          seen = req.headers['Authorization'];
          return jsonRes(cardBody('abc'), 200);
        }),
      );
      await api.useToken('tok-1');

      await ApiCardRepository(api).cardBySlug('abc');

      expect(seen, isNull);
    });

    test('슬러그를 URL 에 안전하게 싣는다', () async {
      String? path;
      final repo = ApiCardRepository(ApiClient(
        tokens: InMemoryTokenStore(),
        client: MockClient((req) async {
          path = req.url.path;
          return notFound('CARD_NOT_FOUND');
        }),
      ));

      await repo.cardBySlug('a/b');

      expect(path, contains('a%2Fb'));
    });
  });
}
