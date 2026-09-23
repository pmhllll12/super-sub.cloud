import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/auth/data/models/app_user.dart';
import 'package:super_sub/features/auth/data/models/team_membership.dart';

AppUser _userWith(List<TeamMembership> teams) => AppUser(
      id: 'u1',
      email: 'a@b.test',
      nickname: '나',
      createdAt: DateTime(2026, 9, 1),
      teams: teams,
    );

TeamMembership _team(String id, String role) => TeamMembership(
      teamId: id,
      name: '팀 $id',
      region: '서울 강남',
      sportCode: 'football',
      role: role,
      joinedAt: DateTime(2026, 7, 1),
    );

void main() {
  test('GET /me 의 teams 항목을 읽는다', () {
    final m = TeamMembership.fromJson(const {
      'team_id': '9a2e',
      'name': '번개FC',
      'region': '서울 강남',
      'sport_code': 'football',
      'role': 'member',
      'joined_at': '2026-07-01T00:00:00Z',
    });

    expect(m.teamId, '9a2e');
    expect(m.name, '번개FC');
    expect(m.region, '서울 강남');
    expect(m.sportCode, 'football');
    expect(m.role, 'member');
    expect(m.isOwner, isFalse);
    expect(m.joinedAt, DateTime.utc(2026, 7, 1));
  });

  test('role 이 owner 면 주장이다', () {
    expect(_team('t1', 'owner').isOwner, isTrue);
  });

  test('모르는 role 은 주장이 아니다 — 문자열 그대로 둔다', () {
    // 🔴 enum 으로 가두지 않는 이유: 값이 늘 때 앱을 고치지 않으려는 것이고,
    //    서버도 같은 이유로 문자열을 쓴다.
    final m = _team('t1', 'coach');
    expect(m.role, 'coach');
    expect(m.isOwner, isFalse);
  });

  group('AppUser', () {
    test('팀이 없으면 대상 팀도 없다', () {
      final u = _userWith(const []);
      expect(u.ownedTeamId, isNull);
      expect(u.primaryTeamId, isNull);
    });

    test('주장인 팀이 ownedTeamId 다', () {
      final u = _userWith([_team('t1', 'member'), _team('t2', 'owner')]);
      expect(u.ownedTeamId, 't2');
    });

    test('주장인 팀이 없으면 속한 첫 팀을 판으로 연다', () {
      // 🔴 주장이 아니어도 판은 **읽을 수** 있다(계약 3-7절 권한표) — 못 여는
      //    것은 만들기·등재다.
      final u = _userWith([_team('t1', 'member')]);
      expect(u.ownedTeamId, isNull);
      expect(u.primaryTeamId, 't1');
    });

    test('주장인 팀이 있으면 그것이 우선이다', () {
      final u = _userWith([_team('t1', 'member'), _team('t2', 'owner')]);
      expect(u.primaryTeamId, 't2');
    });

    test('teams 가 다르면 다른 사용자다', () {
      // 🔴 == 에 teams 가 안 섞이면 팀이 바뀌어도 화면이 안 다시 그려진다.
      expect(_userWith(const []) == _userWith([_team('t1', 'owner')]), isFalse);
    });
  });
}
