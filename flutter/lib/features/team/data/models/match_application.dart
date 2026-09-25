/// 경기 한 건에 낸 **지원** — 계약 3-5절.
///
/// 🔴 **양쪽이 차야 확정이다.** 본인이 지원하면 `user_accepted_at` 만 차고,
/// 주장이 수락하면 `team_accepted_at` 이 찬다 — 둘 다 찼을 때만 [confirmed]
/// 가 참이다. 한쪽만 보고 「자리를 얻었다」고 말하면 안 된다.
///
/// ⚠️ **주장이 먼저 제안하는 길도 같은 표를 쓴다**(`user_id` 를 담아 POST).
/// 그때는 반대로 팀 쪽이 먼저 차 있다.
class MatchApplication {
  const MatchApplication({
    required this.id,
    required this.matchId,
    required this.userId,
    required this.nickname,
    required this.confirmed,
  });

  factory MatchApplication.fromJson(Map<String, dynamic> json) =>
      MatchApplication(
        id: json['id'] as String,
        matchId: json['match_id'] as String? ?? '',
        userId: json['user_id'] as String? ?? '',
        /* ⚠️ **닉네임이 함께 온다** — 주장이 명단을 볼 때 사람을 한 건씩
           다시 묻지 않게 하려는 것이다(계약). 본인 지원에는 쓸 데가 없다. */
        nickname: json['nickname'] as String? ?? '',
        confirmed: json['confirmed'] as bool? ?? false,
      );

  final String id;
  final String matchId;
  final String userId;
  final String nickname;

  /// 양쪽이 다 수락했는가 — 🔴 **이때만 자리가 잡힌 것이다.**
  final bool confirmed;
}
