import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../features/auth/data/models/app_user.dart';
import '../../features/auth/data/models/team_membership.dart';
import '../../features/card/data/models/player_card.dart';
import '../../features/profile/presentation/widgets/player_card_view.dart'
    show kDefaultCardAlias;
import '../../features/team/data/models/squad.dart';
import '../../features/team/data/models/sport.dart';
import '../../features/team/data/models/team.dart';
import '../../features/team/data/models/team_member.dart';
import '../../features/video/data/models/my_video.dart';
import '../../features/video/data/models/video_report.dart';

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

  /// 클립은 **주인과 함께** 담는다. `MyVideo` 자신은 소유자를 안 싣는다
  /// (계약의 `GET /videos` 가 내 것만 주므로 서버도 안 싣는다) — 그래서
  /// 여러 사람을 흉내 내는 Mock 쪽에서만 짝지어 둔다.
  final List<({String userId, MyVideo video})> videos = [];

  List<MyVideo> videosOf(String userId) => [
        for (final row in videos)
          if (row.userId == userId) row.video,
      ];

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
    /* 🔴 **꾸며진 채로 시드한다 (2026-09-22, 사용자 요청).** 전에는 `style`
       이 없어 목업을 올릴 때마다 **기본 연두 카드**가 떴다 — 폰에 새로 올릴
       때마다 색을 다시 고쳐야 했다. 실기기에서 쓰던 그 카드(하늘색 바탕 ·
       흰 자국)를 그대로 옮겼다.

       🔴 **`tagline` 을 함께 둔다.** `aliasOf` 는 「`style` 이 있는데
       `tagline` 이 비었다」를 **일부러 지운 것**으로 읽는다 — 색만 넣으면
       카드에서 글자가 사라진다(웹이 헤드리스로 겪은 그 자리). */
    cards.add(PlayerCard(
      id: 'pc-$playerId',
      publicSlug: 'baek-seonggeom-3a71',
      nickname: '백성검',
      tagline: kDefaultCardAlias,
      style: CardStyle.fromJson(const {
        'bg': '#118AB2',
        'logo': '#FFFFFF',
        'text_color': '#1E3029',
        'brush': 12,
        'brush_color': '#FFFFFF',
        'brush_scale': 1.4,
        'brush_x': 6,
        'brush_y': 35,
        'mode': 'full',
      }),
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

    _seedVideos();
    attachTeams();
  }

  /// 🔴 **네 갈래를 다 둔다** — 분석 완료 · 분석 중 · 분석 안 함 · 규격 반려.
  /// 하나라도 빠지면 그 상태의 화면을 안 만들게 되고, 진짜 서버에서 처음
  /// 본다(Mock 이 「일부러 실패한다」와 같은 이유).
  void _seedVideos() {
    videos.addAll([
      (
        userId: playerId,
        video: MyVideo(
          id: 'v-analyzed',
          sportCode: 'football',
          storageKey: 'videos/$playerId/first-goal.mp4',
          durationMs: 10200,
          createdAt: DateTime(2026, 9, 20, 14, 30),
          passed: true,
          analysisJobId: 'job-1',
          analysisStatus: 'succeeded',
          title: '왼발 감아차기',
        ),
      ),
      (
        userId: playerId,
        video: MyVideo(
          id: 'v-running',
          sportCode: 'football',
          storageKey: 'videos/$playerId/practice.mp4',
          durationMs: 8400,
          createdAt: DateTime(2026, 9, 19, 9, 5),
          passed: true,
          analysisJobId: 'job-2',
          analysisStatus: 'running',
        ),
      ),
      (
        userId: playerId,
        video: MyVideo(
          id: 'v-raw',
          sportCode: 'football',
          storageKey: 'videos/$playerId/team-match.mp4',
          durationMs: 21000,
          createdAt: DateTime(2026, 9, 18, 19, 40),
          passed: true,
        ),
      ),
      (
        userId: playerId,
        video: MyVideo(
          id: 'v-rejected',
          sportCode: 'football',
          storageKey: 'videos/$playerId/too-long.mp4',
          durationMs: 92000,
          createdAt: DateTime(2026, 9, 17, 11, 0),
          passed: false,
          rejectReason: '길이가 상한을 넘습니다: 92초 (상한 60초)',
        ),
      ),
    ]);
    // 신규 가입자(newbieId)에게는 영상을 안 준다 — 「아직 올린 영상이
    // 없습니다」 빈 상태를 반드시 만들게 하는 장치다.
  }

  /// 시드 리포트 한 벌. 🔴 축을 **여섯** 둔다 — 레이더 색이 여섯이고, 그
  /// 상한(축구 인스텝 슛)에서 겹치거나 잘리지 않는지 목업으로 봐야 한다.
  VideoReport reportFor(String videoId) => const VideoReport(
        summary: '디딤발 무릎 굽히기가 강점입니다.',
        points: [
          ReportPoint(title: '흔들리지 않는 축', evidence: '디딤발이 안정적으로 놓였습니다.'),
          // 🔴 **호칭이 없는 항목도 둔다** — 못 받은 항목의 문장까지 사라지면
          //    안 된다는 규칙(CCC 47)을 목업에서도 밟는다.
          ReportPoint(title: null, evidence: '팔로스루가 중간에 멈춥니다.'),
          ReportPoint(title: '정확한 임팩트', evidence: '공의 가운데를 맞혔습니다.'),
        ],
        scenes: [
          ReportScene(at: '0:02', what: '임팩트 프레임'),
          ReportScene(at: '0:04', what: '팔로스루 최고점'),
        ],
        radar: [
          RadarAxis(name: '디딤발 무릎 굽히기', stat: 88.5),
          RadarAxis(name: '디딤발 위치', stat: 72),
          RadarAxis(name: '임팩트 정확도', stat: 64),
          RadarAxis(name: '팔로스루', stat: 41),
          RadarAxis(name: '상체 기울기', stat: 79),
          RadarAxis(name: '스윙 궤적', stat: 55),
        ],
        totalScore: 71,
        overallGrade: 'B',
        savedAt: '2026-09-20',
      );

  /// 사용자마다 [AppUser.teams] 를 채운다 — 실제 `GET /me` 가 `teams[]` 를
  /// 함께 주기 때문이다.
  ///
  /// 🔴 **시드 순서 때문에 따로 돈다.** users 를 만들 때는 teamMembers 가 아직
  /// 없어서 그 자리에서는 채울 수가 없다.
  ///
  /// 🔴 **`leftAt` 이 있는 행은 뺀다** — 서버도 `left_at` 이 널인 행만 추려서
  /// 준다. 안 거르면 나간 팀이 홈 판의 대상이 되어 「탈퇴한 팀의 스쿼드」를
  /// 그린다.
  /// 🔴 **팀이 생기거나 사라지면 다시 부른다** — `AppUser.teams` 는 여기서
  /// 만들어지는 파생값이라, 안 부르면 방금 만든 팀이 프로필에 안 뜬다.
  void attachTeams() {
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
