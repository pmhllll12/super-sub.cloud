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
}
