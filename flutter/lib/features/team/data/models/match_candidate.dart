/// 「맞는 상대」 후보 한 팀 — `GET /teams/{id}/match-candidates`.
///
/// 🔴 **유사도 점수가 없다.** 판 크기가 같고, 자기 팀이 아니고, 상대 로스터가
/// 그 인원만큼 찼고, 경기 조건을 등록한 팀만 — 전부 **하드 필터**로 걸러진 뒤
/// **이미 정렬된 순서**로 온다. 화면이 다시 줄 세우지 않는다.
class MatchCandidate {
  const MatchCandidate({
    required this.teamId,
    required this.name,
    required this.regionLabel,
    required this.formation,
    this.reasons = const [],
  });

  factory MatchCandidate.fromJson(Map<String, dynamic> json) => MatchCandidate(
        teamId: json['team_id'] as String,
        name: json['team_name'] as String,
        regionLabel: json['region_label'] as String? ?? '',
        formation: json['formation'] as String? ?? '',
        reasons: ((json['reasons'] as List?) ?? const [])
            .cast<Map<String, dynamic>>()
            .map(MatchReason.fromJson)
            .toList(),
      );

  final String teamId;
  final String name;
  final String regionLabel;

  /// `5:5` 처럼 온다 — 우리와 같은 크기만 후보가 된다.
  final String formation;

  /// **왜 이 팀이 나왔는가.** 🔴 **서버가 준 사실값 문장 그대로**다
  /// (「토요일 11:00~12:00 겹침」) — 화면이 겹침을 다시 계산하지 않는다
  /// (계약의 「하지 말 것」: 다시 계산하면 서버와 다른 답이 나온다).
  ///
  /// ⚠️ **빈 배열도 정상이다** — 소프트 근거가 0개라는 뜻이고, 하드 필터는
  /// 통과했으므로 목록에 남는다.
  final List<MatchReason> reasons;
}

/// 후보로 나온 근거 한 줄.
class MatchReason {
  const MatchReason({required this.kind, required this.detail});

  factory MatchReason.fromJson(Map<String, dynamic> json) => MatchReason(
        kind: json['kind'] as String? ?? '',
        detail: json['detail'] as String? ?? '',
      );

  /// `time` · `region` 등. 화면이 색·아이콘을 가를 때만 쓴다.
  final String kind;

  /// 사람이 읽는 문장. **이 글자를 그대로 보여 준다.**
  final String detail;
}

/// 팀 대 팀 경기 신청 한 건 — 계약 3-15절.
class TeamMatchRequest {
  const TeamMatchRequest({
    required this.id,
    required this.requesterTeamId,
    required this.targetTeamId,
    required this.status,
    required this.playedAt,
    required this.place,
    this.matchId,
    this.targetTeamName = '',
    this.targetSquadSlug,
    this.requesterTeamName = '',
    this.requesterSquadSlug,
  });

  factory TeamMatchRequest.fromJson(Map<String, dynamic> json) =>
      TeamMatchRequest(
        id: json['id'] as String,
        requesterTeamId: json['requester_team_id'] as String,
        targetTeamId: json['target_team_id'] as String,
        status: json['status'] as String,
        playedAt: json['proposed_played_at'] as String? ?? '',
        place: json['proposed_place'] as String? ?? '',
        matchId: json['match_id'] as String?,
        targetTeamName: json['target_team_name'] as String? ?? '',
        targetSquadSlug: json['target_squad_public_slug'] as String?,
        requesterTeamName: json['requester_team_name'] as String? ?? '',
        requesterSquadSlug: json['requester_squad_public_slug'] as String?,
      );

  final String id;
  final String requesterTeamId;
  final String targetTeamId;

  /// `pending` → `accepted` / `rejected` / `cancelled`.
  final String status;
  final String playedAt;
  final String place;

  /// 🔴 **수락되어야 찬다** — 그 전에는 `null` 이다. 「걸었다」와 「잡혔다」를
  /// 가르는 값이라, 이것이 있어야 대기 화면을 띄운다.
  final String? matchId;

  /* 🔴 **이 이름들을 캐시하지 않는다**(계약). 팀 이름이 바뀌면 다음 조회에
     바로 반영되는 값이라, 들고 있으면 조용히 옛 이름이 남는다. */
  final String targetTeamName;
  final String requesterTeamName;

  /// 대기 화면이 **상대 판을 그리는 데** 쓴다.
  /// ⚠️ **스쿼드를 아직 안 만든 팀이면 `null` 이고 그게 정상이다.**
  final String? targetSquadSlug;
  final String? requesterSquadSlug;

  bool get isPending => status == 'pending';
  bool get isAccepted => status == 'accepted';
}
