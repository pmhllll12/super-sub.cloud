import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/auth/data/models/app_user.dart';
import '../../features/auth/data/models/team_membership.dart';
import '../../features/card/data/models/player_card.dart';
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
  final List<PlayerCard> cards = [];

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

    // 🔴 **playerId 의 카드는 일부러 안 만든다.** 「카드 없음」 빈 상태를
    //    반드시 만들게 하는 장치다(위 newbieId 와 같은 이유). 카드는 화면에서
    //    실제로 만들어야 생긴다 — 계약도 「가입만으로는 안 생긴다」이다.
    cards.add(const PlayerCard(
      id: 'pc-$managerId',
      publicSlug: 'lee-gamdok-7f21',
      nickname: '이감독',
      tagline: 'THREE LUNGS',
    ));

    _attachTeams();
  }

  /// 사용자마다 [AppUser.teams] 를 채운다 — 실제 `GET /me` 가 `teams[]` 를
  /// 함께 주기 때문이다.
  ///
  /// 🔴 **시드 순서 때문에 따로 돈다.** users 를 만들 때는 teamMembers 가 아직
  /// 없어서 그 자리에서는 채울 수가 없다.
  ///
  /// 🔴 **`leftAt` 이 있는 행은 뺀다** — 서버도 `left_at` 이 널인 행만 추려서
  /// 준다. 안 거르면 나간 팀이 홈 판의 대상이 되어 「탈퇴한 팀의 스쿼드」를
  /// 그린다.
  void _attachTeams() {
    for (var i = 0; i < users.length; i += 1) {
      final user = users[i];
      final memberships = <TeamMembership>[];
      for (final tm in teamMembers) {
        if (tm.userId != user.id || tm.leftAt != null) continue;
        final team = teams.where((t) => t.id == tm.teamId).firstOrNull;
        if (team == null) continue;
        memberships.add(
          TeamMembership(
            teamId: team.id,
            name: team.name,
            region: team.region,
            sportCode: team.sportCode,
            role: tm.role == TeamRole.manager ? 'owner' : 'member',
            joinedAt: tm.joinedAt,
          ),
        );
      }
      users[i] = user.copyWith(teams: memberships);
    }
  }
}

final mockDbProvider = Provider<MockDb>((ref) => MockDb());
