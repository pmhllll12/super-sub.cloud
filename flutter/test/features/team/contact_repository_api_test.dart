import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:super_sub/core/network/api_client.dart';
import 'package:super_sub/features/auth/data/token_store.dart';
import 'package:super_sub/features/team/data/contact_repository_api.dart';

import '../../contract/contact_repository_contract.dart';

http.Response ok(Object body) =>
    http.Response.bytes(utf8.encode(jsonEncode(body)), 200);

http.Response err(String code, int status) => http.Response.bytes(
      utf8.encode(jsonEncode({
        'error': {'code': code, 'message': code},
      })),
      status,
    );

/// 마지막 요청의 경로+쿼리. 구현체별 의무를 보는 자리다.
String lastUrl = '';

ApiContactRepository buildRepo() {
  final contacts = <Map<String, dynamic>>[
    {
      'contact_id': 'ct-1',
      'user_id': 'u-jin',
      'nickname': '정어진',
      'note': null,
      'accepted_at': '2026-09-20T10:00:00Z',
    },
  ];
  final requests = <Map<String, dynamic>>[
    {
      'id': 'ct-pending',
      'requester_user_id': 'u-pass',
      'target_user_id': 'u-me',
      'note': null,
      'accepted_at': null,
      'created_at': '2026-09-24T09:00:00Z',
    },
  ];
  const directory = [
    {'id': 'u-pass', 'nickname': '한박자빠른패스'},
    {'id': 'u-stranger', 'nickname': '처음보는사람'},
  ];
  final sent = <String>{};

  final client = MockClient((req) async {
    lastUrl = '${req.url.path}?${req.url.query}';
    final path = req.url.path;

    if (path.endsWith('/me/contacts') && req.method == 'GET') {
      return ok({'items': contacts});
    }
    if (path.endsWith('/me/contacts/requests')) return ok(requests);

    if (path.endsWith('/users/search')) {
      final q = req.url.queryParameters['q'] ?? '';
      return ok(
        directory.where((u) => (u['nickname']!).contains(q)).toList(),
      );
    }

    if (path.endsWith('/me/contacts') && req.method == 'POST') {
      final body = jsonDecode(req.body) as Map<String, dynamic>;
      final target = body['target_user_id'] as String;
      if (target == 'u-me') return err('CANNOT_REQUEST_SELF', 422);
      if (!sent.add(target)) return err('ALREADY_REQUESTED', 409);
      return http.Response.bytes(utf8.encode(jsonEncode({'id': 'ct-new'})), 201);
    }

    if (path.contains('/me/contacts/') && path.endsWith('/accept')) {
      final id = path.split('/me/contacts/')[1].replaceAll('/accept', '');
      final i = requests.indexWhere((r) => r['id'] == id);
      if (i < 0) return err('CONTACT_NOT_FOUND', 404);
      requests.removeAt(i);
      return ok({'ok': true});
    }

    return err('NOT_FOUND', 404);
  });

  return ApiContactRepository(
    ApiClient(client: client, tokens: InMemoryTokenStore()),
  );
}

void main() {
  runContactRepositoryContract(
    'ApiContactRepository',
    buildRepo,
    knownNickname: '한박자빠른패스',
    strangerId: 'u-stranger',
    pendingRequestId: 'ct-pending',
    myOwnId: 'u-me',
  );

  group('ApiContactRepository 고유 규칙', () {
    /// 🔴 `items` 로 한 겹 감싸여 오는 경로는 여기 하나뿐이다(계약). 배열로
    /// 읽으면 `type 'Map' is not a subtype of List` 로 터진다.
    test('지인 목록은 items 안에 있다', () async {
      expect(await buildRepo().contacts(), hasLength(1));
    });

    /// 🔴 닉네임에 한글·공백·`&` 가 있어도 쿼리가 안 깨져야 한다.
    test('검색어를 인코딩해서 보낸다', () async {
      await buildRepo().search('한박자 & 빠른');

      expect(lastUrl, contains('q=%ED%95%9C%EB%B0%95%EC%9E%90'));
      expect(lastUrl, contains('%26'));
    });

    /// 🔴 409 를 성공으로 치는 것은 **`ALREADY_REQUESTED` 일 때만**이다.
    /// 409 를 통째로 삼키면 나중에 다른 409 가 생겼을 때 조용히 묻힌다.
    test('다른 오류는 그대로 올린다', () async {
      await expectLater(
        buildRepo().request('u-me'),
        throwsA(isA<ApiException>()),
      );
    });
  });
}
