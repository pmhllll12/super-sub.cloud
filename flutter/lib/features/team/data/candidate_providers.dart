import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/dev/data_source.dart';
import '../../../core/network/api_client.dart';
import 'candidate_repository.dart';
import 'candidate_repository_api.dart';
import 'candidate_repository_mock.dart';
import 'contact_repository.dart';
import 'demo_candidate_repository.dart';
import 'contact_repository_api.dart';
import 'contact_repository_mock.dart';
import 'invitation_repository.dart';
import 'invitation_repository_api.dart';
import 'invitation_repository_mock.dart';
import 'models/contact.dart';
import 'models/squad_candidate.dart';

/// 🔴 **백엔드 교체 지점.** 빈 자리를 채우는 세 저장소를 한 파일에 둔다 —
/// 같은 시트가 셋을 함께 쓰므로 무효화 범위가 같다(`squad_providers.dart` 를
/// 따로 둔 것과 반대되는 이유다).
/// 🔴 **실서버 위에 가짜 후보 한 명을 얹는다**(2026-09-25 사용자 요청).
/// 실서버 추천은 조건에 맞는 사람이 **실제로 있어야** 나와서, 시험할 때 목록이
/// 비어 아무것도 못 눌러 보는 일이 잦다.
///
/// 🔴 **걷어낼 때는 이 `DemoCandidateRepository(...)` 감싸기 한 줄이다.**
/// 팀 쪽 `DemoMatchRepository` 와 같은 결이고, 걷는 시점도 같다.
final candidateRepositoryProvider = Provider<CandidateRepository>((ref) {
  if (ref.watch(useMockProvider)) return MockCandidateRepository();
  return DemoCandidateRepository(
    ApiCandidateRepository(ref.watch(apiClientProvider)),
  );
});

final contactRepositoryProvider = Provider<ContactRepository>((ref) {
  if (ref.watch(useMockProvider)) return MockContactRepository();
  return ApiContactRepository(ref.watch(apiClientProvider));
});

final invitationRepositoryProvider = Provider<InvitationRepository>((ref) {
  if (ref.watch(useMockProvider)) return MockInvitationRepository();
  // 🔴 가짜 후보를 **부르는 것**만 가로챈다 — 위 감싸기와 짝이다.
  return DemoInvitationRepository(
    ApiInvitationRepository(ref.watch(apiClientProvider)),
  );
});

/// 어느 팀의 어느 자리를, 어느 등급으로 찾는가.
///
/// 🔴 **등급이 열쇠에 들어간다** — 등급은 서버가 거르므로 필터를 바꾸면
/// **다시 물어야** 한다. 열쇠에서 빼면 첫 번째 결과가 계속 쓰인다.
class CandidateQuery {
  const CandidateQuery(this.teamId, this.positionCode, {this.grade});

  final String teamId;
  final String positionCode;
  final String? grade;

  @override
  bool operator ==(Object other) =>
      other is CandidateQuery &&
      other.teamId == teamId &&
      other.positionCode == positionCode &&
      other.grade == grade;

  @override
  int get hashCode => Object.hash(teamId, positionCode, grade);
}

/// 그 자리의 후보. retry 를 끈 이유는 `squadProvider` 와 같다 — 자동 재시도가
/// 돌면 화면이 오류 대신 로딩만 계속 보여 준다.
final candidatesProvider =
    FutureProvider.family<List<SquadCandidate>, CandidateQuery>(
  (ref, q) => ref.watch(candidateRepositoryProvider).candidates(
        q.teamId,
        positionCode: q.positionCode,
        grade: q.grade,
      ),
  retry: (_, _) => null,
);

/// 후보의 대표 영상 id — 썸네일을 물어볼 열쇠다.
///
/// 🔴 **보이는 줄만 부른다.** `ListView.builder` 가 늦게 만드는 줄에서
/// `watch` 하므로, 아홉 명이 있어도 화면에 뜬 만큼만 나간다. 실서버가 느린
/// 동안(아무 일 안 하는 404 가 4.6초) 아홉 발을 한꺼번에 쏘지 않으려는 것이다.
final candidateFeaturedVideoProvider = FutureProvider.family<String?, String>(
  (ref, slug) => ref.watch(candidateRepositoryProvider).featuredVideoId(slug),
  retry: (_, _) => null,
);

/// 수락된 지인 목록.
final contactsProvider = FutureProvider<List<Contact>>(
  (ref) => ref.watch(contactRepositoryProvider).contacts(),
  retry: (_, _) => null,
);

/// 나에게 온 대기중 지인 신청.
final contactRequestsProvider = FutureProvider<List<ContactRequest>>(
  (ref) => ref.watch(contactRepositoryProvider).requests(),
  retry: (_, _) => null,
);
