import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/auth/data/models/app_user.dart';
import '../../features/team/data/models/sport.dart';
import '../../features/team/data/models/team.dart';
import '../../features/team/data/models/team_member.dart';

/// 모든 Mock 리포지토리가 공유하는 단일 인메모리 저장소.
///
/// feature마다 각자 가짜 데이터를 들면 서로 모순된다 — 존재하지 않는 팀을
/// 참조하는 경기 같은 것. ERD와 같은 구조로 한 곳에 담고 모두 여기서 읽는다.
class MockDb {
  MockDb() {
    _seed();
  }

  static const playerId = 'u-player';
  static const managerId = 'u-manager';
  static const newbieId = 'u-newbie';

  final List<Sport> sports = [];
  final List<AppUser> users = [];
  final List<Team> teams = [];
  final List<TeamMember> teamMembers = [];

  AppUser? findUserByEmail(String email) {
    for (final u in users) {
      if (u.email == email) return u;
    }
    return null;
  }

  AppUser? findUserById(String id) {
    for (final u in users) {
      if (u.id == id) return u;
    }
    return null;
  }

  void _seed() {
    sports.addAll(const [
      Sport(code: 'futsal', name: '풋살'),
      Sport(code: 'baseball', name: '야구'),
    ]);

    users.addAll([
      AppUser(
        id: playerId,
        email: 'player@supersub.test',
        nickname: '백성검',
        createdAt: DateTime(2026, 3, 2),
      ),
      AppUser(
        id: managerId,
        email: 'manager@supersub.test',
        nickname: '이감독',
        createdAt: DateTime(2026, 2, 10),
      ),
      AppUser(
        id: newbieId,
        email: 'newbie@supersub.test',
        nickname: '박신입',
        createdAt: DateTime(2026, 8, 24),
      ),
    ]);

    teams.addAll(const [
      Team(
        id: 't-thunder',
        sportCode: 'futsal',
        name: '번개 풋살클럽',
        region: '서울 강남',
      ),
      Team(
        id: 't-bears',
        sportCode: 'baseball',
        name: '동네 베어스',
        region: '서울 송파',
      ),
    ]);

    teamMembers.addAll([
      TeamMember(
        id: 'tm-1',
        teamId: 't-thunder',
        userId: managerId,
        role: TeamRole.manager,
        joinedAt: DateTime(2026, 2, 12),
      ),
      TeamMember(
        id: 'tm-2',
        teamId: 't-thunder',
        userId: playerId,
        role: TeamRole.member,
        joinedAt: DateTime(2026, 3, 5),
      ),
      // 소프트 삭제 사례 — 탈퇴 이력이 남아 있어야 한다.
      TeamMember(
        id: 'tm-3',
        teamId: 't-bears',
        userId: playerId,
        role: TeamRole.member,
        joinedAt: DateTime(2026, 3, 10),
        leftAt: DateTime(2026, 6, 30),
      ),
    ]);
    // 신규 가입자(newbieId)는 의도적으로 소속을 넣지 않는다.
    // 빈 상태 UI를 반드시 만들도록 강제하는 장치다.
  }
}

final mockDbProvider = Provider<MockDb>((ref) => MockDb());
