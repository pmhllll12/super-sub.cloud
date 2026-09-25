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
}
