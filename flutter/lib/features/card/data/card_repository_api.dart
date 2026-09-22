import '../../../core/network/api_client.dart';
import '../../../core/network/presigned_upload.dart';
import '../../../core/network/upload_file.dart';
import 'card_repository.dart';
import 'models/player_card.dart';

/// `fastapi/` 백엔드에 붙는 실제 구현. 계약은 `fastapi/docs/api-contract.md` 3절.
class ApiCardRepository implements CardRepository {
  ApiCardRepository(this._api, {PresignedUpload? upload})
      : _upload = upload ?? PresignedUpload();

  final ApiClient _api;

  /// 🔴 **저장소 PUT 은 `ApiClient` 를 안 지난다** — 토큰을 실으면 서명이
  /// 깨지고 응답이 JSON 이 아니다. 클립 업로드와 같은 것을 쓴다.
  final PresignedUpload _upload;

  @override
  Future<PlayerCard?> myCard() => _orNullOn404(() => _api.get('/me/card'));

  @override
  Future<PlayerCard> createMyCard() async =>
      // 본문이 없다. 이미 있으면 200 으로 있는 카드가 그대로 온다 — 응답 본문이
      // `GET /me/card` 와 완전히 같아서 파서가 하나면 된다.
      PlayerCard.fromJson(await _api.post('/me/card'));

  @override
  Future<PlayerCard?> cardBySlug(String slug) => _orNullOn404(
        // 🔴 **인증하지 않는다** — 계약이 인증 없이 열어 둔 공개 경로다.
        //    토큰을 실으면 안 되는 것이 아니라, 실을 이유가 없다.
        () => _api.get('/cards/${Uri.encodeComponent(slug)}', authorized: false),
      );

  @override
  Future<PlayerCard> updateCard({
    String? tagline,
    bool clearTagline = false,
    CardStyle? style,
  }) async {
    /* 🔴 **보낸 것만 바뀐다**(계약: `model_fields_set` 로 본다). 그래서
       「안 보냄」과 「null 을 보냄」이 **다른 뜻**이다 — 후자는 「지워라」다.
       [clearTagline] 이 그 둘을 가른다. */
    final body = <String, dynamic>{
      if (clearTagline) 'tagline': null else 'tagline': ?tagline,
      'style': ?style?.toWire(),
    };
    return PlayerCard.fromJson(await _api.patch('/me/card', body));
  }

  @override
  Future<String> uploadCardPhoto(UploadFile file) async {
    // (1) 올릴 자리를 받는다.
    /* 🔴 **`content_type` 만 보낸다** — 확장자는 서버가 붙인다. 클라이언트가
       정하면 「image/jpeg 라면서 .html 로 올리는 키」가 생긴다(계약). */
    final spot = await _api.post('/me/card/photo-upload-url', {
      'content_type': file.contentType,
    });

    // (2) S3 에 직접. 바이트가 앱 서버를 안 지난다(PER-002).
    await _upload.put(
      url: Uri.parse(spot['upload_url'] as String),
      openRead: file.openRead,
      contentLength: file.sizeBytes,
      // 🔴 요청한 값 그대로 — 서명에 들어 있어 다르면 S3 가 403 이다.
      contentType: file.contentType,
    );

    /* (3) 은 부르는 쪽이 한다 — `updateCard(style: …photoKey)`.
       🔴 여기서 몰래 PATCH 하면 아직 저장 안 한 색·글자 변경과 순서가 엉킨다. */
    return spot['storage_key'] as String;
  }

  /// 🔴 **404 만** `null` 로 바꾼다.
  ///
  /// 401·500 까지 삼키면 「로그인이 풀렸다」와 「카드가 없다」가 같아 보여,
  /// 화면이 빈 카드를 그리며 조용히 잘못된 상태에 머문다 — 사람은 왜 자기
  /// 카드가 사라졌는지 알 길이 없다.
  Future<PlayerCard?> _orNullOn404(
    Future<Map<String, dynamic>> Function() request,
  ) async {
    try {
      return PlayerCard.fromJson(await request());
    } on ApiException catch (e) {
      if (e.status == 404) return null;
      rethrow;
    }
  }
}
