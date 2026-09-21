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

/// `t-thunder` 만 스쿼드가 있는 가짜 서버.
///
/// 🔴 **서버가 막는 것을 여기서도 막는다** — 계약 시험이 「이미 찬 칸」·「같은
/// 카드 두 번」·「남의 등재」를 실제로 밟아야 뜻이 있다.
ApiSquadRepository buildRepo() {
  // GK(1,3)는 이감독이 앉아 있다 — 계약 시험의 takenSeat 다.
  final members = <Map<String, dynamic>>[
    {
      'id': 'sm-1',
      'player_card_id': 'pc-manager',
      'card_public_slug': 'lee-gamdok-7f21',
      'nickname': '이감독',
      'position_code': 'GK',
      'position_label': '골키퍼',
      'grid_col': 1,
      'grid_row': 3,
    },
  ];

  Map<String, dynamic> squadBody() => {
        'id': 'sq-1',
        'team_id': 't-thunder',
        'public_slug': 'aB3xK9mQ2pL7vN4t',
        'formation': '5:5',
        'members': members,
      };

  http.Response err(String code, String message, int status) =>
      jsonRes({
        'error': {'code': code, 'message': message},
      }, status);

  final client = MockClient((req) async {
    final path = req.url.path;
    if (!path.contains('/teams/t-thunder/squad')) {
      return err('SQUAD_NOT_FOUND', '스쿼드가 없습니다', 404);
    }
    final body = req.body.isEmpty
        ? <String, dynamic>{}
        : jsonDecode(req.body) as Map<String, dynamic>;
    final col = body['grid_col'] as int?;
    final row = body['grid_row'] as int?;

    if (req.method == 'POST') {
      if (members.any((m) => m['player_card_id'] == body['player_card_id'])) {
        return err('ALREADY_ENLISTED', '이미 등재된 카드입니다', 409);
      }
      if (members.any((m) => m['grid_col'] == col && m['grid_row'] == row)) {
        return err('SEAT_TAKEN', '그 자리에는 이미 사람이 있습니다', 409);
      }
      members.add({
        'id': 'sm-${members.length + 1}',
        'player_card_id': body['player_card_id'],
        'card_public_slug': null,
        'nickname': '새사람',
        'position_code': body['position_code'],
        'position_label': body['position_code'],
        'grid_col': col,
        'grid_row': row,
      });
      return jsonRes(squadBody(), 201);
    }

    if (req.method == 'PATCH') {
      final memberId = path.split('/').last;
      final target = members.where((m) => m['id'] == memberId).firstOrNull;
      if (target == null) {
        return err('MEMBER_NOT_FOUND', '이 팀 스쿼드의 등재가 아닙니다', 404);
      }
      if (members.any((m) =>
          m['id'] != memberId && m['grid_col'] == col && m['grid_row'] == row)) {
        return err('SEAT_TAKEN', '그 자리에는 이미 사람이 있습니다', 409);
      }
      target['position_code'] = body['position_code'];
      target['position_label'] = body['position_code'];
      target['grid_col'] = col;
      target['grid_row'] = row;
      return jsonRes(squadBody(), 200);
    }

    return jsonRes(squadBody(), 200);
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
    cardIdToEnlist: 'pc-u-player',
    freeSeat: (1, 0),
    takenSeat: (1, 3),
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
