import 'models/squad.dart';

/// 화면이 아는 유일한 스쿼드 계약.
///
/// 🔴 **「안 만들었다」를 예외로 던지지 않는다** — 카드와 같은 판단이다
/// (`card_repository.dart`).
abstract class SquadRepository {
  /// 팀의 스쿼드. **아직 안 만들었으면 `null`** 이다.
  ///
  /// 🔴 빈 스쿼드를 돌려주면 「만들지 않은 것」과 「비어 있는 것」이 같아
  /// 보인다 — 계약이 404 `SQUAD_NOT_FOUND` 를 내는 이유가 그것이다.
  ///
  /// 읽기는 **소속이면 된다**(주장이 아니어도 된다). 팀 id 로 남의 팀 구성을
  /// 훑는 것을 막는 자리라, 소속이 아니면 404 가 아니라 403 이 온다.
  Future<Squad?> squadOf(String teamId);
}
