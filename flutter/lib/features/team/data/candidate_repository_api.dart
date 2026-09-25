import '../../../core/network/api_client.dart';
import 'candidate_repository.dart';
import 'models/squad_candidate.dart';

/// `fastapi/` 백엔드에 붙는 실제 구현. 계약은 `api-contract.md` 3-14절.
class ApiCandidateRepository implements CandidateRepository {
  ApiCandidateRepository(this._api);

  final ApiClient _api;

  @override
  Future<List<SquadCandidate>> candidates(
    String teamId, {
    required String positionCode,
    String? grade,
  }) async {
    final q = {
      'position_code': positionCode,
      /* 🔴 「등급 상관없음」은 **칸을 빼서** 보낸다. `grade=any` 를 지어
         보내면 서버가 그 글자를 등급으로 읽어 0명이 된다 — 계약은 "안 주거나
         `any`" 를 허용하지만, 안 주는 쪽이 한 가지 해석뿐이라 그쪽을 쓴다. */
      'grade': ?grade,
    };

    final rows = await _api.getList(
      '/teams/${Uri.encodeComponent(teamId)}/squad/candidates'
      '?${Uri(queryParameters: q).query}',
    );

    // 🔴 순서를 건드리지 않는다 — 서버가 이미 정렬했다.
    return rows.map(SquadCandidate.fromJson).toList();
  }

  @override
  Future<String?> featuredVideoId(String cardPublicSlug) async {
    try {
      final body = await _api.get(
        '/cards/${Uri.encodeComponent(cardPublicSlug)}/featured-video',
      );
      return body['video_id'] as String?;
    } on ApiException catch (e) {
      // 🔴 **404 만** 삼킨다 — 「대표 영상을 안 세웠다」는 정상이다.
      if (e.status == 404) return null;
      rethrow;
    }
  }
}
