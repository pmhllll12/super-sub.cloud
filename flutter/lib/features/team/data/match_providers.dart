import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/dev/data_source.dart';
import '../../../core/network/api_client.dart';
import '../match_prefs.dart';
import '../match_prefs_server.dart';
import 'demo_match_repository.dart';
import 'match_repository.dart';
import 'match_repository_api.dart';
import 'match_repository_mock.dart';
import 'models/match_candidate.dart';
import 'models/open_match.dart';

/// 🔴 **백엔드 교체 지점.**
///
/// 🔴 **실서버 위에 가짜 상대 한 팀을 얹는다**(2026-09-25 사용자 요청:
/// 「우리 앱에 그냥 mock 팀 하나만 넣으면 안됨? mock 모드 말고」). 실서버
/// 에서는 상대 팀장이 **실제로** 수락해야 해서 혼자서는 흐름을 못 본다.
///
/// 🔴 **걷어낼 때는 이 `DemoMatchRepository(...)` 감싸기 한 줄이다.**
/// 실제 배포에서는 걷는다 — 자리 초대의 시연용 자동 수락과 같은 결이고,
/// 걷는 시점도 같다.
final matchRepositoryProvider = Provider<MatchRepository>((ref) {
  if (ref.watch(useMockProvider)) return MockMatchRepository();
  return DemoMatchRepository(ApiMatchRepository(ref.watch(apiClientProvider)));
});

/// 팀의 경기 조건. 🔴 **`null` 은 「아직 안 정했다」**이고, 그때 화면은 조건
/// 폼을 먼저 띄운다 — 빈 조건과 갈라야 한다.
final teamPrefsProvider = FutureProvider.family<MatchPrefs?, String>(
  (ref, teamId) => ref.watch(matchRepositoryProvider).teamPrefs(teamId),
  retry: (_, _) => null,
);

/// 「맞는 상대」 후보 — 서버가 정렬한 순서 그대로.
final matchCandidatesProvider =
    FutureProvider.family<List<MatchCandidate>, String>(
  (ref, teamId) => ref.watch(matchRepositoryProvider).candidates(teamId),
  retry: (_, _) => null,
);

/// 그 팀이 **지금 살아 있는** 신청들 — 상대별로 잠그는 데 쓴다.
///
/// 🔴 **거절·취소된 것은 안 센다**(계약과 같은 기준) — 안 그러면 한 번 붙은
/// 팀과 다시는 못 붙는다.
final liveRequestsProvider =
    FutureProvider.family<Map<String, TeamMatchRequest>, String>(
  (ref, teamId) async {
    final all = await ref.watch(matchRepositoryProvider).requests(teamId);
    return {
      for (final r in all)
        /* 🔴 **내가 건 것만 센다** (2026-09-25, 사용자: 「경기 취소 안되는
           팀들도 있어」). 계약의 `GET …/match-requests` 는 **보낸 것 + 받은
           것**을 함께 준다 — 안 가르면 받은 신청이 엉뚱한 팀을 잠그고, 그
           팀은 취소도 안 된다(취소는 **신청 팀 주장만** 할 수 있다). */
        if (r.requesterTeamId == teamId && (r.isPending || r.isAccepted))
          r.targetTeamId: r,
    };
  },
  retry: (_, _) => null,
);

/* 🔴 **「지금 잡혀 있는 경기」는 여기 없다.** 알림함(`inbox_providers.dart`)이
   같은 값을 들고 있고, **그 판단은 `isLiveConfirmed` 한 곳**이어야 한다 —
   두 곳에서 따로 하면 한쪽이 끈 것을 다른 쪽이 켠다(웹이 세 번 신고받은
   자리다). 한때 여기에도 뒀다가 걷었다. */

/// **내** 경기 조건. 🔴 **팀 조건과 저장소가 다르다**(계약 3-13절) —
/// 같은 사람이 팀장이면서 팀원일 수 있어 절대 안 섞는다.
final myPrefsProvider = FutureProvider<MatchPrefs?>(
  (ref) => ref.watch(matchRepositoryProvider).myPrefs(),
  retry: (_, _) => null,
);

/// 포지션 목록(약칭 + id). 「내 자리」 칸이 쓴다.
final matchPositionsProvider = FutureProvider<List<RefItem>>(
  (ref) => ref.watch(matchRepositoryProvider).positions('football'),
  retry: (_, _) => null,
);

/// 무엇으로 좁혀 보는가 — `null` 이면 전체다.
class OpenMatchQuery {
  const OpenMatchQuery({this.sportCode, this.region});

  final String? sportCode;
  final String? region;

  @override
  bool operator ==(Object other) =>
      other is OpenMatchQuery &&
      other.sportCode == sportCode &&
      other.region == region;

  @override
  int get hashCode => Object.hash(sportCode, region);
}

/// **사람을 찾는 경기들.**
///
/// 🔴 **거르는 것은 서버다** — 받아 놓고 화면에서 거르면 다음 쪽을 못
/// 가져온다(목록이 페이지로 온다). 그래서 조건이 열쇠에 들어간다.
final openMatchesProvider =
    FutureProvider.family<List<OpenMatch>, OpenMatchQuery>(
  (ref, q) => ref.watch(matchRepositoryProvider).openMatches(
        sportCode: q.sportCode,
        region: q.region,
      ),
  retry: (_, _) => null,
);

/// 지역 목록(id + 이름). 참조 데이터라 한 번 받으면 그대로 쓴다.
final matchRegionsProvider = FutureProvider<List<RefItem>>(
  (ref) => ref.watch(matchRepositoryProvider).regions(),
  retry: (_, _) => null,
);
