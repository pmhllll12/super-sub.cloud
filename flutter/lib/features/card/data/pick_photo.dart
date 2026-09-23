import 'dart:io';

import 'package:image_picker/image_picker.dart';

import '../../../core/network/upload_file.dart';

/// 카드 사진을 앨범·카메라에서 고른다.
///
/// 🔴 **`dart:io` 와 플러그인에 닿는 유일한 자리다** — 리포지토리는
/// [UploadFile] 만 받으므로 그쪽 시험이 임시 파일을 안 만들어도 된다
/// (`features/video/data/pick_clip.dart` 와 같은 구조).
class PhotoPicker {
  PhotoPicker({ImagePicker? picker}) : _picker = picker ?? ImagePicker();

  final ImagePicker _picker;

  Future<PickedPhoto?> fromGallery() => _pick(ImageSource.gallery);

  Future<PickedPhoto?> fromCamera() => _pick(ImageSource.camera);

  Future<PickedPhoto?> _pick(ImageSource source) async {
    /* 🔴 **올리기 전에 줄인다.** 카드는 380px 폭인데 폰 사진은 3~5MB 다.
       안 줄이면 올리는 데 오래 걸리고, **남이 그 카드를 열 때마다 그 원본을
       내려받는다**(스쿼드 판 하나가 자리마다 카드를 부른다).
       [kPhotoMaxEdge] 는 카드 기본 폭의 두 배 — 고해상도 화면 몫이다.

       🔴 **`imageQuality` 를 주지 않는다.** 그것은 JPEG 재인코딩을 걸어
       **투명한 자리를 검게 칠한다** — 「사람만 오려서」 갈래는 배경 없는
       PNG 가 요점이라 그러면 카드가 망가진다(웹이 같은 함정을 주석에 남겼다).
       크기만 줄이면 형식은 그대로다. */
    final picked = await _picker.pickImage(
      source: source,
      maxWidth: kPhotoMaxEdge,
      maxHeight: kPhotoMaxEdge,
    );
    if (picked == null) return null; // 고르다 말았다 — 오류가 아니다.

    final file = File(picked.path);
    final length = await file.length();
    return PickedPhoto(
      path: picked.path,
      file: UploadFile(
        name: picked.name,
        contentType: photoTypeOf(picked.name),
        sizeBytes: length,
        // 🔴 부를 때마다 새로 연다 — 재시도할 때 빈 몸통을 보내지 않으려면.
        openRead: file.openRead,
      ),
    );
  }
}

/// 긴 변을 이 길이로 맞춘다. 카드 기본 폭(380)의 두 배.
const double kPhotoMaxEdge = 768;

class PickedPhoto {
  const PickedPhoto({required this.file, required this.path});

  final UploadFile file;

  /// 올라가기 전에 카드에 **바로 보여 줄** 로컬 경로.
  final String path;
}

/// 파일 이름 → 계약이 받는 사진 형식.
///
/// 🔴 **모르는 확장자를 `image/jpeg` 로 지어내지 않는다.** 폰 앨범은 HEIC 를
/// 내주는데, 지어내면 `checkCardPhoto` 가 통과시키고 **S3 서명까지 만들어진
/// 뒤 등록에서 422 로 죽는다.** 정직하게 두면 고른 즉시 막힌다.
///
/// 🔴 **`image/svg+xml` 로 매핑하지 않는다** — 계약이 일부러 안 받는다
/// (SVG 는 스크립트를 담는다).
String photoTypeOf(String name) {
  final dot = name.lastIndexOf('.');
  final ext = dot < 0 ? '' : name.substring(dot + 1).toLowerCase();
  return switch (ext) {
    'jpg' || 'jpeg' => 'image/jpeg',
    'png' => 'image/png',
    'webp' => 'image/webp',
    _ => 'application/octet-stream',
  };
}
