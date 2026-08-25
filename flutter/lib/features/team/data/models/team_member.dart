enum TeamRole { member, manager }

/// ERD `team_member` 테이블.
///
/// 탈퇴는 행 삭제가 아니라 leftAt 기록이다(소프트 삭제). 경기·평가 이력이
/// 남아야 하기 때문이다. 재가입이 가능해 (team_id, user_id, joined_at)이
/// 유일키이므로, 한 사람이 같은 팀에 대해 여러 행을 가질 수 있다.
class TeamMember {
  const TeamMember({
    required this.id,
    required this.teamId,
    required this.userId,
    required this.role,
    required this.joinedAt,
    this.leftAt,
  });

  final String id;
  final String teamId;
  final String userId;
  final TeamRole role;
  final DateTime joinedAt;
  final DateTime? leftAt;

  bool get isActive => leftAt == null;

  @override
  bool operator ==(Object other) =>
      other is TeamMember &&
      other.id == id &&
      other.teamId == teamId &&
      other.userId == userId &&
      other.role == role &&
      other.joinedAt == joinedAt &&
      other.leftAt == leftAt;

  @override
  int get hashCode =>
      Object.hash(id, teamId, userId, role, joinedAt, leftAt);
}
