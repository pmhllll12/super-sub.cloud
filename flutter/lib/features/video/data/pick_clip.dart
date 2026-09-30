import 'dart:io';

import 'package:image_picker/image_picker.dart';
import 'package:video_player/video_player.dart';

import 'clip_file.dart';

/// 앨범·카메라에서 클립을 고르고 **크기를 잰다.**
///
/// 🔴 **여기가 `dart:io` 와 플러그인에 닿는 유일한 자리다.** 리포지토리는
/// [ClipFile] 만 받으므로 그쪽 시험이 임시 파일을 안 만들어도 된다.
///
/// 🔴 **재는 것은 계약이 요구하는 것이다** — 서버가 다시 재려면 원본을
/// 내려받아야 하고 그러면 PER-002 가 무너진다(계약 3-6절).
class ClipPicker {
  ClipPicker({ImagePicker? picker}) : _picker = picker ?? ImagePicker();

  final ImagePicker _picker;

  Future<PickedClip?> fromGallery() => _pick(ImageSource.gallery);

  Future<PickedClip?> fromCamera() => _pick(ImageSource.camera);

  Future<PickedClip?> _pick(ImageSource source) async {
    /* 🔴 **길이를 여기서 자르지 않는다**(`maxDuration`). 상한을 넘는 클립은
       서버가 **반려 사유로 남겨야 하는 것**이라(SFR-001), 고르는 자리에서
       말없이 잘라 보내면 사람은 왜 자기 영상이 짧아졌는지 모른다. */
    final picked = await _picker.pickVideo(source: source);
    if (picked == null) return null; // 고르다 말았다 — 오류가 아니다.
    return measureClip(File(picked.path), name: picked.name);
  }
}

/// 고른 것 하나 — 올릴 것([file])과 잰 것([meta]), 그리고 미리 볼 경로.
class PickedClip {
  const PickedClip({
    required this.file,
    required this.meta,
    required this.path,
  });

  final ClipFile file;
  final ClipMeta meta;

  /// 미리보기 플레이어가 쓸 로컬 경로.
  final String path;
}

/// 파일 하나를 재서 [PickedClip] 으로 만든다.
///
/// 🔴 **재고 나서 반드시 `dispose` 한다.** 안 하면 고를 때마다 디코더가
/// 쌓이고, 안드로이드는 동시 디코더가 몇 개 안 돼서 **몇 번 고르면 그다음
/// 부터 영상이 아예 안 열린다.**
Future<PickedClip> measureClip(File file, {required String name}) async {
  final controller = VideoPlayerController.file(file);
  int durationMs = 0;
  int width = 0;
  int height = 0;
  try {
    await controller.initialize();
    durationMs = controller.value.duration.inMilliseconds;
    width = controller.value.size.width.round();
    height = controller.value.size.height.round();
  } catch (_) {
    /* 🔴 **못 재도 던지지 않는다.** 0 을 보내면 서버가 규격 검사에서 반려
       사유를 남겨 주고, 그것이 사람에게 훨씬 쓸모 있는 답이다 — 여기서
       막으면 「올리기가 안 된다」만 남는다. */
  } finally {
    await controller.dispose();
  }

  final length = await file.length();
  return PickedClip(
    path: file.path,
    meta: ClipMeta(durationMs: durationMs, width: width, height: height),
    file: ClipFile(
      name: name,
      contentType: contentTypeOf(name),
      sizeBytes: length,
      // 🔴 **부를 때마다 새로 연다** — 한 번 읽고 끝나는 스트림을 들고 있으면
      //    재시도할 때 빈 몸통을 보낸다.
      openRead: file.openRead,
    ),
  );
}

/// 파일 이름 → 계약이 받는 형식.
///
/// 🔴 **모르는 확장자를 `video/mp4` 로 지어내지 않는다.** 그러면 `checkClip`
/// 이 통과시키고 S3 서명까지 만들어진 뒤 **등록에서 422 로 죽는다** — 사람은
/// 한참 올린 다음에 거절을 본다. 여기서 정직하게 두면 고른 즉시 막힌다.
String contentTypeOf(String name) {
  final dot = name.lastIndexOf('.');
  final ext = dot < 0 ? '' : name.substring(dot + 1).toLowerCase();
  return switch (ext) {
    'mp4' || 'm4v' => 'video/mp4',
    'mov' || 'qt' => 'video/quicktime',
    _ => 'application/octet-stream',
  };
}
