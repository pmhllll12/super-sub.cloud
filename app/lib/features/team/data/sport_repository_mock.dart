import '../../../core/mock/mock_db.dart';
import 'models/sport.dart';
import 'sport_repository.dart';

class MockSportRepository implements SportRepository {
  MockSportRepository(this._db);

  final MockDb _db;

  static const _delay = Duration(milliseconds: 300);

  @override
  Future<List<Sport>> sports() async {
    // Mock이 즉시 성공하면 로딩 UI를 만들지 않게 되고, API를 붙이는 날
    // 화면을 다시 짠다(스펙 4.3). 인증 Mock과 같은 지연을 쓴다.
    await Future<void>.delayed(_delay);
    return List.unmodifiable(_db.sports);
  }
}
