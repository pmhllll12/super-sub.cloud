import 'models/sport.dart';

/// 화면이 아는 유일한 종목 조회 계약.
///
/// 종목 목록은 지금 MockDb의 상수 2행이지만 서버가 소유하는 데이터다
/// (ERD `sport`). 동기 게터로 노출하면 API가 붙는 날 목록을 쓰는 화면을
/// 전부 다시 짜게 되므로 처음부터 Future로 둔다(스펙 4.1 규칙 2).
abstract class SportRepository {
  Future<List<Sport>> sports();
}
