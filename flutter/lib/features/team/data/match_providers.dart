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

/// 지역 목록(id + 이름). 참조 데이터라 한 번 받으면 그대로 쓴다.
final matchRegionsProvider = FutureProvider<List<RefItem>>(
  (ref) => ref.watch(matchRepositoryProvider).regions(),
  retry: (_, _) => null,
);
