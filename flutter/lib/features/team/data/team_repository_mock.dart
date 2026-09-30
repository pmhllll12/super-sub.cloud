import '../../../core/mock/mock_db.dart';
import '../../../core/network/api_client.dart';
import '../../auth/data/models/team_membership.dart';
import 'models/team.dart';
import 'models/team_member.dart';
import 'regions.dart';
import 'team_repository.dart';

/// 백엔드 없이 도는 팀 저장소.
class MockTeamRepository implements TeamRepository {
  MockTeamRepository(this._db, {required this.userId});

  final MockDb _db;
  final String userId;

  static const _delay = Duration(milliseconds: 300);

  @override
  Future<TeamMembership> createTeam({
    required String name,
    required String region,
  }) async {
    await Future<void>.delayed(_delay);
    _check(name: name, region: region);

    final team = Team(
      id: 't-${DateTime.now().microsecondsSinceEpoch}',
      sportCode: kTeamSportCode,
      name: name.trim(),
      region: region.trim(),
    );
    _db.teams.add(team);
    // 🔴 **만든 사람이 owner 로 함께 들어간다**(계약).
    _db.teamMembers.add(TeamMember(
      id: 'tm-${team.id}',
      teamId: team.id,
      userId: userId,
      role: TeamRole.manager,
      joinedAt: DateTime.now(),
    ));
    return _membership(team, 'owner');
  }

  @override
  Future<TeamMembership> updateTeam(
    String teamId, {
    String? name,
    String? region,
  }) async {
    await Future<void>.delayed(_delay);
    _check(name: name, region: region);
    _requireOwner(teamId);

    final at = _db.teams.indexWhere((t) => t.id == teamId);
    if (at < 0) {
      throw const ApiException('없는 팀입니다',
          code: 'TEAM_NOT_FOUND', status: 404);
    }
    final was = _db.teams[at];
    final next = Team(
      id: was.id,
      sportCode: was.sportCode,
      // 보낸 것만 바뀐다.
      name: name?.trim() ?? was.name,
      region: region?.trim() ?? was.region,
    );
    _db.teams[at] = next;
    return _membership(next, 'owner');
  }

  @override
  Future<void> leaveTeam(String teamId) async {
    await Future<void>.delayed(_delay);
    final me = _myRow(teamId);
    /* 🔴 **주장은 못 나간다** — 남은 사람들의 팀이 주인 없이 남는다. Mock 이
       받아 주면 그 오류 문구를 안 만들게 되고 진짜 서버에서 처음 막힌다. */
    if (me.role == TeamRole.manager) {
      throw const ApiException('주장은 팀을 나갈 수 없습니다 — 해체하거나 넘겨 주세요',
          code: 'OWNER_CANNOT_LEAVE', status: 409);
    }
    _db.teamMembers.removeWhere((m) => m.id == me.id);
  }

  @override
  Future<void> disbandTeam(String teamId) async {
    await Future<void>.delayed(_delay);
    _requireOwner(teamId);
    _db.teams.removeWhere((t) => t.id == teamId);
    // 🔴 소속과 판도 함께 간다 — 남으면 없는 팀을 가리키는 행이 된다.
    _db.teamMembers.removeWhere((m) => m.teamId == teamId);
    _db.squads.removeWhere((s) => s.teamId == teamId);
  }

  /// 🔴 **이름·지역을 Mock 도 검사한다.** 받아 주면 그 오류 화면을 안 만들게
  /// 되고, 특히 **목록에 없는 지역**은 진짜 서버에서도 통과해 버려서
  /// 「저장은 됐는데 남의 검색에 안 뜨는」 팀이 된다.
  void _check({String? name, String? region}) {
    if (name != null && (name.trim().isEmpty || name.trim().length > kMaxTeamName)) {
      throw const ApiException('팀 이름을 확인해 주세요',
          code: 'VALIDATION_ERROR', status: 422);
    }
    if (region != null && !isRegion(region)) {
      throw const ApiException('목록에 있는 지역을 골라 주세요',
          code: 'VALIDATION_ERROR', status: 422);
    }
  }

  TeamMember _myRow(String teamId) {
    for (final m in _db.teamMembers) {
      if (m.teamId == teamId && m.userId == userId && m.leftAt == null) {
        return m;
      }
    }
    throw const ApiException('그 팀의 소속이 아닙니다',
        code: 'FORBIDDEN', status: 403);
  }

  void _requireOwner(String teamId) {
    if (_myRow(teamId).role != TeamRole.manager) {
      throw const ApiException('주장만 할 수 있습니다',
          code: 'FORBIDDEN', status: 403);
    }
  }

  TeamMembership _membership(Team t, String role) => TeamMembership(
        teamId: t.id,
        name: t.name,
        region: t.region,
        sportCode: t.sportCode,
        role: role,
        joinedAt: DateTime.now(),
      );
}
