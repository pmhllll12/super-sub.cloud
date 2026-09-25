import '../../../core/network/api_client.dart';
import 'invitation_repository.dart';
import 'models/team_invitation.dart';

/// `fastapi/` 백엔드에 붙는 실제 구현. 계약은 `api-contract.md` 3-3절.
class ApiInvitationRepository implements InvitationRepository {
  ApiInvitationRepository(this._api);

  final ApiClient _api;

  @override
  Future<TeamInvitation> invite(
    String teamId, {
    required String userId,
    String? positionCode,
  }) async =>
      TeamInvitation.fromJson(
        await _api.post('/teams/${Uri.encodeComponent(teamId)}/invitations', {
          'invited_user_id': userId,
          /* 🔴 **선택 칸은 뺀다.** `null` 을 실어 보내는 것과 안 보내는 것은
             서버마다 다르게 읽힐 수 있고, 계약이 「선택」이라고만 적어 둔
             자리에서는 안 보내는 쪽이 해석이 하나뿐이다. */
          'position_code': ?positionCode,
        }),
      );
}
