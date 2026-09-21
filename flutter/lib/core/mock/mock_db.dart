import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/auth/data/models/app_user.dart';
import '../../features/auth/data/models/team_membership.dart';
import '../../features/card/data/models/player_card.dart';
import '../../features/team/data/models/squad.dart';
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
  final List<Squad> squads = [];

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
      /* 🔴 **playerId 가 주장이다 (2026-09-21 에 바꿨다).** 전에는 managerId 가
         주장이고 playerId 는 팀원이었는데, 목업으로 들어가는 계정이 playerId
         라서 **자동 착석도 자리 끌기도 켜질 수가 없었다**(둘 다 주장 전용).
         목업의 존재 이유가 「서버 없이 화면 작업을 잇는 것」인데 그게 깨졌다.
         「주장이 아닌 사람」 갈래는 managerId 가 맡는다. */
      TeamMember(
        id: 'tm-1',
        teamId: 't-thunder',
        userId: playerId,
        role: TeamRole.manager,
        joinedAt: DateTime(2026, 2, 12),
      ),
      TeamMember(
        id: 'tm-2',
        teamId: 't-thunder',
        userId: managerId,
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

    /* 🔴 **「카드 없음」 빈 상태는 newbieId 가 맡는다 (2026-09-21 정정).**
       전에는 playerId 의 카드를 일부러 안 만들어 그 갈래를 강제했는데,
       목업으로 들어가는 계정이 playerId 라서 **자동 착석을 영영 못 봤다**
       (카드가 없으면 앉힐 것이 없다). newbieId 는 카드도 팀도 없으므로
       빈 상태 화면은 그쪽으로 확인한다. */
    cards.add(const PlayerCard(
      id: 'pc-$playerId',
      publicSlug: 'baek-seonggeom-3a71',
      nickname: '백성검',
    ));
    cards.add(const PlayerCard(
      id: 'pc-$managerId',
      publicSlug: 'lee-gamdok-7f21',
      nickname: '이감독',
      /* 🔴 **기본 별명과 다른 글자를 준다 (2026-09-21).** 전에는 여기도
         'THREE LUNGS' 였는데, 내 카드는 tagline·style 이 없어 **기본 별명**이
         그 글자라 판에서 두 카드가 똑같아 보였다 — 어느 것이 내 카드인지
         목업으로 확인할 수가 없었다. */
      tagline: 'IRON GLOVES',
    ));

    // 🔴 **t-bears 에는 스쿼드를 안 둔다** — 「아직 안 만든 팀」 갈래를 반드시
    //    밟게 하는 장치다(계약은 그때 404 SQUAD_NOT_FOUND 를 낸다).
    squads.add(const Squad(
      id: 'sq-thunder',
      teamId: 't-thunder',
      publicSlug: 'aB3xK9mQ2pL7vN4t',
      formation: '5:5',
      members: [
        SquadMember(
          id: 'sm-1',
          playerCardId: 'pc-$managerId',
          cardPublicSlug: 'lee-gamdok-7f21',
          nickname: '이감독',
          positionCode: 'GK',
          positionLabel: '골키퍼',
          gridCol: 1,
          gridRow: 3,
          accepted: true,
        ),
        // 🔴 **칸이 없는 등재** — 판에 안 올린 사람도 포지션으로 앉는다.
        //    서버의 기존 행이 거의 전부 이 꼴이라 이 갈래를 Mock 에서도 밟는다.
        SquadMember(
          id: 'sm-2',
          playerCardId: 'pc-newbie',
          cardPublicSlug: null,
          nickname: '박신입',
          positionCode: 'MF',
          positionLabel: '미드필더',
          accepted: true,
        ),
      ],
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
