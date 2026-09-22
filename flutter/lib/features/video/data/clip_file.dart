/// 올릴 클립 하나 — **파일이 아니라 「읽을 수 있는 것」**이다.
///
/// 🔴 **`File` 을 받지 않는다.** 그러면 리포지토리와 그 시험이 `dart:io` 와
/// 실제 파일에 매이고, 계약 시험이 임시 파일을 만들어야 한다. 바이트를
/// 어디서 가져오는지는 **고르는 쪽**(`pick_clip.dart`)이 알면 되는 일이다.
class ClipFile {
  const ClipFile({
    required this.name,
    required this.contentType,
    required this.sizeBytes,
    required this.openRead,
  });

  /// 원본 파일 이름. 저장 키를 **사람이 알아볼 수 있게** 짓는 데 쓴다 —
  /// 서버가 슬러그화하므로 공백·문장부호·이모지가 들어와도 안전하다.
  final String name;

  /// `video/mp4` · `video/quicktime`.
  ///
  /// 🔴 **사전 서명에 이 값이 들어간다** — S3 에 PUT 할 때 `Content-Type` 을
  /// 이것과 똑같이 보내야 하고, 다르면 서명이 안 맞아 거절당한다.
  final String contentType;

  final int sizeBytes;

  /// 🔴 **부를 때마다 새 스트림을 준다.** 한 번 읽고 끝나는 스트림을 들고
  /// 있으면 재시도할 때 빈 몸통을 보낸다.
  final Stream<List<int>> Function() openRead;
}

/// 클라이언트가 잰 값. 서버가 다시 재려면 원본을 받아야 하고 그러면 PER-002
/// 가 무너진다 — 잰 값을 우리가 실어 보낸다(계약 3-6절).
class ClipMeta {
  const ClipMeta({
    required this.durationMs,
    required this.width,
    required this.height,
  });

  final int durationMs;
  final int width;
  final int height;
}

/// 계약 3-6절의 상한 중 **화면이 미리 볼 수 있는 것**.
const int kClipMaxBytes = 200 * 1024 * 1024;
const List<String> kClipTypes = ['video/mp4', 'video/quicktime'];

/// 올리기 전에 거른다 — 통과면 `null`, 아니면 사람이 읽을 사유.
///
/// 🔴 **형식과 용량만 본다.** 그 둘은 `upload-url` 이 422 로 튕겨 **아무 데도
/// 안 남으므로** 미리 막는 편이 낫다. 길이·해상도는 반대다 — 서버가
/// `reject_reason` 으로 **남겨야 하는** 것이고(SFR-001 이 규격 검사를 두는
/// 이유가 그것이다), 화면이 미리 막으면 **그 사유가 사라진다.**
String? checkClip(ClipFile file) {
  if (!kClipTypes.contains(file.contentType)) {
    return '받지 않는 형식입니다. mp4 또는 mov 로 올려 주세요.';
  }
  if (file.sizeBytes > kClipMaxBytes) {
    return '용량이 상한을 넘습니다 (상한 ${kClipMaxBytes ~/ 1024 ~/ 1024}MB).';
  }
  return null;
}
