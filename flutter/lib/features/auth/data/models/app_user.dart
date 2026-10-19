import 'team_membership.dart';

/// ERD `user` 테이블. Dart 코어의 이름과 겹치지 않도록 AppUser로 둔다.
class AppUser {
  const AppUser({
    required this.id,
    required this.email,
    required this.nickname,
    required this.createdAt,
    this.teams = const [],
    this.isNicknameSearchable = true,
  });

  final String id;
  final String email;
  final String nickname;
  final DateTime createdAt;

  /// 🔴 **지인 검색 노출 여부** — 닉네임으로 나를 찾을 수 있는가.
  /// 용병 매칭의 `is_searchable` 과는 **다른 값이다**(계약).
  /// 옛 서버가 이 칸을 안 주면 「보인다」로 본다(기존 동작이 그랬다).
  final bool isNicknameSearchable;

  /// 내가 지금 속한 팀들(`GET /me` 의 `teams`). 🔴 **옛 서버는 이 칸을 안 줄 수
  /// 있어** 기본값이 빈 목록이다 — 없으면 「팀이 없다」로 다룬다.
  final List<TeamMembership> teams;

  /// 내가 주장인 팀 — 스쿼드를 **만들고 등재할 수 있는** 팀이다.
  String? get ownedTeamId {
    for (final t in teams) {
      if (t.isOwner) return t.teamId;
    }
    return null;
  }

  /// 홈 판에 그릴 대상 팀 — 주장인 팀이 우선, 없으면 속한 첫 팀.
  ///
  /// 🔴 **주장이 아니어도 판은 읽을 수 있다**(계약 3-7절: 「팀 화면에서 보기는
  /// 소속이면 된다」). 주장만 할 수 있는 것은 만들기·등재·제외다.
  String? get primaryTeamId =>
      ownedTeamId ?? (teams.isEmpty ? null : teams.first.teamId);

  AppUser copyWith({
    String? nickname,
    List<TeamMembership>? teams,
    bool? isNicknameSearchable,
  }) =>
      AppUser(
        id: id,
        email: email,
        nickname: nickname ?? this.nickname,
        createdAt: createdAt,
        teams: teams ?? this.teams,
        isNicknameSearchable: isNicknameSearchable ?? this.isNicknameSearchable,
      );

  @override
  bool operator ==(Object other) =>
      other is AppUser &&
      other.id == id &&
      other.email == email &&
      other.nickname == nickname &&
      other.createdAt == createdAt &&
      other.isNicknameSearchable == isNicknameSearchable &&
      _sameTeams(other.teams);

  bool _sameTeams(List<TeamMembership> other) {
    if (other.length != teams.length) return false;
    for (var i = 0; i < teams.length; i += 1) {
      if (other[i] != teams[i]) return false;
    }
    return true;
  }

  @override
  // 🔴 팀은 `Object.hashAll` 로 따로 섞는다 — 리스트를 그대로 넣으면 동일성이
  //    참조 기준이 되어 == 와 어긋난다.
  int get hashCode => Object.hash(
        id,
        email,
        nickname,
        createdAt,
        isNicknameSearchable,
        Object.hashAll(teams),
      );
}
