import '../../../core/network/api_client.dart';
import 'models/squad.dart';
import 'squad_repository.dart';

/// `fastapi/` 백엔드에 붙는 실제 구현. 계약은 `api-contract.md` 3-7절.
class ApiSquadRepository implements SquadRepository {
  ApiSquadRepository(this._api);

  final ApiClient _api;

  @override
  Future<Squad?> squadOf(String teamId) async {
    try {
      return Squad.fromJson(
        await _api.get('/teams/${Uri.encodeComponent(teamId)}/squad'),
      );
    } on ApiException catch (e) {
      // 🔴 **404 만** null 로 바꾼다. 403 까지 삼키면 「소속이 아니라 못 본다」와
      //    「아직 안 만들었다」가 같아 보여, 판을 만들라고 권하게 된다.
      if (e.status == 404) return null;
      rethrow;
    }
  }

  @override
  Future<Squad?> squadBySlug(String publicSlug) async {
    try {
      return Squad.fromJson(
        await _api.get('/squads/${Uri.encodeComponent(publicSlug)}'),
      );
    } on ApiException catch (e) {
      // 🔴 404 만 null 로 — 아직 스쿼드를 안 만든 팀이 정상 상태다.
      if (e.status == 404) return null;
      rethrow;
    }
  }

  @override
  Future<Squad> enlist(
    String teamId, {
    required String playerCardId,
    required String positionCode,
    int? gridCol,
    int? gridRow,
  }) async =>
      Squad.fromJson(
        await _api.post('/teams/${Uri.encodeComponent(teamId)}/squad/members', {
          'player_card_id': playerCardId,
          'position_code': positionCode,
          // 🔴 함께 주거나 함께 비운다 — 한쪽만 주면 422 다. 그래서 둘 다
          //    늘 싣고, 없을 때는 둘 다 null 로 간다.
          'grid_col': gridCol,
          'grid_row': gridRow,
        }),
      );

  @override
  Future<Squad> moveSeat(
    String teamId, {
    required String memberId,
    required String positionCode,
    int? gridCol,
    int? gridRow,
  }) async =>
      Squad.fromJson(
        await _api.patch(
          '/teams/${Uri.encodeComponent(teamId)}/squad/members/'
          '${Uri.encodeComponent(memberId)}',
          {
            'position_code': positionCode,
            'grid_col': gridCol,
            'grid_row': gridRow,
          },
        ),
      );

  @override
  Future<Squad> removeSeat(String teamId, {required String memberId}) async =>
      Squad.fromJson(
        await _api.deleteReturning(
          '/teams/${Uri.encodeComponent(teamId)}/squad/members/'
          '${Uri.encodeComponent(memberId)}',
        ),
      );

  @override
  Future<void> removeTeamMember(String teamId, {required String userId}) =>
      _api.delete(
        '/teams/${Uri.encodeComponent(teamId)}/members/'
        '${Uri.encodeComponent(userId)}',
      );
}
