import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/team/data/models/team_member.dart';

void main() {
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
