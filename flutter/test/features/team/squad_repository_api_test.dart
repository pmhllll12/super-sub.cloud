import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:super_sub/core/network/api_client.dart';
import 'package:super_sub/features/auth/data/token_store.dart';
import 'package:super_sub/features/team/data/squad_repository_api.dart';

import '../../contract/squad_repository_contract.dart';

http.Response jsonRes(Map<String, dynamic> body, int status) =>
    http.Response.bytes(utf8.encode(jsonEncode(body)), status);

/// `t-thunder` 만 스쿼드가 있고 나머지는 404 인 가짜 서버.
ApiSquadRepository buildRepo() {
  final client = MockClient((req) async {
    if (req.url.path.contains('/teams/t-thunder/squad')) {
      return jsonRes({
        'id': 'sq-1',
        'team_id': 't-thunder',
        'public_slug': 'aB3xK9mQ2pL7vN4t',
        'formation': '5:5',
        'members': <dynamic>[],
      }, 200);
    }
    return jsonRes({
      'error': {'code': 'SQUAD_NOT_FOUND', 'message': '스쿼드가 없습니다'},
    }, 404);
  });
  return ApiSquadRepository(
    ApiClient(tokens: InMemoryTokenStore(), client: client),
  );
}

void main() {
  runSquadRepositoryContract(
    'ApiSquadRepository',
    buildRepo,
    teamWithSquad: 't-thunder',
    teamWithoutSquad: 't-bears',
  );

  group('ApiSquadRepository 고유 규칙', () {
    /// 🔴 403 을 삼키면 「소속이 아니라 못 본다」가 「아직 안 만들었다」로
    /// 보여, 판을 만들라고 권하게 된다.
    test('403 은 삼키지 않고 그대로 올린다', () async {
      final repo = ApiSquadRepository(ApiClient(
        tokens: InMemoryTokenStore(),
        client: MockClient((_) async => jsonRes({
              'error': {'code': 'FORBIDDEN', 'message': '소속이 아닙니다'},
            }, 403)),
      ));

      await expectLater(repo.squadOf('t-other'), throwsA(isA<ApiException>()));
    });

    test('팀 id 를 URL 에 안전하게 싣는다', () async {
      String? path;
      final repo = ApiSquadRepository(ApiClient(
        tokens: InMemoryTokenStore(),
        client: MockClient((req) async {
          path = req.url.path;
          return jsonRes({
            'error': {'code': 'SQUAD_NOT_FOUND', 'message': '없습니다'},
          }, 404);
        }),
      ));

      await repo.squadOf('a/b');

      expect(path, contains('a%2Fb'));
    });
  });
}
