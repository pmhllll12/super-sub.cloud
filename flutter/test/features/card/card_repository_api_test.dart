import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:super_sub/core/network/api_client.dart';
import 'package:super_sub/core/network/presigned_upload.dart';
import 'package:super_sub/core/network/upload_file.dart';
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

UploadFile photoFile({
  String name = '얼굴.jpg',
  String contentType = 'image/jpeg',
}) =>
    UploadFile(
      name: name,
      contentType: contentType,
      sizeBytes: 4,
      openRead: () => Stream.value(const [1, 2, 3, 4]),
    );

/// 계약을 물릴 가짜 서버.
///
/// `POST /me/card` 전에는 `GET /me/card` 가 404 다 — **계약의 「없으면 null」과
/// 「멱등」을 둘 다 실제로 밟게** 하려는 것이다. 멱등은 이미 만든 슬러그를 그대로
/// 돌려주는 것으로 흉내 낸다.
ApiCardRepository buildRepo() {
  String? mySlug;
  /// 저장된 `style` — 🔴 「올리기만 해서는 안 붙는다」와 「저장하면 붙는다」를
  /// 가르려면 가짜 서버가 **PATCH 를 실제로 기억해야** 한다.
  Map<String, dynamic>? savedStyle;
  final client = MockClient((req) async {
    final path = req.url.path;
    if (path.endsWith('/me/card/photo-upload-url')) {
      // 🔴 카드가 먼저 있어야 한다 — 키에 카드 id 가 들어간다(계약 3-5절).
      if (mySlug == null) return notFound('CARD_NOT_FOUND');
      final body = jsonDecode(req.body) as Map<String, dynamic>;
      final type = body['content_type'] as String?;
      // 🔴 받는 형식 셋뿐이다.
      if (type != 'image/jpeg' && type != 'image/png' && type != 'image/webp') {
        return jsonRes({
          'error': {'code': 'UNSUPPORTED_PHOTO_TYPE', 'message': '안 받는 형식입니다'},
        }, 422);
      }
      return jsonRes({
        // 🔴 확장자는 서버가 붙인다 — 클라이언트가 정하지 않는다.
        'storage_key': 'cards/photos/u1/pc-1-1a2b3c4d.jpg',
        'upload_url': 'https://storage.test/put',
        'expires_in': 900,
      }, 200);
    }
    if (path.endsWith('/me/card')) {
      if (req.method == 'POST') {
        mySlug ??= 'my-card-slug';
        return jsonRes(cardBody(mySlug!, id: 'pc-1'), 201);
      }
      if (req.method == 'PATCH') {
        final body = jsonDecode(req.body) as Map<String, dynamic>;
        if (body.containsKey('style')) {
          savedStyle = body['style'] as Map<String, dynamic>?;
        }
        return jsonRes({
          ...cardBody(mySlug ?? 'my-card-slug', id: 'pc-1'),
          'style': savedStyle,
        }, 200);
      }
      if (mySlug == null) return notFound('CARD_NOT_FOUND');
      return jsonRes({
        ...cardBody(mySlug!, id: 'pc-1'),
        'style': savedStyle,
      }, 200);
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
    // 🔴 저장소 PUT 은 `ApiClient` 를 안 지나므로 따로 덮는다.
    upload: PresignedUpload(
      client: MockClient((_) async => http.Response('', 200)),
    ),
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

    /// 🔴 **자리를 받기 전에 올리면** S3 에 서명이 없어 403 이고, **올리기
    /// 전에 PATCH 하면** 아무도 안 가리키는 키가 저장된다.
    test('사진 올리기는 자리받기 → S3 순서다', () async {
      final calls = <String>[];
      final repo = ApiCardRepository(
        ApiClient(
          tokens: InMemoryTokenStore(),
          client: MockClient((_) async {
            calls.add('spot');
            return jsonRes({
              'storage_key': 'cards/photos/u1/pc-1-abcd.jpg',
              'upload_url': 'https://storage.test/put',
              'expires_in': 900,
            }, 200);
          }),
        ),
        upload: PresignedUpload(
          client: MockClient((_) async {
            calls.add('s3');
            return http.Response('', 200);
          }),
        ),
      );

      await repo.uploadCardPhoto(photoFile());

      expect(calls, equals(['spot', 's3']));
    });

    /// 🔴 **확장자를 클라이언트가 정하지 않는다** — 타입만 보내고 서버가
    /// 붙인다(`image/jpeg` 라면서 `.html` 로 올리는 키가 생기지 않게).
    test('올릴 자리를 부를 때 content_type 만 보낸다', () async {
      Map<String, dynamic>? sent;
      final repo = ApiCardRepository(
        ApiClient(
          tokens: InMemoryTokenStore(),
          client: MockClient((req) async {
            sent = jsonDecode(req.body) as Map<String, dynamic>;
            return jsonRes({
              'storage_key': 'cards/photos/u1/pc-1-abcd.jpg',
              'upload_url': 'https://storage.test/put',
              'expires_in': 900,
            }, 200);
          }),
        ),
        upload: PresignedUpload(
          client: MockClient((_) async => http.Response('', 200)),
        ),
      );

      await repo.uploadCardPhoto(photoFile(name: '얼굴.png'));

      expect(sent, equals({'content_type': 'image/jpeg'}));
      expect(sent!.containsKey('filename'), isFalse);
    });

    /// 🔴 서명에 들어 있어 다르면 S3 가 **403** 이다.
    test('S3 에 보내는 Content-Type 이 요청한 값과 같다', () async {
      String? put;
      final repo = ApiCardRepository(
        ApiClient(
          tokens: InMemoryTokenStore(),
          client: MockClient((_) async => jsonRes({
                'storage_key': 'cards/photos/u1/pc-1-abcd.png',
                'upload_url': 'https://storage.test/put',
                'expires_in': 900,
              }, 200)),
        ),
        upload: PresignedUpload(
          client: MockClient((req) async {
            put = req.headers['Content-Type'];
            return http.Response('', 200);
          }),
        ),
      );

      await repo.uploadCardPhoto(photoFile(contentType: 'image/webp'));

      expect(put, equals('image/webp'));
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
