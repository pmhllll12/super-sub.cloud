import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/invitation_repository.dart';

/// InvitationRepository 의 모든 구현체가 지켜야 하는 계약 — 계약 3-3절
/// 「팀 초대」.
///
/// 🔴 **동의 없이 팀에 넣지 않는다**(2026-09-10 박민호 결정) — 주장이 초대를
/// 보내고 받은 사람이 수락해야 소속이 된다. 그래서 이 저장소에는 「바로
/// 넣기」가 없다.
void runInvitationRepositoryContract(
  String name,
  InvitationRepository Function() build, {
  required String myTeamId,
  required String foreignTeamId,
  required String userId,
}) {
  group('$name — InvitationRepository 계약', () {
    late InvitationRepository repo;

    setUp(() => repo = build());

    test('초대를 보내면 대기중으로 돌아온다', () async {
      final inv =
          await repo.invite(myTeamId, userId: userId, positionCode: 'DF');

      expect(inv.teamId, myTeamId);
      expect(inv.invitedUserId, userId);
      expect(inv.isPending, isTrue);
    });

    /// 🔴 자리를 정해 부르면 그 자리가 초대에 실린다 — 받는 쪽 화면이
    /// 「어느 자리로 부르는지」를 보여 줄 수 있어야 한다.
    test('부르는 자리가 초대에 실린다', () async {
      final inv =
          await repo.invite(myTeamId, userId: userId, positionCode: 'GK');

      expect(inv.positionCode, 'GK');
    });

    /// 🔴 **자리를 안 정한 초대도 정상이다**(「우리 팀에 오세요」). 계약이
    /// `position_code` 를 선택으로 둔 이유다.
    test('자리를 안 정해도 초대할 수 있다', () async {
      final inv = await repo.invite(myTeamId, userId: userId);

      expect(inv.positionCode, isNull);
      expect(inv.isPending, isTrue);
    });

    /// 🔴 **받은 쪽에서 읽고 답할 수 있어야 한다** (2026-09-25 사용자:
    /// 「웹이든 앱이든 알림오는거 똑같이 있어야 하고 ... 진짜로 서로
    /// 연결되어있어야」). 이게 없으면 웹에서 보낸 초대를 앱에서 못 받는다.
    test('나에게 온 초대를 읽는다', () async {
      final mine = await repo.myInvitations();

      expect(mine, isNotEmpty);
      expect(mine.every((i) => i.isPending), isTrue,
          reason: '아직 답 안 한 것만 온다(계약)');
    });

    /// 🔴 **팀 이름이 함께 와야 한다** — 팀 id 하나로는 어느 팀의 초대인지
    /// 판단할 수가 없다(계약이 그래서 네 칸을 더 준다).
    test('받은 초대에는 팀 이름이 실려 있다', () async {
      final mine = await repo.myInvitations();

      expect(mine.first.teamName, isNotEmpty);
    });

    test('받은 초대를 수락하면 목록에서 빠진다', () async {
      final first = (await repo.myInvitations()).first;

      await repo.acceptInvitation(first.id);

      expect((await repo.myInvitations()).any((i) => i.id == first.id), isFalse);
    });

    test('받은 초대를 거절해도 목록에서 빠진다', () async {
      final first = (await repo.myInvitations()).first;

      await repo.rejectInvitation(first.id);

      expect((await repo.myInvitations()).any((i) => i.id == first.id), isFalse);
    });

    test('남의 팀 이름으로는 못 부른다', () async {
      await expectLater(
        repo.invite(foreignTeamId, userId: userId, positionCode: 'DF'),
        throwsA(anything),
      );
    });
  });
}
