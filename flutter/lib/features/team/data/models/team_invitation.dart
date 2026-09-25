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
    this.teamName = '',
    this.teamRegion = '',
    this.squadPublicSlug,
  });

  factory TeamInvitation.fromJson(Map<String, dynamic> json) => TeamInvitation(
        id: json['id'] as String,
        teamId: json['team_id'] as String,
        invitedUserId: json['invited_user_id'] as String,
        status: json['status'] as String,
        positionCode: json['position_code'] as String?,
        positionLabel: json['position_label'] as String?,
        /* 🔴 **`GET /me/invitations` 만 네 칸을 더 준다**(계약). 받는 사람은
           아직 그 팀 소속이 아니라 **팀 id 하나로는 판단할 수가 없다.**
           보낸 쪽 목록에는 없으므로 빈 값이 정상이다. */
        teamName: json['team_name'] as String? ?? '',
        teamRegion: json['team_region'] as String? ?? '',
        squadPublicSlug: json['squad_public_slug'] as String?,
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

  /// 🔴 **받은 목록에만 실린다**(계약 3-3절) — 보낸 쪽에서는 빈 값이다.
  final String teamName;
  final String teamRegion;

  /// 그 팀 판을 볼 수 있는 길. ⚠️ 스쿼드를 아직 안 만든 팀이면 `null` 이다.
  final String? squadPublicSlug;

  bool get isPending => status == 'pending';
}
