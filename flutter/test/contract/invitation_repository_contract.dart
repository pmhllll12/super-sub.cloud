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

    test('남의 팀 이름으로는 못 부른다', () async {
      await expectLater(
        repo.invite(foreignTeamId, userId: userId, positionCode: 'DF'),
        throwsA(anything),
      );
    });
  });
}
