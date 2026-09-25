import 'models/team_invitation.dart';

/// 팀 초대 — 계약 3-3절.
///
/// 🔴 **「바로 넣기」가 없다.** `POST /teams/{id}/members` 로 동의 없이 넣는
/// 길은 일부러 두지 않았다(2026-09-10 박민호 결정) — 검색 대상자가 모르는 채
/// 어딘가에 등록되는 것을 막는다.
abstract class InvitationRepository {
  /// 그 사람을 팀으로 부른다 — `POST /teams/{id}/invitations`. **주장만**.
  ///
  /// [positionCode] 는 **선택**이다 — 안 주면 자리를 안 정한 초대
  /// (「우리 팀에 오세요」)가 되고 그것도 정상이다.
  Future<TeamInvitation> invite(
    String teamId, {
    required String userId,
    String? positionCode,
  });

  /// **나에게 온** 초대 — `GET /me/invitations`. 아직 답 안 한 것만 온다.
  ///
  /// 🔴 **여기에 팀 이름·지역이 함께 온다**(계약 3-3절). 받는 사람은 아직 그
  /// 팀 소속이 아니라 **팀 id 하나로는 판단할 수가 없다.**
  ///
  /// 🔴 **웹과 앱을 잇는 자리다** — 웹에서 보낸 초대가 앱에 뜨는 길이 이것
  /// 하나뿐이다(2026-09-25 사용자 요청).
  Future<List<TeamInvitation>> myInvitations();

  /// 받은 초대를 수락 — `POST /me/invitations/{id}/accept`.
  Future<void> acceptInvitation(String invitationId);

  /// 받은 초대를 거절 — `POST /me/invitations/{id}/reject`.
  Future<void> rejectInvitation(String invitationId);
}
