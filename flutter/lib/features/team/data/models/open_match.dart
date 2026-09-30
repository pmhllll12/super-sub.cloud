/// 사람을 찾는 경기 한 건 — `GET /matches` 의 한 줄(계약 3-4절).
///
/// 🔴 **팀 id 를 몰라도 되는 유일한 경로다.** 다른 목록은 그 팀을 이미 알아야
/// 하므로, 이것이 생기기 전에는 **용병이 지원할 경기를 찾을 방법이 없었다.**
class OpenMatch {
  const OpenMatch({
    required this.id,
    required this.teamId,
    required this.teamName,
    required this.region,
    required this.sportCode,
    required this.playedAt,
    required this.place,
    this.needs = const [],
  });

  factory OpenMatch.fromJson(Map<String, dynamic> json) => OpenMatch(
        id: json['id'] as String,
        teamId: json['team_id'] as String,
        teamName: json['team_name'] as String? ?? '',
        region: json['region'] as String? ?? '',
        sportCode: json['sport_code'] as String? ?? '',
        playedAt: json['played_at'] as String? ?? '',
        place: json['place'] as String? ?? '',
        needs: ((json['needs'] as List?) ?? const [])
            .cast<Map<String, dynamic>>()
            .map(MatchNeed.fromJson)
            .toList(),
      );

  final String id;
  final String teamId;

  /* 🔴 **팀 이름·지역·종목이 함께 온다**(계약) — 용병이 경기를 고르는 기준이
     그 셋이라, 없으면 화면이 팀을 한 건씩 다시 물어야 한다. */
  final String teamName;
  final String region;
  final String sportCode;

  final String playedAt;
  final String place;

  /// 어느 자리를 몇 명 찾는가. ⚠️ **팀 대 팀으로 잡힌 경기는 늘 빈 배열**이다
  /// (모집이 필요 없다 — 계약 3-15절).
  final List<MatchNeed> needs;
}

/// 찾는 자리 한 줄.
class MatchNeed {
  const MatchNeed({
    required this.positionCode,
    required this.positionLabel,
    required this.headCount,
  });

  factory MatchNeed.fromJson(Map<String, dynamic> json) => MatchNeed(
        positionCode: json['position_code'] as String? ?? '',
        /* 🔴 **사람이 읽을 이름은 서버가 준다** — 약칭으로 「골키퍼」를
           지어내지 않는다(약칭이 종목을 넘나든다). */
        positionLabel: json['position_label'] as String? ?? '',
        headCount: json['head_count'] as int? ?? 0,
      );

  final String positionCode;
  final String positionLabel;
  final int headCount;
}
