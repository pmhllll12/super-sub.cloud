import '../../../core/network/api_client.dart';
import '../match_prefs.dart';
import '../match_prefs_server.dart';
import 'match_repository.dart';
import 'models/match_candidate.dart';
import 'models/review_option.dart';
import 'regions.dart';

/// 🔴 **시연용 자동 수락까지 걸리는 시간.** 심사에서 상대 기기로 수락을 눌러
/// 줄 사람이 없다 — 웹의 `DEMO_ACCEPT_MS`(자리 초대)와 같은 결이고,
/// **걷어낼 때도 같이 걷는다.**
///
/// ⚠️ 자리 초대(1.5초)보다 길게 둔다 — 「신청했다」를 읽을 틈이 있어야 하고,
/// 대기 화면이 곧바로 덮치면 무엇이 일어났는지 안 보인다.
const Duration kDemoAcceptAfter = Duration(seconds: 4);

/// 백엔드 없이 도는 팀 매칭 저장소.
///
/// 🔴 **서버가 막는 것을 여기서도 막는다**(뒤집힌 시간 · 겹쳐 걸기). Mock 이
/// 다 받아 주면 목업으로 만든 화면이 진짜 서버에서 처음으로 422·409 를 만난다.
class MockMatchRepository implements MatchRepository {
  MockMatchRepository();

  static const _delay = Duration(milliseconds: 300);

  /// 팀별 조건. 🔴 **`t-bears` 에는 안 둔다** — 「아직 안 정한 팀」 갈래를
  /// 반드시 밟게 하는 장치다.
  final Map<String, MatchPrefs> _prefs = {};

  final List<TeamMatchRequest> _requests = [];

  @override
  Future<List<RefItem>> regions() async {
    await Future<void>.delayed(_delay);
    /* 지역 이름은 붙박이 목록에서 오고 id 는 여기서 지어낸다 — 진짜 서버는
       `GET /regions` 가 둘 다 준다. 🔴 **이름은 웹과 글자까지 같아야 한다**
       (`regions.dart` 머리말). */
    return [
      for (final label in kRegions) RefItem(id: 'r-$label', label: label),
    ];
  }

  @override
  Future<List<RefItem>> positions(String sportCode) async {
    await Future<void>.delayed(_delay);
    return const [
      RefItem(id: 'p-FW', label: 'FW'),
      RefItem(id: 'p-MF', label: 'MF'),
      RefItem(id: 'p-DF', label: 'DF'),
      RefItem(id: 'p-GK', label: 'GK'),
    ];
  }

  @override
  Future<MatchPrefs?> teamPrefs(String teamId) async {
    await Future<void>.delayed(_delay);
    return _prefs[teamId];
  }

  @override
  Future<void> saveTeamPrefs(String teamId, MatchPrefs prefs) async {
    await Future<void>.delayed(_delay);

    for (final t in prefs.times) {
      // 🔴 서버의 422 INVALID_TIME_SLOT 과 같은 자리다.
      if (t.from.compareTo(t.to) >= 0) {
        throw const ApiException('끝 시각이 시작보다 빠릅니다',
            code: 'INVALID_TIME_SLOT', status: 422);
      }
    }
    // 🔴 **통째로 교체**다(계약) — 합치지 않는다.
    _prefs[teamId] = prefs;
  }

  /* 🔴 **이름에 `(mock)` 을 붙인다** (2026-09-25 사용자 요청: 「팀 매칭이나
     선수 꺼에서 mock 은 따로 mock 이라고 넣어줘」). 진짜 서버 값과 섞이면
     **무엇을 보고 있는지 모른 채** 판단하게 된다 — 상대 팀 이름이 가짜인 것을
     한참 못 알아본 적이 있다. 진짜 서버로 돌릴 때는 이 저장소가 아예 안 쓰여
     표시도 같이 사라진다. */
  /// 🔴 시연에서 「비슷한 팀」이 비어 있으면 아무것도 못 보여 준다. 근거가
  /// **있는 팀과 없는 팀을 섞어** 둔다 — 빈 근거도 정상이라는 갈래를 밟는다.
  static const _seed = [
    MatchCandidate(
      teamId: 't-gangnam',
      name: 'FC 강남 (mock)',
      regionLabel: '서울 강남구',
      formation: '5:5',
      reasons: [
        MatchReason(kind: 'time', detail: '토요일 06:30~20:00 겹침'),
        MatchReason(kind: 'region', detail: '같은 구(서울 강남구)'),
      ],
    ),
    MatchCandidate(
      teamId: 't-judge',
      name: '심사위원 FC (mock)',
      regionLabel: '서울 강남구',
      formation: '5:5',
      reasons: [
        MatchReason(kind: 'time', detail: '토요일 10:00~12:00 겹침'),
        MatchReason(kind: 'region', detail: '같은 구(서울 강남구)'),
      ],
    ),
    MatchCandidate(
      teamId: 't-judge6',
      name: '심사위원 6팀 (mock)',
      regionLabel: '서울 강남구',
      formation: '5:5',
      reasons: [MatchReason(kind: 'time', detail: '토요일 10:00~12:00 겹침')],
    ),
    // 🔴 근거가 하나도 없는 팀 — 하드 필터는 통과했으므로 목록에 남는다.
    MatchCandidate(
      teamId: 't-cloud',
      name: '강남 클라우드FC (mock)',
      regionLabel: '서울 강남구',
      formation: '5:5',
    ),
  ];

  @override
  Future<List<MatchCandidate>> candidates(String teamId) async {
    await Future<void>.delayed(_delay);
    return List.of(_seed);
  }

  @override
  Future<TeamMatchRequest> requestMatch(
    String teamId, {
    required String targetTeamId,
    required String playedAt,
    required String place,
  }) async {
    await Future<void>.delayed(_delay);

    /* 🔴 같은 상대에 **겹쳐 걸 수 없다**(409). 거절·취소된 것과 이미 지난
       경기는 안 센다 — 안 그러면 한 번 붙은 팀과 다시는 못 붙는다. */
    final live = _requests.any((r) =>
        r.targetTeamId == targetTeamId && (r.isPending || r.isAccepted));
    if (live) {
      throw const ApiException('이미 걸어 둔 신청이 있습니다',
          code: 'TEAM_MATCH_REQUEST_ALREADY_LIVE', status: 409);
    }

    final target = _seed.firstWhere(
      (t) => t.teamId == targetTeamId,
      orElse: () => const MatchCandidate(
          teamId: '', name: '상대 팀', regionLabel: '', formation: '5:5'),
    );

    final made = TeamMatchRequest(
      id: 'tmr-${_requests.length + 1}',
      requesterTeamId: teamId,
      targetTeamId: targetTeamId,
      status: 'pending',
      playedAt: playedAt,
      place: place,
      targetTeamName: target.name,
      // 상대 판은 화면이 지어낸다(Mock 에는 진짜 스쿼드가 없다).
      targetSquadSlug: null,
    );
    _requests.add(made);

    /* 🔴 **시연용 자동 수락** — 위 `kDemoAcceptAfter` 주석 참고. 실제
       배포에서는 이 블록을 걷는다. */
    Future<void>.delayed(kDemoAcceptAfter, () {
      final i = _requests.indexWhere((r) => r.id == made.id);
      if (i < 0 || !_requests[i].isPending) return;
      _requests[i] = TeamMatchRequest(
        id: made.id,
        requesterTeamId: made.requesterTeamId,
        targetTeamId: made.targetTeamId,
        status: 'accepted',
        playedAt: made.playedAt,
        place: made.place,
        // 🔴 수락되면 경기가 생긴다 — 이것이 차야 대기 화면을 띄운다.
        matchId: 'm-${made.id}',
        targetTeamName: made.targetTeamName,
        targetSquadSlug: made.targetSquadSlug,
      );
    });

    return made;
  }

  @override
  Future<List<TeamMatchRequest>> requests(String teamId) async {
    await Future<void>.delayed(_delay);
    return List.of(_requests.reversed);
  }

  /* 🔴 **서버 시드와 같은 값이다**(마이그레이션 `20260903_review_trust_tables`
     의 `_REVIEW_OPTIONS`). 문구를 지어내지 않으려고 그대로 옮겼다 — 진짜
     서버는 `GET /review-options` 가 준다.
     🔴 **순서가 곧 노출 순서다** — 「주의」가 맨 뒤인 것이 그 이유다. */
  static const _options = [
    ReviewOption(code: 'manner_time', category: 'manner', label: '시간을 잘 지켰다'),
    ReviewOption(code: 'manner_respect', category: 'manner', label: '매너가 좋았다'),
    ReviewOption(
        code: 'manner_communication', category: 'manner', label: '소통이 원활했다'),
    ReviewOption(
        code: 'skill_above_expected', category: 'skill', label: '실력이 기대 이상이었다'),
    ReviewOption(
        code: 'skill_position_fit', category: 'skill', label: '포지션 소화가 좋았다'),
    ReviewOption(code: 'skill_teamplay', category: 'skill', label: '팀플레이가 좋았다'),
    ReviewOption(code: 'repeat_yes', category: 'repeat', label: '다시 함께 뛰고 싶다'),
    ReviewOption(
        code: 'caution_position_mismatch',
        category: 'caution',
        label: '포지션이 안 맞았다'),
    ReviewOption(
        code: 'caution_would_not_repeat',
        category: 'caution',
        label: '다시 함께 뛰고 싶지 않다'),
  ];

  /// 이미 평가한 (경기, 상대) — 경기당 1회를 여기서도 막는다.
  final Set<String> _reviewed = {};

  @override
  Future<void> cancelRequest(String teamId, {required String requestId}) async {
    await Future<void>.delayed(_delay);

    final i = _requests.indexWhere((r) => r.id == requestId);
    if (i < 0) {
      throw const ApiException('없는 신청입니다',
          code: 'TEAM_MATCH_REQUEST_NOT_FOUND', status: 404);
    }
    // 🔴 `pending` 일 때만 무를 수 있다(계약) — 이미 잡힌 경기는 다른 길이다.
    if (!_requests[i].isPending) {
      throw const ApiException('이미 답이 온 신청입니다',
          code: 'TEAM_MATCH_REQUEST_ALREADY_RESPONDED', status: 409);
    }
    final was = _requests[i];
    _requests[i] = TeamMatchRequest(
      id: was.id,
      requesterTeamId: was.requesterTeamId,
      targetTeamId: was.targetTeamId,
      status: 'cancelled',
      playedAt: was.playedAt,
      place: was.place,
      targetTeamName: was.targetTeamName,
      targetSquadSlug: was.targetSquadSlug,
    );
  }

  @override
  Future<List<ReviewOption>> reviewOptions() async {
    await Future<void>.delayed(_delay);
    return List.of(_options);
  }

  @override
  Future<void> submitReview(
    String matchId, {
    required String revieweeId,
    required List<String> optionCodes,
  }) async {
    await Future<void>.delayed(_delay);

    if (optionCodes.isEmpty) {
      throw const ApiException('하나 이상 골라야 합니다',
          code: 'NO_OPTION_SELECTED', status: 422);
    }
    // 🔴 경기당 1회 — 서버는 DB 유일 제약으로 막는다.
    if (!_reviewed.add('$matchId/$revieweeId')) {
      throw const ApiException('이미 평가했습니다',
          code: 'ALREADY_REVIEWED', status: 409);
    }
  }
}
