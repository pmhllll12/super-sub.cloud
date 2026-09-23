import 'package:http/http.dart' as http;

import 'api_client.dart';

/// 사전 서명 주소로 **저장소에 직접** 올린다.
///
/// 🔴 **`ApiClient` 에 넣지 않는다.** 그쪽은 「계약 모양 JSON + Authorization
/// + UTF-8 디코딩」 창구인데 S3 는 셋 다 아니다 — 토큰을 실으면 서명이 깨지고,
/// 응답이 JSON 이 아니라 `_decode` 가 통째로 헛돈다.
///
/// 🔴 **원본이 앱 서버를 지나지 않는다**(PER-002). 서버가 아는 것은 키와
/// 크기뿐이다.
///
/// 🔴 **카드 사진 올리기도 이걸 쓴다**(`POST /me/card/photo-upload-url`).
/// 그래서 `features/video/` 가 아니라 여기 있다 — 두 벌로 두면 아래 두 함정
/// 중 하나를 한쪽에서만 빠뜨린다.
class PresignedUpload {
  PresignedUpload({http.Client? client}) : _client = client ?? http.Client();

  final http.Client _client;

  /// [url] 에 [openRead] 의 바이트를 PUT 한다.
  ///
  /// 🔴 **바이트를 다 읽지 않는다.** 클립 상한이 200MB 라 `readAsBytes()` 로
  /// 받으면 그만큼이 통째로 램에 올라가고, 폰에서는 그대로 죽는다. 스트림으로
  /// 흘리고 길이만 미리 알려 준다.
  ///
  /// 🔴 **[contentType] 은 `upload-url` 에 보낸 값 그대로여야 한다** — 서명에
  /// 들어 있어서 다르면 S3 가 거절한다. 이 함수가 고쳐 주지 않는다.
  Future<void> put({
    required Uri url,
    required Stream<List<int>> Function() openRead,
    required int contentLength,
    required String contentType,
  }) async {
    final request = http.StreamedRequest('PUT', url)
      ..headers['Content-Type'] = contentType
      ..contentLength = contentLength;

    /* 🔴 **`send()` 를 기다리기 전에 흘려 넣는다.** `send()` 안에서 몸통
       스트림을 끝까지 읽으므로, 다 넣고 나서 부르려 하면 서로를 기다리며
       멈춘다. 그래서 `await` 하지 않고 걸어 둔다. */
    openRead().listen(
      request.sink.add,
      onError: request.sink.addError,
      onDone: request.sink.close,
      cancelOnError: true,
    );

    final http.StreamedResponse response;
    try {
      response = await _client.send(request);
    } on http.ClientException catch (e) {
      throw ApiException('영상을 올리지 못했습니다: ${e.message}');
    }
    // 몸통을 비운다 — 안 비우면 연결이 안 돌아간다.
    await response.stream.drain<void>();

    if (response.statusCode < 200 || response.statusCode >= 300) {
      /* 🔴 **S3 의 XML 오류 본문을 그대로 보여주지 않는다.** 사람이 읽을
         글이 아니고, 서명·키 같은 것이 섞여 나온다. 상태 코드만 남긴다. */
      throw ApiException(
        '영상을 올리지 못했습니다 (${response.statusCode}).',
        status: response.statusCode,
      );
    }
  }
}
