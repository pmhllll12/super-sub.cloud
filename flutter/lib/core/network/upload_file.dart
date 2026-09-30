/// 올릴 것 하나 — **파일이 아니라 「읽을 수 있는 것」**이다.
///
/// 🔴 **`File` 을 받지 않는다.** 그러면 리포지토리와 그 시험이 `dart:io` 와
/// 실제 파일에 매이고, 계약 시험이 임시 파일을 만들어야 한다. 바이트를
/// 어디서 가져오는지는 **고르는 쪽**이 알면 되는 일이다.
///
/// 🔴 **`core/network/` 에 있는 이유**: 클립(`features/video/`)과 카드 사진
/// (`features/card/`)이 **같은 두 단계**(사전 서명 → S3 직접 PUT)를 쓴다.
/// 기능마다 제 것을 두면 두 벌이 되고, 아래 「부를 때마다 새 스트림」 같은
/// 함정을 한쪽에서만 빠뜨린다 — `presigned_upload.dart` 와 같은 판단이다.
class UploadFile {
  const UploadFile({
    required this.name,
    required this.contentType,
    required this.sizeBytes,
    required this.openRead,
  });

  /// 원본 파일 이름. 저장 키를 **사람이 알아볼 수 있게** 짓는 데 쓴다 —
  /// 서버가 슬러그화하므로 공백·문장부호·이모지가 들어와도 안전하다.
  ///
  /// ⚠️ 카드 사진 경로는 이 값을 **안 쓴다**(계약이 `content_type` 만 받고
  /// 확장자는 서버가 붙인다) — 그래도 자리를 비우지 않는 편이 낫다.
  final String name;

  /// 🔴 **사전 서명에 이 값이 들어간다** — S3 에 PUT 할 때 `Content-Type` 을
  /// 이것과 똑같이 보내야 하고, 다르면 서명이 안 맞아 **403** 이다.
  final String contentType;

  final int sizeBytes;

  /// 🔴 **부를 때마다 새 스트림을 준다.** 한 번 읽고 끝나는 스트림을 들고
  /// 있으면 재시도할 때 빈 몸통을 보낸다.
  final Stream<List<int>> Function() openRead;
}
