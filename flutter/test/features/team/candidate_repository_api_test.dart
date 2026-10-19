import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:super_sub/core/network/api_client.dart';
import 'package:super_sub/features/auth/data/token_store.dart';
import 'package:super_sub/features/team/data/candidate_repository_api.dart';

import '../../contract/candidate_repository_contract.dart';

http.Response jsonList(List<Map<String, dynamic>> body, int status) =>
    http.Response.bytes(utf8.encode(jsonEncode(body)), status);

http.Response jsonErr(String code, int status) => http.Response.bytes(
      utf8.encode(jsonEncode({
        'error': {'code': code, 'message': code},
      })),
      status,
    );

/// 후보 목록. 계약의 모양 그대로 — 카드 없는 사람은 칸이 전부 `null` 이다.
const _df = <Map<String, dynamic>>[
  {
    'user_id': 'u-line',
    'nickname': '라인세우기',
    'card_public_slug': 'line-3a92',
    'grade': 'A',
    'provisional': false,
    'notes': ['수비 라인을 먼저 올립니다'],
  },
  {
    'user_id': 'u-kim',
    'nickname': '끝까지뛰는',
    'card_public_slug': 'kim-abc1',
    'grade': 'C',
    'provisional': false,
    'notes': ['첫 터치를 앞으로 길게 놓습니다'],
  },
  {
    'user_id': 'u-newbie',
    'nickname': '오재현',
    'card_public_slug': null,
    'grade': null,
    'provisional': null,
    'notes': null,
  },
];

/// 마지막으로 나간 요청의 쿼리. 구현체별 의무를 보는 자리다.
Map<String, String> lastQuery = {};

ApiCandidateRepository buildRepo() {
  final client = MockClient((req) async {
    lastQuery = req.url.queryParameters;
    final path = req.url.path;

    if (path.contains('/cards/kim-abc1/featured-video')) {
      return http.Response.bytes(
        utf8.encode(jsonEncode({'video_id': 'v-kim-1', 'expires_in': 900})),
        200,
      );
    }
    if (path.contains('/featured-video')) {
      // 대표 영상을 안 세운 사람 — 404 가 정상이다.
      return jsonErr('VIDEO_NOT_FOUND', 404);
    }

    if (!path.contains('/teams/t-thunder/squad/candidates')) {
      return jsonErr('FORBIDDEN', 403);
    }
    final pos = req.url.queryParameters['position_code'];
    if (pos == null || !{'FW', 'MF', 'DF', 'GK'}.contains(pos)) {
      return jsonErr('UNKNOWN_POSITION', 422);
    }
    if (pos != 'DF') return jsonList(const [], 200);

    // 🔴 **서버가 거른다** — 쿼리가 실제로 실려야 이 갈래를 탄다.
    final grade = req.url.queryParameters['grade'];
    if (grade == null) return jsonList(_df, 200);
    return jsonList(
      _df.where((c) => c['grade'] == grade).toList(),
      200,
    );
  });

  return ApiCandidateRepository(
    ApiClient(client: client, tokens: InMemoryTokenStore()),
  );
}

void main() {
  runCandidateRepositoryContract(
    'ApiCandidateRepository',
    buildRepo,
    teamId: 't-thunder',
    position: 'DF',
    emptyPosition: 'GK',
    unknownPosition: 'PG',
    foreignTeamId: 't-bears',
    cardSlugWithVideo: 'kim-abc1',
    cardSlugWithoutVideo: 'line-3a92',
  );

  group('ApiCandidateRepository 고유 규칙', () {
    /// 🔴 계약 테스트에 두지 않는다 — **어떻게** 거르는지는 구현체의 의무다.
    /// 이 시험이 없으면 「받아서 화면에서 거르기」로 몰래 바꿔도 계약 시험이
    /// 통과해 버린다.
    test('등급을 서버로 보낸다', () async {
      await buildRepo()
          .candidates('t-thunder', positionCode: 'DF', grade: 'A');

      expect(lastQuery['position_code'], 'DF');
      expect(lastQuery['grade'], 'A');
    });

    /// 🔴 「등급 상관없음」은 **`grade` 를 빼서** 보낸다 — `grade=any` 같은
    /// 값을 지어 보내지 않는다.
    test('등급 상관없음이면 grade 를 아예 안 보낸다', () async {
      await buildRepo().candidates('t-thunder', positionCode: 'DF');

      expect(lastQuery.containsKey('grade'), isFalse);
    });

    /// 🔴 닉네임에 한글·공백이 있어도 경로가 깨지지 않아야 한다.
    test('팀 id 를 인코딩해서 넣는다', () async {
      await expectLater(
        buildRepo().candidates('t bears/../x', positionCode: 'DF'),
        throwsA(anything),
      );
    });
  });
}
