import 'models/squad_candidate.dart';

/// 빈 자리를 채울 후보를 찾는다 — 계약 3-14절
/// `GET /teams/{id}/squad/candidates`.
///
/// 🔴 **후보는 팀 밖에서 찾는다.** 지금 팀원과 이미 판에 앉은 사람은 서버가
/// 뺀다 — 데려올 이유가 없기 때문이다. `teamId` 는 **보는 권한**을 가리는
/// 값이지 후보 범위가 아니다(계약이 한 번 잘못 읽힌 자리라 못 박아 뒀다).
abstract class CandidateRepository {
  /// [positionCode] 자리의 후보를 **서버가 정렬한 순서 그대로** 돌려준다.
  ///
  /// [grade] 를 주면 `S`~`F` 중 그 칸으로 **서버가 하드 필터**한다. 안 주면
  /// 거르지 않고 정렬만 한다 — 등급을 모르는 사람도 뒤에 남는다.
  ///
  /// 🔴 **받아서 거르지 않는다.** 머리말의 「N명」이 곧 이 목록의 길이여야
  /// 하는데, 화면에서 한 번 더 거르면 그 수가 안 맞는다.
  ///
  /// 조건에 맞는 사람이 없으면 **빈 목록**이다(예외가 아니다).
  Future<List<SquadCandidate>> candidates(
    String teamId, {
    required String positionCode,
    String? grade,
  });

  /// 그 카드 주인의 **대표 영상** id — `GET /cards/{slug}/featured-video`.
  /// 후보 옆에 도는 장면이 이것이다(계약이 그렇게 적어 뒀다).
  ///
  /// 🔴 **없으면 `null`** 이다(404 가 정상). 예외로 올리면 줄 하나 때문에
  /// 시트 전체가 오류 화면이 된다.
  ///
  /// 🔴 **id 만 받는다** — 사전 서명 URL 은 15분이면 만료되는데, 썸네일은 앱에
  /// 이미 있는 포스터 경로(`videoPosterProvider`)가 더 잘 다룬다. 거기엔
  /// 2026-09-25에 붙인 **재시도 세 번**이 있다.
  Future<String?> featuredVideoId(String cardPublicSlug);
}
