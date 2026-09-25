import '../../../core/network/api_client.dart';
import 'candidate_repository.dart';
import 'models/squad_candidate.dart';

/// 백엔드 없이 도는 후보 저장소.
///
/// 🔴 **서버가 막는 것을 여기서도 막는다**(없는 포지션 · 남의 팀). Mock 이 다
/// 받아 주면 목업으로 만든 화면이 진짜 서버에서 처음으로 422·403 을 만난다.
class MockCandidateRepository implements CandidateRepository {
  MockCandidateRepository();

  static const _delay = Duration(milliseconds: 300);

  /// 내가 속한 팀. 여기 없는 팀에 물으면 403 처럼 던진다.
  static const _myTeams = {'t-thunder'};

  /// 그 팀 종목(축구)의 포지션.
  static const _positions = {'FW', 'MF', 'DF', 'GK'};

  /* 🔴 **닉네임에 `(mock)` 을 붙인다** (2026-09-25 사용자 요청). 진짜 후보와
     섞이면 무엇을 보고 있는지 모른다 — 진짜 서버로 돌리면 이 저장소가 아예
     안 쓰여 표시도 같이 사라진다. */
  /// 🔴 **세 갈래를 일부러 섞어 둔다** — 등급이 있는 사람 · 검수 전 · 카드가
  /// 아예 없는 사람. 한 갈래만 두면 나머지 둘을 그리는 코드를 실서버에서
  /// 처음 만나게 된다. GK 는 **비워 둔다**(「후보 없음」 갈래).
  static const _seed = <String, List<SquadCandidate>>{
    'DF': [
      SquadCandidate(
        userId: 'u-kim',
        nickname: '끝까지뛰는 (mock)',
        cardPublicSlug: 'kim-abc1',
        grade: 'C',
        provisional: false,
        notes: ['첫 터치를 앞으로 길게 놓습니다'],
      ),
      SquadCandidate(
        userId: 'u-futsal',
        nickname: '풋살초보 (mock)',
        cardPublicSlug: 'futsal-7f21',
        grade: 'F',
        provisional: true,
        notes: ['공을 몸 가까이에 두려 합니다', '디딤발이 공에서 멉니다'],
      ),
      SquadCandidate(
        userId: 'u-line',
        nickname: '라인세우기 (mock)',
        cardPublicSlug: 'line-3a92',
        grade: 'A',
        provisional: false,
        notes: ['수비 라인을 먼저 올립니다'],
      ),
      // 🔴 카드도 등급도 없는 사람 — 목록에서 사라지지 않는다.
      SquadCandidate(userId: 'u-newbie', nickname: '오재현 (mock)'),
    ],
    'MF': [
      SquadCandidate(
        userId: 'u-pass',
        nickname: '한박자빠른패스 (mock)',
        cardPublicSlug: 'pass-1b44',
        grade: 'B',
        provisional: false,
        notes: ['앞을 먼저 보고 받습니다'],
      ),
      SquadCandidate(userId: 'u-quiet', nickname: '조용한중원 (mock)'),
    ],
    'FW': [
      SquadCandidate(
        userId: 'u-shot',
        nickname: '왼발만 (mock)',
        cardPublicSlug: 'shot-9c01',
        grade: 'A',
        provisional: true,
        notes: ['디딤발을 공 옆에 붙입니다'],
      ),
    ],
    'GK': [],
  };

  @override
  Future<List<SquadCandidate>> candidates(
    String teamId, {
    required String positionCode,
    String? grade,
  }) async {
    // Mock 이 즉시 성공하면 로딩 UI 를 안 만들게 된다(다른 Mock 과 같은 지연).
    await Future<void>.delayed(_delay);

    if (!_myTeams.contains(teamId)) {
      throw const ApiException('그 팀 소속이 아닙니다',
          code: 'FORBIDDEN', status: 403);
    }
    if (!_positions.contains(positionCode)) {
      throw const ApiException('그 종목에 없는 포지션입니다',
          code: 'UNKNOWN_POSITION', status: 422);
    }

    final all = _seed[positionCode] ?? const <SquadCandidate>[];
    /* 🔴 **서버가 거른다**(하드 필터). Mock 도 같은 자리에서 걸러야 화면이
       「받아서 거르면 안 된다」를 지키고 있는지가 드러난다. */
    if (grade == null) return List.of(all);
    return all.where((c) => c.grade == grade).toList();
  }

  /// 🔴 **일부러 한 명만 대표 영상을 둔다** — 「없음」 갈래(자리표시자)를
  /// 반드시 밟게 하는 장치다.
  static const _featured = {'kim-abc1': 'v-kim-1', 'futsal-7f21': 'v-futsal-1'};

  @override
  Future<String?> featuredVideoId(String cardPublicSlug) async {
    await Future<void>.delayed(_delay);
    return _featured[cardPublicSlug];
  }
}
