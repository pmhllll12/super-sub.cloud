import '../../../core/network/upload_file.dart';

export '../../../core/network/upload_file.dart' show UploadFile;

/// 올릴 클립 하나.
///
/// 🔴 **카드 사진과 같은 것을 쓴다**(`core/network/upload_file.dart`) —
/// 두 기능이 같은 두 단계(사전 서명 → S3 직접 PUT)를 밟으므로 값 객체를
/// 두 벌로 두면 함정을 한쪽에서만 빠뜨린다. 이름만 이 기능의 말로 둔다.
typedef ClipFile = UploadFile;

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
