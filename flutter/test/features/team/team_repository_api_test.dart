import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:super_sub/core/network/api_client.dart';
import 'package:super_sub/features/auth/data/token_store.dart';
import 'package:super_sub/features/team/data/regions.dart';
import 'package:super_sub/features/team/data/team_repository.dart';
import 'package:super_sub/features/team/data/team_repository_api.dart';

import '../../contract/team_repository_contract.dart';

http.Response jsonRes(Object body, int status) =>
    http.Response.bytes(utf8.encode(jsonEncode(body)), status);

http.Response errRes(String code, int status) => jsonRes({
      'error': {'code': code, 'message': '안 됩니다'},
    }, status);

/// 계약을 물릴 가짜 서버. **상태를 들고 있어** 고치기가 실제로 반영된다.
///
/// 역할은 `myUserId` 로 가른다 — `u-owner` 는 주장, 그 밖은 팀원이다.
ApiTeamRepository buildRepo(String myUserId, Map<String, dynamic> team) {
  final client = MockClient((req) async {
    final path = req.url.path;
    final owner = myUserId == 'u-owner';
    final body = req.body.isEmpty
        ? <String, dynamic>{}
        : jsonDecode(req.body) as Map<String, dynamic>;

    if (path.endsWith('/squad') && req.method == 'POST') {
      return jsonRes({'id': 'sq-1'}, 201);
    }
    if (path.endsWith('/teams') && req.method == 'POST') {
      // 🔴 서버도 이름·지역을 본다(계약 422 VALIDATION_ERROR).
      final name = (body['name'] as String? ?? '').trim();
      final region = body['region'] as String? ?? '';
      if (name.isEmpty || name.length > kMaxTeamName || !isRegion(region)) {
        return errRes('VALIDATION_ERROR', 422);
      }
      return jsonRes({
        'id': 't-new',
        'name': name,
        'region': region,
        'sport_code': 'football',
      }, 201);
    }
    if (path.contains('/members/')) {
      // 🔴 주장은 못 나간다.
      if (owner) return errRes('OWNER_CANNOT_LEAVE', 409);
      return http.Response('', 204);
    }
    if (path.contains('/teams/')) {
      // 주장만 고치고 해체한다.
      if (!owner) return errRes('FORBIDDEN', 403);
      if (req.method == 'DELETE') return http.Response('', 204);
      if (req.method == 'PATCH') {
        final name = body['name'] as String?;
        final region = body['region'] as String?;
        if (name != null &&
            (name.trim().isEmpty || name.trim().length > kMaxTeamName)) {
          return errRes('VALIDATION_ERROR', 422);
        }
        if (region != null && !isRegion(region)) {
          return errRes('VALIDATION_ERROR', 422);
        }
        // 🔴 보낸 것만 바뀐다.
        if (name != null) team['name'] = name.trim();
        if (region != null) team['region'] = region.trim();
        return jsonRes(team, 200);
      }
    }
    return errRes('NOT_FOUND', 404);
  });

  return ApiTeamRepository(
    ApiClient(tokens: InMemoryTokenStore(), client: client),
    myUserId: myUserId,
  );
}

void main() {
  late Map<String, dynamic> team;

  setUp(() {
    team = {
      'id': 't-1',
      'name': '번개FC',
      'region': '서울 강남구',
      'sport_code': 'football',
    };
  });

  runTeamRepositoryContract(
    'ApiTeamRepository',
    asOwner: () => buildRepo('u-owner', team),
    asMember: () => buildRepo('u-member', team),
    teamId: 't-1',
  );

  group('ApiTeamRepository 고유 규칙', () {
    test('만들 때 종목을 실어 보낸다 — 없으면 422 UNKNOWN_SPORT 다', () async {
      Map<String, dynamic>? sent;
      final repo = ApiTeamRepository(
        ApiClient(
          tokens: InMemoryTokenStore(),
          client: MockClient((req) async {
            if (req.url.path.endsWith('/squad')) {
              return jsonRes({'id': 'sq-1'}, 201);
            }
            sent = jsonDecode(req.body) as Map<String, dynamic>;
            return jsonRes({
              'id': 't-new',
              'name': '새 팀',
              'region': '서울 마포구',
              'sport_code': 'football',
            }, 201);
          }),
        ),
        myUserId: 'u-1',
      );

      await repo.createTeam(name: '새 팀', region: '서울 마포구');

      expect(sent!['sport_code'], kTeamSportCode);
    });

    /// 🔴 **판 만들기가 실패해도 팀은 살린다.** 여기서 던지면 **이미 만들어진
    /// 팀**을 두고 「실패했다」고 말하게 되고, 사람은 다시 만들어 팀이 둘이 된다.
    test('스쿼드 만들기가 실패해도 팀 만들기는 성공이다', () async {
      final repo = ApiTeamRepository(
        ApiClient(
          tokens: InMemoryTokenStore(),
          client: MockClient((req) async {
            if (req.url.path.endsWith('/squad')) {
              return errRes('INTERNAL', 500);
            }
            return jsonRes({
              'id': 't-new',
              'name': '새 팀',
              'region': '서울 마포구',
              'sport_code': 'football',
            }, 201);
          }),
        ),
        myUserId: 'u-1',
      );

      final made = await repo.createTeam(name: '새 팀', region: '서울 마포구');

      expect(made.teamId, 't-new');
    });

    test('나가기는 내 멤버 id 를 URL 에 싣는다', () async {
      String? path;
      final repo = ApiTeamRepository(
        ApiClient(
          tokens: InMemoryTokenStore(),
          client: MockClient((req) async {
            path = req.url.path;
            return http.Response('', 204);
          }),
        ),
        myUserId: 'u-42',
      );

      await repo.leaveTeam('t-1');

      expect(path, contains('/teams/t-1/members/u-42'));
    });
  });
}
