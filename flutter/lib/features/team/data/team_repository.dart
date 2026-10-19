import '../../auth/data/models/team_membership.dart';

/// 팀을 만들고 고치고 떠나는 계약(계약 3-3절).
///
/// 🔴 **읽기는 여기 없다** — 내 팀 목록은 `GET /me` 의 `teams[]` 가 이미
/// 준다(`AppUser.teams`). 따로 부르면 두 벌이 되고, 어긋나면 어느 쪽이 맞는지
/// 모르게 된다.
abstract class TeamRepository {
  /// 팀을 만든다. **만든 사람이 `owner` 로 함께 들어간다**(계약).
  ///
  /// 🔴 **[region] 은 목록의 값이어야 한다**(`regions.dart`). 「강남」·「강남구」
  /// 가 섞이면 「사람을 찾는 팀」의 지역 거르기에서 이 팀이 통째로 빠진다.
  Future<TeamMembership> createTeam({
    required String name,
    required String region,
  });

  /// 이름·지역을 고친다. 🔴 **보낸 것만 바뀐다.**
  Future<TeamMembership> updateTeam(
    String teamId, {
    String? name,
    String? region,
  });

  /// 팀에서 나간다(`DELETE /teams/{id}/members/{me}`).
  ///
  /// ⚠️ **주장은 못 나간다** — 남은 사람들의 팀이 주인 없이 남는다. 주장은
  /// 해체하거나 다른 사람에게 넘겨야 한다.
  Future<void> leaveTeam(String teamId);

  /// 팀을 해체한다(`DELETE /teams/{id}`). **주장만.** 되돌릴 수 없다.
  Future<void> disbandTeam(String teamId);
}

/// 이름 상한 — 계약이 넘치면 422 `VALIDATION_ERROR` 다.
const int kMaxTeamName = 30;

/// 새 팀의 종목. 🔴 **축구 하나다**(미결 `ho` 39번) — 되살리면 여기와 함께
/// 고르는 자리도 되살린다. 안 그러면 다른 종목 팀이 축구 판에 섞인다.
const String kTeamSportCode = 'football';
