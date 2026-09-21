import 'models/player_card.dart';

/// 화면이 아는 유일한 카드 계약.
///
/// 🔴 **「없음」을 예외로 던지지 않는다.** `GET /me/card` 의 404
/// `CARD_NOT_FOUND` 는 오류가 아니라 「아직 안 만들었다」이고, 그것을 예외로
/// 올리면 화면마다 try/catch 로 정상 상태를 가려내야 한다 — 그러면 진짜 오류
/// (네트워크 끊김·401)와 구분이 사라져서, 로그인이 풀린 것을 「카드가 없네」로
/// 그리게 된다.
///
/// 구현체가 Mock 인지 API 인지 화면은 모른다. 교체는 `card_providers.dart`
/// 한 줄이다.
abstract class CardRepository {
  /// 내 카드. **아직 없으면 `null`** 이다 — 카드는 가입만으로 생기지 않는다.
  Future<PlayerCard?> myCard();

  /// 카드를 만든다. 🔴 **멱등** — 이미 있으면 있는 것을 그대로 돌려준다.
  Future<PlayerCard> createMyCard();

  /// 남의 카드를 공개 슬러그로. 없으면 `null`.
  ///
  /// 🔴 **인증하지 않는다** — 슬러그가 96비트 난수라 그 자체가 접근 통제다
  /// (SEC-005). 스쿼드에 앉은 팀원의 카드를 그릴 때 이 길로 간다.
  Future<PlayerCard?> cardBySlug(String slug);
}
