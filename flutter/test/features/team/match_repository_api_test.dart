import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:super_sub/core/network/api_client.dart';
import 'package:super_sub/features/auth/data/token_store.dart';
import 'package:super_sub/features/team/data/match_repository_api.dart';
import 'package:super_sub/features/team/match_prefs.dart';

import '../../contract/match_repository_contract.dart';

http.Response ok(Object body) =>
    http.Response.bytes(utf8.encode(jsonEncode(body)), 200);

http.Response err(String code, int status) => http.Response.bytes(
      utf8.encode(jsonEncode({
        'error': {'code': code, 'message': code},
      })),
      status,
    );

/// 마지막으로 보낸 조건 본문 — 구현체별 의무(요일 변환)를 보는 자리다.
Map<String, dynamic> lastPrefsBody = {};

ApiMatchRepository buildRepo() {
  // 팀별로 저장된 조건. t-bears 는 **비워 둔다**(「아직 안 정한 팀」 갈래).
  final prefs = <String, Map<String, dynamic>>{};
  final requests = <Map<String, dynamic>>[
    // 🔴 나에게 온 신청 하나 — 받은 쪽에서 답하는 갈래.
    {
      'id': 'tmr-incoming',
      'requester_team_id': 't-bears',
      'target_team_id': 't-thunder',
      'status': 'pending',
      'proposed_played_at': '2026-10-05T11:00:00+09:00',
      'proposed_place': '영등포공원 풋살경기장',
      'match_id': null,
      'requester_team_name': '베어스',
    },
  ];
  final reviewed = <String>{};
  Map<String, dynamic>? minePrefs;

  final client = MockClient((req) async {
    final path = req.url.path;
    final body = req.body.isEmpty
        ? <String, dynamic>{}
        : jsonDecode(req.body) as Map<String, dynamic>;

    if (path.endsWith('/regions')) {
      return ok(const [
        {'id': 'r-gangnam', 'label': '서울 강남구'},
        {'id': 'r-yd', 'label': '서울 영등포구'},
      ]);
    }
    if (path.endsWith('/positions')) {
      return ok(const [
        {'id': 'p-mf', 'sport_code': 'football', 'code': 'MF', 'label': '미드필더'},
        {'id': 'p-gk', 'sport_code': 'football', 'code': 'GK', 'label': '골키퍼'},
      ]);
    }

    // 내 조건 — 🔴 팀 조건과 **다른 통**이다(계약: 절대 안 섞는다).
    if (path.endsWith('/me/match-preferences')) {
      if (req.method == 'PUT') {
        minePrefs = body;
        return ok(body);
      }
      return ok(minePrefs ??
          const {'region_ids': [], 'slots': [], 'position_ids': []});
    }

    if (path.endsWith('/matches')) {
      final sport = req.url.queryParameters['sport_code'];
      if (sport != null && sport != 'football') {
        return err('UNKNOWN_SPORT', 422);
      }
      final region = req.url.queryParameters['region'];
      final rows = [
        {
          'id': 'om-1',
          'team_id': 't-bears',
          'team_name': '베어스',
          'region': '서울 송파구',
          'sport_code': 'football',
          'played_at': '2026-10-02T19:00:00Z',
          'place': '잠실 풋살장',
          'needs': [
            {'position_code': 'GK', 'position_label': '골키퍼', 'head_count': 1},
          ],
        },
      ];
      return ok({
        'items': [
          for (final r in rows)
            if (region == null || (r['region']! as String).contains(region)) r,
        ],
        'total': 1,
        'page': 1,
        'size': 20,
      });
    }

    if (path.contains('/match-preferences')) {
      final teamId = path.split('/teams/')[1].split('/')[0];
      if (req.method == 'PUT') {
        lastPrefsBody = body;
        // 🔴 서버가 막는 것을 여기서도 막는다(422 INVALID_TIME_SLOT).
        for (final s in (body['slots'] as List).cast<Map<String, dynamic>>()) {
          if ((s['start_time'] as String).compareTo(s['end_time'] as String) >=
              0) {
            return err('INVALID_TIME_SLOT', 422);
          }
        }
        // **통째로 교체**다 — 합치지 않는다.
        prefs[teamId] = body;
        return ok(body);
      }
      return ok(prefs[teamId] ?? const {'region_ids': [], 'slots': []});
    }

    if (path.endsWith('/review-options')) {
      // 🔴 순서가 곧 노출 순서다 — 「주의」가 맨 뒤인 채로 준다.
      return ok(const [
        {'code': 'manner_time', 'category': 'manner', 'label': '시간을 잘 지켰다'},
        {'code': 'skill_teamplay', 'category': 'skill', 'label': '팀플레이가 좋았다'},
        {'code': 'repeat_yes', 'category': 'repeat', 'label': '다시 함께 뛰고 싶다'},
        {
          'code': 'caution_would_not_repeat',
          'category': 'caution',
          'label': '다시 함께 뛰고 싶지 않다',
        },
      ]);
    }

    if (path.contains('/reviews')) {
      final codes = (body['option_codes'] as List).cast<String>();
      if (codes.isEmpty) return err('NO_OPTION_SELECTED', 422);
      final key = '${path.split('/matches/')[1]}/${body['reviewee_id']}';
      if (!reviewed.add(key)) return err('ALREADY_REVIEWED', 409);
      return http.Response.bytes(utf8.encode(jsonEncode({'id': 'rv-1'})), 201);
    }

    if (path.contains('/match-candidates')) {
      return ok(const [
        {
          'team_id': 't-gangnam',
          'team_name': 'FC 강남',
          'region_label': '서울 강남구',
          'formation': '5:5',
          'reasons': [
            {'kind': 'time', 'detail': '토요일 10:00~12:00 겹침'},
          ],
        },
        // 🔴 근거가 빈 후보 — 하드 필터는 통과했으므로 목록에 남는다.
        {
          'team_id': 't-cloud',
          'team_name': '강남 클라우드FC',
          'region_label': '서울 강남구',
          'formation': '5:5',
          'reasons': [],
        },
      ]);
    }

    if (path.contains('/match-requests')) {
      for (final verb in ['accept', 'reject']) {
        if (!path.endsWith('/$verb')) continue;
        final id = path.split('/match-requests/')[1].replaceAll('/$verb', '');
        final i = requests.indexWhere((r) => r['id'] == id);
        if (i < 0) return err('TEAM_MATCH_REQUEST_NOT_FOUND', 404);
        if (requests[i]['status'] != 'pending') {
          return err('TEAM_MATCH_REQUEST_ALREADY_RESPONDED', 409);
        }
        requests[i] = {
          ...requests[i],
          'status': verb == 'accept' ? 'accepted' : 'rejected',
          if (verb == 'accept') 'match_id': 'm-$id',
        };
        return ok(requests[i]);
      }
      if (req.method == 'DELETE') {
        final id = path.split('/match-requests/')[1];
        final i = requests.indexWhere((r) => r['id'] == id);
        if (i < 0) return err('TEAM_MATCH_REQUEST_NOT_FOUND', 404);
        if (requests[i]['status'] != 'pending') {
          return err('TEAM_MATCH_REQUEST_ALREADY_RESPONDED', 409);
        }
        requests[i] = {...requests[i], 'status': 'cancelled'};
        return ok(requests[i]);
      }
      if (req.method == 'POST') {
        final target = body['target_team_id'] as String;
        final live = requests.any(
          (r) => r['target_team_id'] == target && r['status'] == 'pending',
        );
        if (live) return err('TEAM_MATCH_REQUEST_ALREADY_LIVE', 409);
        final made = {
          'id': 'tmr-${requests.length + 1}',
          'requester_team_id': 't-thunder',
          'target_team_id': target,
          'status': 'pending',
          'proposed_played_at': body['played_at'],
          'proposed_place': body['place'],
          'match_id': null,
          'target_team_name': 'FC 강남',
          'target_squad_public_slug': null,
        };
        requests.add(made);
        return http.Response.bytes(utf8.encode(jsonEncode(made)), 201);
      }
      return ok(requests);
    }

    return err('NOT_FOUND', 404);
  });

  return ApiMatchRepository(
    ApiClient(client: client, tokens: InMemoryTokenStore()),
  );
}

void main() {
  runMatchRepositoryContract(
    'ApiMatchRepository',
    buildRepo,
    myTeamId: 't-thunder',
    teamWithoutPrefs: 't-bears',
    knownRegion: '서울 강남구',
    incomingId: 'tmr-incoming',
  );

  group('ApiMatchRepository 고유 규칙', () {
    /// 🔴 **여기가 이 구현의 가장 위험한 자리다.** 화면은 `0=일`, 계약은
    /// `0=월`이라 한 칸 밀려도 **화면에는 아무 표시가 안 나고** 겹침 계산만
    /// 조용히 틀린다.
    test('토요일을 계약 요일 5 로 보낸다', () async {
      await buildRepo().saveTeamPrefs(
        't-thunder',
        const MatchPrefs(
          regions: ['서울 강남구'],
          times: [TimeSlot(day: 6, from: '10:00', to: '12:00')],
        ),
      );

      final slot = (lastPrefsBody['slots'] as List).first as Map;
      expect(slot['weekday'], 5);
      expect(slot['start_time'], '10:00:00', reason: '초를 붙여 보낸다');
    });

    /// 🔴 지역은 **이름이 아니라 id** 로 나간다.
    test('지역을 id 로 보낸다', () async {
      await buildRepo().saveTeamPrefs(
        't-thunder',
        const MatchPrefs(
          regions: ['서울 강남구'],
          times: [TimeSlot(day: 6, from: '10:00', to: '12:00')],
        ),
      );

      expect(lastPrefsBody['region_ids'], ['r-gangnam']);
    });

    /// 🔴 포지션 목록은 **약칭(`code`)** 을 담아 온다 — 화면이 다루는 값이
    /// 약칭이고, 계약으로 나갈 때 다시 id 가 된다.
    test('포지션은 약칭을 라벨로 담는다', () async {
      final list = await buildRepo().positions('football');

      expect(list.map((p) => p.label).toList(), ['MF', 'GK']);
    });
  });
}
