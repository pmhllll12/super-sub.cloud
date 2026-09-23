import '../../../core/network/api_client.dart';
import '../../auth/data/models/team_membership.dart';
import 'team_repository.dart';

/// `fastapi/` 백엔드에 붙는 실제 구현. 계약은 `api-contract.md` 3-3절.
class ApiTeamRepository implements TeamRepository {
  ApiTeamRepository(this._api, {required this.myUserId});

  final ApiClient _api;

  /// 나가기 경로가 **내 멤버 id** 를 요구한다(`/members/{id}`).
  final String myUserId;

  @override
  Future<TeamMembership> createTeam({
    required String name,
    required String region,
  }) async {
    final made = await _api.post('/teams', {
      'name': name,
      'region': region,
      // 🔴 계약이 종목을 요구한다. 없는 코드면 422 UNKNOWN_SPORT 다.
      'sport_code': kTeamSportCode,
    });

    /* 🔴 **스쿼드를 함께 만들되 실패해도 팀은 살린다**(웹과 같은 처리).
       판이 없으면 나중에 주장이 다시 만들면 되지만, 여기서 던지면 **이미
       만들어진 팀**을 두고 「실패했다」고 말하게 된다. */
    try {
      await _api.post('/teams/${Uri.encodeComponent(made['id'] as String)}/squad');
    } on ApiException {
      // 판은 나중에 만들면 된다.
    }
    return _asMembership(made, role: 'owner');
  }

  @override
  Future<TeamMembership> updateTeam(
    String teamId, {
    String? name,
    String? region,
  }) async {
    // 🔴 보낸 것만 바뀐다 — `null` 을 실으면 「지우라」가 된다.
    final row = await _api.patch('/teams/${Uri.encodeComponent(teamId)}', {
      'name': ?name,
      'region': ?region,
    });
    return _asMembership(row, role: 'owner');
  }

  @override
  Future<void> leaveTeam(String teamId) => _api.delete(
        '/teams/${Uri.encodeComponent(teamId)}'
        '/members/${Uri.encodeComponent(myUserId)}',
      );

  @override
  Future<void> disbandTeam(String teamId) =>
      _api.delete('/teams/${Uri.encodeComponent(teamId)}');

  /* 🔴 **`GET /me` 의 `teams[]` 모양으로 맞춘다.** 화면이 아는 팀은 그 한
     가지뿐이라(`AppUser.teams`), 여기서 다른 모양을 돌려주면 목록에 끼워
     넣을 때마다 변환이 필요해진다. `joined_at` 은 응답에 없으므로 지금으로
     둔다 — 방금 들어간 것이 사실이다. */
  TeamMembership _asMembership(Map<String, dynamic> row, {required String role}) =>
      TeamMembership(
        teamId: row['id'] as String,
        name: row['name'] as String,
        region: row['region'] as String,
        sportCode: row['sport_code'] as String? ?? kTeamSportCode,
        role: role,
        joinedAt: DateTime.now(),
      );
}
