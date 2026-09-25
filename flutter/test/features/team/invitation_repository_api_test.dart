import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:super_sub/core/network/api_client.dart';
import 'package:super_sub/features/auth/data/token_store.dart';
import 'package:super_sub/features/team/data/invitation_repository_api.dart';

import '../../contract/invitation_repository_contract.dart';

/// 마지막으로 보낸 본문. 구현체별 의무를 보는 자리다.
Map<String, dynamic> lastBody = {};

ApiInvitationRepository buildRepo() {
  final client = MockClient((req) async {
    lastBody = req.body.isEmpty
        ? <String, dynamic>{}
        : jsonDecode(req.body) as Map<String, dynamic>;

    if (!req.url.path.contains('/teams/t-thunder/invitations')) {
      return http.Response.bytes(
        utf8.encode(jsonEncode({
          'error': {'code': 'FORBIDDEN', 'message': '주장이 아닙니다'},
        })),
        403,
      );
    }

    return http.Response.bytes(
      utf8.encode(jsonEncode({
        'id': 'inv-1',
        'team_id': 't-thunder',
        'invited_user_id': lastBody['invited_user_id'],
        'status': 'pending',
        'created_at': '2026-09-25T09:00:00Z',
        'responded_at': null,
        'position_code': lastBody['position_code'],
        'position_label': lastBody['position_code'] == null ? null : '수비수',
      })),
      201,
    );
  });

  return ApiInvitationRepository(
    ApiClient(client: client, tokens: InMemoryTokenStore()),
  );
}

void main() {
  runInvitationRepositoryContract(
    'ApiInvitationRepository',
    buildRepo,
    myTeamId: 't-thunder',
    foreignTeamId: 't-bears',
    userId: 'u-kim',
  );

  group('ApiInvitationRepository 고유 규칙', () {
    /// 🔴 자리를 안 정한 초대는 `position_code` 를 **빼서** 보낸다. `null` 을
    /// 실어 보내는 것과 안 보내는 것이 같아 보이지만, 「보낸 칸만 바뀐다」류의
    /// 경로에서 한 번 데인 적이 있어 **선택 칸은 뺀다**로 통일한다.
    test('자리를 안 정하면 그 칸을 안 보낸다', () async {
      await buildRepo().invite('t-thunder', userId: 'u-kim');

      expect(lastBody.containsKey('position_code'), isFalse);
      expect(lastBody['invited_user_id'], 'u-kim');
    });

    test('자리를 정하면 그 칸을 보낸다', () async {
      await buildRepo()
          .invite('t-thunder', userId: 'u-kim', positionCode: 'GK');

      expect(lastBody['position_code'], 'GK');
    });
  });
}
