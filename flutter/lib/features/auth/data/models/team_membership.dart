/// `GET /me` 의 `teams[]` 한 항목 — **내가 지금 속한 팀**이다.
///
/// 🔴 **내 팀을 얻는 데 새 경로가 필요 없다.** 계약이 이미 `GET /me` 에 실어
/// 주는데 앱이 그동안 버리고 있었을 뿐이다.
///
/// 서버가 `team_member` 에서 `left_at` 이 널인 행만 추려서 주므로 **나간 팀은
/// 애초에 안 온다** — 앱에서 거를 필요가 없다.
class TeamMembership {
  const TeamMembership({
    required this.teamId,
    required this.name,
    required this.region,
    required this.sportCode,
    required this.role,
    required this.joinedAt,
  });

  factory TeamMembership.fromJson(Map<String, dynamic> json) => TeamMembership(
        teamId: json['team_id'] as String,
        name: json['name'] as String,
        region: json['region'] as String,
        sportCode: json['sport_code'] as String,
        role: json['role'] as String,
        joinedAt: DateTime.parse(json['joined_at'] as String),
      );

  final String teamId;
  final String name;
  final String region;
  final String sportCode;

  /// `owner` · `member`. 🔴 **문자열 그대로 둔다** — 값이 늘 때 앱을 고치지
  /// 않으려는 것이고, 서버도 같은 이유로 enum 을 안 쓴다. 모르는 값이 오면
  /// 주장이 아닌 것으로 다룬다(권한을 지어내지 않는다).
  final String role;

  final DateTime joinedAt;

  /// 스쿼드를 **만들고 등재할 수 있는가**(계약 3-7절 권한표 — 「만들기·등재·제외는
  /// 주장만」). 읽기는 소속이면 된다.
  bool get isOwner => role == 'owner';

  @override
  bool operator ==(Object other) =>
      other is TeamMembership &&
      other.teamId == teamId &&
      other.name == name &&
      other.region == region &&
      other.sportCode == sportCode &&
      other.role == role &&
      other.joinedAt == joinedAt;

  @override
  int get hashCode =>
      Object.hash(teamId, name, region, sportCode, role, joinedAt);
}
