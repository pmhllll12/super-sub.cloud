import '../../../core/mock/mock_db.dart';
import '../../../core/network/api_client.dart';
import 'models/squad.dart';
import 'models/team_member.dart';
import 'squad_repository.dart';

/// 백엔드 없이 도는 스쿼드 저장소.
///
/// 🔴 **`t-bears` 에는 스쿼드를 안 둔다**(`MockDb` 시드) — 「아직 안 만든 팀」
/// 갈래를 반드시 밟게 하는 장치다.
///
/// 🔴 **서버가 막는 것을 여기서도 막는다**(주장만 · 이미 찬 칸 · 이미 등재된
/// 카드). Mock 이 다 받아 주면 목업으로 만든 화면이 진짜 서버에서 처음으로
/// 403·409 를 만난다 — Mock 이 일부러 실패하는 것과 같은 이유다.
class MockSquadRepository implements SquadRepository {
  MockSquadRepository(this._db, {this.captainOfTeams = const {}});

  final MockDb _db;

  /// 내가 **주장인** 팀들. 여기 없는 팀에 쓰면 403 처럼 던진다.
  final Set<String> captainOfTeams;

  static const _delay = Duration(milliseconds: 300);

  @override
  Future<Squad?> squadOf(String teamId) async {
    // Mock 이 즉시 성공하면 로딩 UI 를 안 만들게 된다(다른 Mock 과 같은 지연).
    await Future<void>.delayed(_delay);
    return _find(teamId);
  }

  @override
  Future<Squad> enlist(
    String teamId, {
    required String playerCardId,
    required String positionCode,
    int? gridCol,
    int? gridRow,
  }) async {
    await Future<void>.delayed(_delay);
    final squad = _requireWritable(teamId);

    // 🔴 스쿼드당 카드 1회(부록 D.7) — 서버는 409 ALREADY_ENLISTED 다.
    if (squad.members.any((m) => m.playerCardId == playerCardId)) {
      throw const ApiException('이미 등재된 카드입니다',
          code: 'ALREADY_ENLISTED', status: 409);
    }
    _requireFreeSeat(squad, gridCol, gridRow, skipMemberId: null);

    final member = SquadMember(
      id: 'sm-${DateTime.now().microsecondsSinceEpoch}',
      playerCardId: playerCardId,
      cardPublicSlug: _slugOf(playerCardId),
      nickname: _nicknameOf(playerCardId),
      positionCode: positionCode,
      positionLabel: positionCode,
      gridCol: gridCol,
      gridRow: gridRow,
      accepted: true,
    );
    return _replace(squad, [...squad.members, member]);
  }

  @override
  Future<Squad> moveSeat(
    String teamId, {
    required String memberId,
    required String positionCode,
    int? gridCol,
    int? gridRow,
  }) async {
    await Future<void>.delayed(_delay);
    final squad = _requireWritable(teamId);
    if (!squad.members.any((m) => m.id == memberId)) {
      throw const ApiException('이 팀 스쿼드의 등재가 아닙니다',
          code: 'MEMBER_NOT_FOUND', status: 404);
    }
    _requireFreeSeat(squad, gridCol, gridRow, skipMemberId: memberId);

    return _replace(squad, [
      for (final m in squad.members)
        if (m.id == memberId)
          SquadMember(
            id: m.id,
            playerCardId: m.playerCardId,
            cardPublicSlug: m.cardPublicSlug,
            nickname: m.nickname,
            positionCode: positionCode,
            positionLabel: positionCode,
            gridCol: gridCol,
            gridRow: gridRow,
            accepted: m.accepted,
          )
        else
          m,
    ]);
  }

  @override
  Future<Squad> removeSeat(String teamId, {required String memberId}) async {
    await Future<void>.delayed(_delay);
    final squad = _requireWritable(teamId);
    if (!squad.members.any((m) => m.id == memberId)) {
      throw const ApiException('이 팀 스쿼드의 등재가 아닙니다',
          code: 'MEMBER_NOT_FOUND', status: 404);
    }
    // 🔴 카드는 안 지운다 — 스쿼드에서 빠질 뿐이다.
    return _replace(
      squad,
      [for (final m in squad.members) if (m.id != memberId) m],
    );
  }

  @override
  Future<void> removeTeamMember(String teamId, {required String userId}) async {
    await Future<void>.delayed(_delay);
    _requireWritable(teamId);
    /* ⚠️ 서버는 행을 지우지 않고 `left_at` 을 채운다 — Mock 도 같게 한다.
       그래야 `AppUser.teams`(널인 행만 추린다)가 실제와 같이 움직인다. */
    for (var i = 0; i < _db.teamMembers.length; i += 1) {
      final tm = _db.teamMembers[i];
      if (tm.teamId != teamId || tm.userId != userId || tm.leftAt != null) {
        continue;
      }
      _db.teamMembers[i] = TeamMember(
        id: tm.id,
        teamId: tm.teamId,
        userId: tm.userId,
        role: tm.role,
        joinedAt: tm.joinedAt,
        leftAt: DateTime.now(),
      );
      return;
    }
    throw const ApiException('그 팀의 구성원이 아닙니다',
        code: 'NOT_A_MEMBER', status: 404);
  }

  Squad? _find(String teamId) {
    for (final s in _db.squads) {
      if (s.teamId == teamId) return s;
    }
    return null;
  }

  /// 쓰기가 되는 스쿼드인가 — 있어야 하고, 내가 **주장**이어야 한다.
  Squad _requireWritable(String teamId) {
    final squad = _find(teamId);
    if (squad == null) {
      throw const ApiException('스쿼드를 아직 안 만들었습니다',
          code: 'SQUAD_NOT_FOUND', status: 404);
    }
    if (!captainOfTeams.contains(teamId)) {
      throw const ApiException('주장만 할 수 있습니다',
          code: 'FORBIDDEN', status: 403);
    }
    return squad;
  }

  /// 🔴 이미 찬 칸에는 못 놓는다 — 서버도 같은 칸에 둘을 허용하지 않는다.
  void _requireFreeSeat(
    Squad squad,
    int? col,
    int? row, {
    required String? skipMemberId,
  }) {
    if (col == null || row == null) return;
    for (final m in squad.members) {
      if (m.id == skipMemberId) continue;
      if (m.gridCol == col && m.gridRow == row) {
        throw const ApiException('그 자리에는 이미 사람이 있습니다',
            code: 'SEAT_TAKEN', status: 409);
      }
    }
  }

  Squad _replace(Squad squad, List<SquadMember> members) {
    final next = Squad(
      id: squad.id,
      teamId: squad.teamId,
      publicSlug: squad.publicSlug,
      formation: squad.formation,
      members: members,
    );
    _db.squads[_db.squads.indexOf(squad)] = next;
    return next;
  }

  String? _slugOf(String playerCardId) {
    for (final c in _db.cards) {
      if (c.id == playerCardId) return c.publicSlug;
    }
    return null;
  }

  String _nicknameOf(String playerCardId) {
    for (final c in _db.cards) {
      if (c.id == playerCardId) return c.nickname;
    }
    return '';
  }
}
