import '../../../core/network/upload_file.dart';
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

  /// 카드의 **한 줄과 꾸미기**를 바꾼다(`PATCH /me/card`).
  ///
  /// 🔴 **둘은 따로 바뀐다** — 보낸 것만 본다. `style` 만 보내면 `tagline` 은
  /// 그대로다(반대도 마찬가지).
  /// 🔴 **`style` 은 전체 값을 보낸다** — 계약이 부분 병합을 안 하고 거부한다.
  /// 🔴 한 줄은 **20자까지**이고, 넘기면 422 다 — **조용히 자르지 않는다**
  /// (쓴 것과 보이는 것이 달라지고, 알아차리는 시점은 공유한 뒤다).
  Future<PlayerCard> updateCard({
    String? tagline,
    bool clearTagline = false,
    CardStyle? style,
  });

  /// 카드 사진을 올린다 — **저장 키를 돌려준다**(계약 3-5절).
  ///
  /// ```
  /// (1) POST /me/card/photo-upload-url   올릴 자리를 받는다
  /// (2) PUT  <upload_url>                 S3 에 직접 (PER-002)
  /// (3) PATCH /me/card  style.photo_key   ← 부르는 쪽이 한다
  /// ```
  ///
  /// 🔴 **(3)은 여기서 안 한다.** 사진은 카드 꾸미기의 한 조각이고 저장은
  /// 편집기가 「저장」을 누를 때 **한 번에** 일어나야 한다 — 여기서 몰래
  /// `PATCH` 하면 아직 저장 안 한 다른 변경(색·글자)과 순서가 엉킨다.
  ///
  /// 🔴 그래서 **올리기만 하고 키를 안 저장하면 아무 일도 안 난다** — 그
  /// 파일은 아무도 안 가리키는 채로 남는다. 편집기가 그 사이를 말해 준다.
  ///
  /// 🔴 **카드가 먼저 있어야 한다** — 저장 키에 카드 id 가 들어가서,
  /// 없으면 `404 CARD_NOT_FOUND` 다.
  Future<String> uploadCardPhoto(UploadFile file);
}

/// 계약이 받는 사진 형식 — **셋뿐이다**(계약 3-5절).
///
/// 🔴 **`image/svg+xml` 은 일부러 없다** — SVG 는 스크립트를 담는다.
const List<String> kCardPhotoTypes = ['image/jpeg', 'image/png', 'image/webp'];

/// 고른 사진이 올릴 수 있는 것인가 — 통과면 `null`, 아니면 사람이 읽을 사유.
///
/// 🔴 **`image/*` 를 그대로 보내지 않는다.** 폰 앨범은 HEIC 도 내주는데 서버는
/// 셋만 받는다(`UNSUPPORTED_PHOTO_TYPE`) — 여기서 안 막으면 **고른 사진이
/// 올라가다 422 로 죽는다.**
String? checkCardPhoto(UploadFile file) {
  if (!kCardPhotoTypes.contains(file.contentType)) {
    return '받지 않는 형식입니다. JPG · PNG · WebP 로 올려 주세요.';
  }
  return null;
}
