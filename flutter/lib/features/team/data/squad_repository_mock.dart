import '../../../core/mock/mock_db.dart';
import 'models/squad.dart';
import 'squad_repository.dart';

/// 백엔드 없이 도는 스쿼드 저장소.
///
/// 🔴 **`t-bears` 에는 스쿼드를 안 둔다**(`MockDb` 시드) — 「아직 안 만든 팀」
/// 갈래를 반드시 밟게 하는 장치다.
class MockSquadRepository implements SquadRepository {
  MockSquadRepository(this._db);

  final MockDb _db;

  static const _delay = Duration(milliseconds: 300);

  @override
  Future<Squad?> squadOf(String teamId) async {
    // Mock 이 즉시 성공하면 로딩 UI 를 안 만들게 된다(다른 Mock 과 같은 지연).
    await Future<void>.delayed(_delay);
    for (final s in _db.squads) {
      if (s.teamId == teamId) return s;
    }
    return null;
  }
}
