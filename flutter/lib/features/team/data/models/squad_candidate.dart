/// 빈 자리를 채울 **후보 한 명** — `GET /teams/{id}/squad/candidates` 의 한 줄.
///
/// 🔴 **등급·문구가 여기 이미 실려 온다**(계약 3-14절, `paik` 33번). 후보마다
/// `GET /cards/{slug}/grade` 를 다시 부르지 않는다 — 웹이 그 이유로 이 칸들을
/// 응답에 넣었다.
///
/// 🔴 **점수·거리는 응답에 없다.** 순서는 서버가 이미 정렬했으므로 화면이
/// 다시 줄 세우지 않는다.
class SquadCandidate {
  const SquadCandidate({
    required this.userId,
    required this.nickname,
    this.cardPublicSlug,
    this.grade,
    this.provisional,
    this.notes = const [],
  });

  factory SquadCandidate.fromJson(Map<String, dynamic> json) => SquadCandidate(
        userId: json['user_id'] as String,
        nickname: json['nickname'] as String,
        cardPublicSlug: json['card_public_slug'] as String?,
        grade: json['grade'] as String?,
        provisional: json['provisional'] as bool?,
        /* 🔴 `null` 을 빈 목록으로 바꾸는 것은 **안 그리기 위해서**다. 없는
           줄을 지어내는 것과는 반대 방향이다 — 아래 [notes] 주석 참고. */
        notes: (json['notes'] as List?)?.cast<String>().toList() ?? const [],
      );

  final String userId;
  final String nickname;

  /// 카드 슬러그. 아직 카드를 안 만든 사람은 `null` 이고, 그러면 썸네일도
  /// 물어볼 데가 없다.
  final String? cardPublicSlug;

  /// `S`~`F`. 🔴 **모르면 `null`** 이고 그 후보는 목록에서 사라지지 않는다 —
  /// 서버가 뒤로 보낼 뿐이다.
  final String? grade;

  /// 「검수 전」 — 아직 사람이 확인하지 않은 등급이다. 등급을 모르면 `null`.
  final bool? provisional;

  /// 카드에 그릴 불릿. 🔴 **`null`·한 줄·두 줄이 모두 정상이고 화면이
  /// 지어내지 않는다**(계약이 못 박았다). 여기서는 빈 목록으로 들어온다.
  final List<String> notes;

  /// 썸네일·칭호를 물어볼 카드가 있는가.
  bool get hasCard => cardPublicSlug != null;
}
