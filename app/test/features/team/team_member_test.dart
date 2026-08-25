import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/models/team_member.dart';

void main() {
  final joined = DateTime(2026, 3, 1);

  test('leftAt이 없으면 활성 소속이다', () {
    final m = TeamMember(
      id: 'tm1',
      teamId: 't1',
      userId: 'u1',
      role: TeamRole.member,
      joinedAt: joined,
    );
    expect(m.isActive, isTrue);
  });

  test('leftAt이 있으면 비활성 소속이다 (소프트 삭제)', () {
    final m = TeamMember(
      id: 'tm1',
      teamId: 't1',
      userId: 'u1',
      role: TeamRole.member,
      joinedAt: joined,
      leftAt: DateTime(2026, 6, 1),
    );
    expect(m.isActive, isFalse);
  });

  test('같은 값이면 동등하다', () {
    final a = TeamMember(
      id: 'tm1', teamId: 't1', userId: 'u1',
      role: TeamRole.manager, joinedAt: joined,
    );
    final b = TeamMember(
      id: 'tm1', teamId: 't1', userId: 'u1',
      role: TeamRole.manager, joinedAt: joined,
    );
    expect(a, equals(b));
  });
}
