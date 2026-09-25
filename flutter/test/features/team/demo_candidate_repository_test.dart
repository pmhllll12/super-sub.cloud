import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/candidate_repository.dart';
import 'package:super_sub/features/team/data/demo_candidate_repository.dart';
import 'package:super_sub/features/team/data/invitation_repository.dart';
import 'package:super_sub/features/team/data/models/squad_candidate.dart';
import 'package:super_sub/features/team/data/models/team_invitation.dart';

/// 진짜 서버를 흉내 내는 속 저장소 — **가짜 후보는 여기 없다.**
class _RealCandidates implements CandidateRepository {
  final asked = <String>[];

  @override
  Future<List<SquadCandidate>> candidates(
    String teamId, {
    required String positionCode,
    String? grade,
  }) async {
    asked.add(positionCode);
    return const [
      SquadCandidate(userId: 'u-real', nickname: '진짜사람', grade: 'B'),
    ];
  }

  @override
  Future<String?> featuredVideoId(String cardPublicSlug) async => 'v-real';
}

class _RealInvites implements InvitationRepository {
  final sent = <String>[];

  @override
  Future<List<TeamInvitation>> myInvitations() async => const [];
  @override
  Future<void> acceptInvitation(String id) async {}
  @override
  Future<void> rejectInvitation(String id) async {}

  @override
  Future<TeamInvitation> invite(
    String teamId, {
    required String userId,
    String? positionCode,
  }) async {
    sent.add(userId);
    return TeamInvitation(
      id: 'inv-real',
      teamId: teamId,
      invitedUserId: userId,
      status: 'pending',
      positionCode: positionCode,
    );
  }
}

void main() {
  group('DemoCandidateRepository', () {
    late _RealCandidates inner;
    late DemoCandidateRepository repo;

    setUp(() {
      inner = _RealCandidates();
      repo = DemoCandidateRepository(inner);
    });

    /// 🔴 **진짜 목록을 가리지 않는다** — 섞는 것이지 대신하는 것이 아니다.
    test('진짜 후보 옆에 가짜 하나가 선다', () async {
      final list = await repo.candidates('t-1', positionCode: 'DF');

      expect(list.any((c) => c.userId == 'u-real'), isTrue);
      expect(list.where((c) => c.userId == kDemoCandidateId), hasLength(1));
    });

    /// 🔴 **이름에 `(mock)` 이 있다** — 진짜와 섞이므로 한눈에 갈려야 한다.
    test('가짜 후보는 이름으로 드러난다', () async {
      final demo = (await repo.candidates('t-1', positionCode: 'DF'))
          .firstWhere((c) => c.userId == kDemoCandidateId);

      expect(demo.nickname, contains('mock'));
    });

    /// 🔴 **등급 필터는 그대로 서버로 간다** — 가짜를 끼우느라 진짜 검색을
    /// 망가뜨리면 안 된다. 가짜는 고른 등급을 **따라간다.**
    test('등급을 고르면 가짜도 그 등급으로 선다', () async {
      final list =
          await repo.candidates('t-1', positionCode: 'DF', grade: 'S');
      final demo = list.firstWhere((c) => c.userId == kDemoCandidateId);

      expect(demo.grade, 'S');
      expect(inner.asked, ['DF'], reason: '속 저장소는 그대로 불린다');
    });

    /// 🔴 **가짜에겐 대표 영상이 없다** — 서버에 없는 슬러그를 물으면 404 다.
    test('가짜의 대표 영상은 묻지 않는다', () async {
      expect(await repo.featuredVideoId(kDemoCardSlug), isNull);
      expect(await repo.featuredVideoId('real-slug'), 'v-real');
    });
  });

  group('DemoInvitationRepository', () {
    late _RealInvites inner;
    late DemoInvitationRepository repo;

    setUp(() {
      inner = _RealInvites();
      repo = DemoInvitationRepository(inner);
    });

    /// 🔴 **가짜를 부르는 것은 서버로 안 나간다.** 나가면 서버에 없는
    /// 사용자 id 라 404 이고, 무엇보다 **진짜 팀에 가짜가 등록된다.**
    test('가짜를 부르면 서버를 안 부른다', () async {
      final inv = await repo.invite('t-1', userId: kDemoCandidateId);

      expect(inner.sent, isEmpty);
      expect(inv.isPending, isTrue);
    });

    test('진짜 사람은 그대로 서버로 간다', () async {
      await repo.invite('t-1', userId: 'u-real');

      expect(inner.sent, ['u-real']);
    });
  });
}
