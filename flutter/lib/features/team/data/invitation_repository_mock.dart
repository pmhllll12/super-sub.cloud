import '../../../core/network/api_client.dart';
import 'invitation_repository.dart';
import 'models/team_invitation.dart';

/// 백엔드 없이 도는 초대 저장소.
///
/// 🔴 **자동 수락을 넣지 않았다.** 웹에는 1.5초 뒤 스스로 수락하는 데모
/// 장치가 있고 그 주석에 「실제 배포에서는 걷어야 한다」가 달려 있다. 옮겨
/// 오면 앱에서도 걷어내야 할 것이 하나 더 생기므로 **처음부터 안 넣는다.**
class MockInvitationRepository implements InvitationRepository {
  MockInvitationRepository();

  static const _delay = Duration(milliseconds: 300);

  /// 내가 **주장인** 팀. 여기 없는 팀으로 부르면 403 처럼 던진다.
  static const _captainOf = {'t-thunder'};

  int _seq = 0;

  @override
  Future<TeamInvitation> invite(
    String teamId, {
    required String userId,
    String? positionCode,
  }) async {
    await Future<void>.delayed(_delay);

    if (!_captainOf.contains(teamId)) {
      throw const ApiException('그 팀의 주장이 아닙니다',
          code: 'FORBIDDEN', status: 403);
    }

    return TeamInvitation(
      id: 'inv-${++_seq}',
      teamId: teamId,
      invitedUserId: userId,
      status: 'pending',
      positionCode: positionCode,
      positionLabel: positionCode == null ? null : _label[positionCode],
    );
  }

  static const _label = {
    'FW': '공격수',
    'MF': '미드필더',
    'DF': '수비수',
    'GK': '골키퍼',
  };
}
