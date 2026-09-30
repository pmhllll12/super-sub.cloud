import 'candidate_repository.dart';
import 'invitation_repository.dart';
import 'models/squad_candidate.dart';
import 'models/team_invitation.dart';

/// 가짜 후보의 사용자 id. 🔴 **서버에 없는 값**이다 — 이것이 붙은 것은
/// 무엇이든 서버로 내보내지 않는다.
const String kDemoCandidateId = 'demo-player-mock';

/// 가짜 후보의 카드 슬러그. 역시 서버에 없다.
const String kDemoCardSlug = 'demo-card-mock';

/// 실서버 위에 **가짜 후보 한 명만** 얹는다.
///
/// 🔴 **왜 있나** (2026-09-25 사용자: 「왜 AI 추천판에서 사람들 mock 하나도
/// 없음?」). 실서버의 추천 후보는 **그 조건에 맞는 사람이 실제로 있어야**
/// 나온다 — 시험할 때 목록이 비어 아무것도 못 눌러 보는 일이 잦다.
/// 팀 쪽의 `DemoMatchRepository` 와 **같은 결**이고, 걷는 시점도 같다.
///
/// 🔴 **가짜는 서버를 건드리지 않는다** — 부르는 것은 아래
/// [DemoInvitationRepository] 가 막는다.
class DemoCandidateRepository implements CandidateRepository {
  DemoCandidateRepository(this._inner);

  final CandidateRepository _inner;

  @override
  Future<List<SquadCandidate>> candidates(
    String teamId, {
    required String positionCode,
    String? grade,
  }) async {
    /* 🔴 **속 저장소를 그대로 부른다.** 가짜를 끼우느라 진짜 검색을
       망가뜨리면 안 된다 — 등급 필터도 그대로 서버로 간다.

       🔴 **서버가 죽어도 가짜는 남긴다** (2026-09-25, 실서버가 522 를 냈다 —
       Cloudflare 가 HTML 오류 쪽을 돌려줘 JSON 파싱까지 터졌다). 가짜는
       **시험하라고** 넣은 것인데 진짜와 함께 죽으면 **정작 서버가 불안정할
       때 못 쓴다** — 그때가 가장 필요한 때다. */
    List<SquadCandidate> real;
    try {
      real = await _inner.candidates(
        teamId,
        positionCode: positionCode,
        grade: grade,
      );
    } catch (_) {
      real = const [];
    }

    return [
      SquadCandidate(
        userId: kDemoCandidateId,
        // 🔴 진짜 후보와 나란히 서므로 한눈에 갈려야 한다.
        nickname: '시험용 선수 (mock)',
        cardPublicSlug: kDemoCardSlug,
        /* 등급을 고르면 **그 등급으로 선다** — 안 그러면 필터를 걸 때마다
           가짜가 사라져서, 정작 시험하려는 자리에서 못 쓴다. */
        grade: grade ?? 'B',
        provisional: true,
        notes: const ['흐름 시험용입니다 — 서버에 없는 사람입니다'],
      ),
      ...real,
    ];
  }

  @override
  Future<String?> featuredVideoId(String cardPublicSlug) async {
    // 🔴 서버에 없는 슬러그를 물으면 404 다 — 아예 안 묻는다.
    if (cardPublicSlug == kDemoCardSlug) return null;
    return _inner.featuredVideoId(cardPublicSlug);
  }
}

/// 가짜 후보를 **부르는 것**만 가로챈다.
///
/// 🔴 **서버로 나가면 안 되는 두 가지** — 서버에 없는 사용자 id 라 404 이고,
/// 설령 통과해도 **진짜 팀에 가짜가 등록된다.**
class DemoInvitationRepository implements InvitationRepository {
  DemoInvitationRepository(this._inner);

  final InvitationRepository _inner;

  int _seq = 0;

  @override
  Future<TeamInvitation> invite(
    String teamId, {
    required String userId,
    String? positionCode,
  }) async {
    if (userId != kDemoCandidateId) {
      return _inner.invite(teamId, userId: userId, positionCode: positionCode);
    }

    /* 🔴 **대기중으로 돌려준다.** 홈의 시연용 자동 수락(`_demoAccept`, 1.5초)이
       그다음을 잇는다 — 여기서 곧바로 `accepted` 로 주면 「수락 대기중」 배지가
       한 프레임도 안 보인다. */
    return TeamInvitation(
      id: 'demo-inv-${++_seq}',
      teamId: teamId,
      invitedUserId: userId,
      status: 'pending',
      positionCode: positionCode,
    );
  }

  /* 🔴 **받은 쪽은 흘려보낸다** — 가짜는 **부르는 쪽**만 가로챈다. 나에게
     온 초대는 진짜 서버 것이어야 웹과 이어진다. */
  @override
  Future<List<TeamInvitation>> myInvitations() => _inner.myInvitations();

  @override
  Future<void> acceptInvitation(String invitationId) =>
      _inner.acceptInvitation(invitationId);

  @override
  Future<void> rejectInvitation(String invitationId) =>
      _inner.rejectInvitation(invitationId);
}
