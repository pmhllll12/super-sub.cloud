import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/team/data/models/team_member.dart';

void main() {
  _teamsInMockDb();
  late MockDb db;

  setUp(() => db = MockDb());

  test('종목은 풋살과 야구 2개다', () {
    expect(db.sports.map((s) => s.code), containsAll(['futsal', 'baseball']));
  });

  test('시드 계정 3종이 있다', () {
    expect(db.findUserById(MockDb.playerId), isNotNull);
    expect(db.findUserById(MockDb.managerId), isNotNull);
    expect(db.findUserById(MockDb.newbieId), isNotNull);
  });

  test('이메일로 사용자를 찾는다', () {
    final u = db.findUserById(MockDb.playerId)!;
    expect(db.findUserByEmail(u.email), equals(u));
  });

  test('없는 이메일이면 null이다', () {
    expect(db.findUserByEmail('nobody@nowhere.test'), isNull);
  });

  test('팀 관리자만 manager 역할을 갖는다', () {
    final roles = db.teamMembers
        .where((m) => m.userId == MockDb.managerId)
        .map((m) => m.role);
    expect(roles, contains(TeamRole.manager));

    final playerRoles = db.teamMembers
        .where((m) => m.userId == MockDb.playerId)
        .map((m) => m.role);
    expect(playerRoles, isNot(contains(TeamRole.manager)));
  });

  test('신규 가입자는 팀 소속이 없다 (빈 상태 UI 검증용)', () {
    final mine = db.teamMembers.where((m) => m.userId == MockDb.newbieId);
    expect(mine, isEmpty);
  });
}

/// `GET /me` 가 `teams[]` 를 함께 주므로 Mock 도 같은 모양이어야 한다 —
/// 안 그러면 목업 모드에서만 홈 판의 대상 팀이 없다.
void _teamsInMockDb() {
  group('AppUser.teams', () {
    test('소속이 있는 사용자는 팀이 채워진다', () {
      final db = MockDb();
      final manager = db.findUserById(MockDb.managerId)!;

      expect(manager.teams, hasLength(1));
      expect(manager.teams.single.name, '번개 풋살클럽');
      expect(manager.ownedTeamId, 't-thunder');
    });

    test('🔴 나간 팀은 안 들어온다 — 서버도 left_at 이 널인 행만 준다', () {
      final db = MockDb();
      final player = db.findUserById(MockDb.playerId)!;

      // t-bears 는 탈퇴 이력(tm-3)이라 빠져야 한다.
      expect(player.teams.map((t) => t.teamId), equals(['t-thunder']));
    });

    test('주장이 아니면 ownedTeamId 가 없지만 판은 연다', () {
      final player = MockDb().findUserById(MockDb.playerId)!;

      expect(player.ownedTeamId, isNull);
      expect(player.primaryTeamId, 't-thunder');
    });

    test('신규 가입자는 팀이 없다 — 빈 상태를 반드시 만들게 한다', () {
      expect(MockDb().findUserById(MockDb.newbieId)!.teams, isEmpty);
    });
  });
}
