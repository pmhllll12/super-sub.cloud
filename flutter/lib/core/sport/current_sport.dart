import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 종목 전역 컨텍스트.
///
/// ERD에서 metric_definition·title_definition·position이 모두 sport_code에
/// 매달려 있다. 즉 지표도 호칭도 포지션도 종목마다 다르다. 나중에 끼워넣으면
/// 거의 모든 화면을 고치게 되므로 처음부터 전역으로 둔다.
///
/// 주의: ERD의 user 테이블에는 선호 종목 컬럼이 없다. 지금은 앱 메모리에만
/// 두고, 영구 저장은 미결 항목이다.
class CurrentSport extends Notifier<String?> {
  @override
  String? build() => null;

  void select(String sportCode) => state = sportCode;

  void clear() => state = null;
}

final currentSportProvider =
    NotifierProvider<CurrentSport, String?>(CurrentSport.new);
