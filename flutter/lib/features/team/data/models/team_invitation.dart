/// 팀 초대 한 건 — 계약 3-3절 `team_invitation`.
///
/// 🔴 **동의 없이 팀에 넣지 않는다**(2026-09-10 박민호 결정). 주장이 초대를
/// 보내고 **받은 사람 본인이 수락해야** 소속이 된다.
class TeamInvitation {
  const TeamInvitation({
    required this.id,
    required this.teamId,
    required this.invitedUserId,
    required this.status,
    this.positionCode,
    this.positionLabel,
  });

  factory TeamInvitation.fromJson(Map<String, dynamic> json) => TeamInvitation(
        id: json['id'] as String,
        teamId: json['team_id'] as String,
        invitedUserId: json['invited_user_id'] as String,
        status: json['status'] as String,
        positionCode: json['position_code'] as String?,
        positionLabel: json['position_label'] as String?,
      );

  final String id;
  final String teamId;
  final String invitedUserId;

  /// `pending` → `accepted` / `rejected` / `cancelled`. **`pending` 일 때만**
  /// 답할 수 있다.
  final String status;

  /// 「부르는 자리」. 🔴 **둘 다 `null` 일 수 있다** — 자리를 안 정한 초대
  /// (「우리 팀에 오세요」)가 정상이다.
  final String? positionCode;
  final String? positionLabel;

  bool get isPending => status == 'pending';
}
