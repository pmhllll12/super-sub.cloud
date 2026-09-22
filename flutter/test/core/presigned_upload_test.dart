import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:super_sub/core/network/api_client.dart';
import 'package:super_sub/core/network/presigned_upload.dart';

void main() {
  group('PresignedUpload', () {
    test('PUT 으로 보낸다', () async {
      String? method;
      final upload = PresignedUpload(
        client: MockClient((req) async {
          method = req.method;
          return http.Response('', 200);
        }),
      );

      await upload.put(
        url: Uri.parse('https://example.test/put'),
        openRead: () => Stream.value(utf8.encode('bytes')),
        contentLength: 5,
        contentType: 'video/mp4',
      );

      expect(method, equals('PUT'));
    });

    /// 🔴 **서명에 Content-Type 이 들어 있다** — 요청한 값과 다르면 S3 가
    /// 거절한다. 이 함수가 값을 고쳐 주면 그 실패를 배포에서 처음 본다.
    test('Content-Type 을 받은 그대로 보낸다', () async {
      String? sent;
      final upload = PresignedUpload(
        client: MockClient((req) async {
          sent = req.headers['Content-Type'];
          return http.Response('', 200);
        }),
      );

      await upload.put(
        url: Uri.parse('https://example.test/put'),
        openRead: () => Stream.value(utf8.encode('bytes')),
        contentLength: 5,
        contentType: 'video/quicktime',
      );

      expect(sent, equals('video/quicktime'));
    });

    test('몸통이 그대로 올라간다', () async {
      String? body;
      final upload = PresignedUpload(
        client: MockClient((req) async {
          body = req.body;
          return http.Response('', 200);
        }),
      );

      await upload.put(
        url: Uri.parse('https://example.test/put'),
        openRead: () => Stream.fromIterable([
          utf8.encode('앞'),
          utf8.encode('뒤'),
        ]),
        contentLength: utf8.encode('앞뒤').length,
        contentType: 'video/mp4',
      );

      expect(body, equals('앞뒤'));
    });

    /// 🔴 **토큰을 안 싣는다.** S3 는 서명으로 인증하고, `Authorization` 을
    /// 얹으면 그 서명과 충돌한다.
    test('Authorization 을 안 싣는다', () async {
      String? auth;
      final upload = PresignedUpload(
        client: MockClient((req) async {
          auth = req.headers['Authorization'];
          return http.Response('', 200);
        }),
      );

      await upload.put(
        url: Uri.parse('https://example.test/put'),
        openRead: () => Stream.value(utf8.encode('b')),
        contentLength: 1,
        contentType: 'video/mp4',
      );

      expect(auth, isNull);
    });

    test('403 이면 던진다', () async {
      final upload = PresignedUpload(
        client: MockClient((_) async => http.Response('<Error/>', 403)),
      );

      await expectLater(
        upload.put(
          url: Uri.parse('https://example.test/put'),
          openRead: () => Stream.value(utf8.encode('b')),
          contentLength: 1,
          contentType: 'video/mp4',
        ),
        throwsA(isA<ApiException>()),
      );
    });

    /// 🔴 S3 의 XML 오류 본문에는 서명·키가 섞여 나온다 — 사람에게 그대로
    /// 보여주지 않는다.
    test('S3 의 오류 본문을 사람에게 그대로 보여주지 않는다', () async {
      final upload = PresignedUpload(
        client: MockClient(
          (_) async => http.Response('<Error><Key>videos/u-1/x.mp4</Key></Error>', 403),
        ),
      );

      try {
        await upload.put(
          url: Uri.parse('https://example.test/put'),
          openRead: () => Stream.value(utf8.encode('b')),
          contentLength: 1,
          contentType: 'video/mp4',
        );
        fail('던졌어야 한다');
      } on ApiException catch (e) {
        expect(e.message, isNot(contains('videos/')));
        expect(e.status, equals(403));
      }
    });
  });
}
