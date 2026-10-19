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
      /* 🔴 **`demo-inv-` 로 시작한다** — 홈의 시연용 자동 수락이 **가짜
         초대에만** 걸리게 하는 표시다(2026-09-25). 목업은 통째로 가짜라
         여기서도 그 표시를 단다. */
      id: 'demo-inv-${++_seq}',
      teamId: teamId,
      invitedUserId: userId,
      status: 'pending',
      positionCode: positionCode,
      positionLabel: positionCode == null ? null : _label[positionCode],
    );
  }

  /* 🔴 **나에게 온 초대 하나를 둔다** — 목업으로 화면을 볼 때 「초대를
     받았다」 갈래를 밟을 길이 그것뿐이다. */
  final List<TeamInvitation> _mine = [
    const TeamInvitation(
      id: 'demo-recv-1',
      teamId: 't-bears',
      invitedUserId: 'u-me',
      status: 'pending',
      positionCode: 'MF',
      positionLabel: '미드필더',
      teamName: '베어스 (mock)',
      teamRegion: '서울 송파구',
    ),
  ];

  @override
  Future<List<TeamInvitation>> myInvitations() async {
    await Future<void>.delayed(_delay);
    return List.of(_mine);
  }

  @override
  Future<void> acceptInvitation(String invitationId) async {
    await Future<void>.delayed(_delay);
    _answer(invitationId);
  }

  @override
  Future<void> rejectInvitation(String invitationId) async {
    await Future<void>.delayed(_delay);
    _answer(invitationId);
  }

  /// 🔴 **답한 것은 목록에서 빠진다**(계약: 아직 답 안 한 것만 온다).
  void _answer(String id) {
    final i = _mine.indexWhere((v) => v.id == id);
    if (i < 0) {
      throw const ApiException('없는 초대입니다',
          code: 'INVITATION_NOT_FOUND', status: 404);
    }
    _mine.removeAt(i);
  }

  static const _label = {
    'FW': '공격수',
    'MF': '미드필더',
    'DF': '수비수',
    'GK': '골키퍼',
  };
}
