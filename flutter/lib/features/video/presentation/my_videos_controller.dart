import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/clip_file.dart';
import '../data/models/my_video.dart';
import '../data/video_providers.dart';

/// 내 영상 목록의 **정본**.
///
/// 🔴 **웹에 있던 그림자 상태 넷이 여기서는 없다.** 웹은 목록이 서버 컴포넌트
/// prop 이라 다시 못 받아서 `added`·`removed`·`pubIds`·`featured` 를 화면이
/// 따로 기워 붙인다. 여기서는 이 컨트롤러가 목록을 쥐고 있으므로 **`PATCH`
/// 응답(= 바뀐 한 줄)으로 그 줄만 갈아 끼우면 된다.**
///
/// 🔴 **서버가 바꾼 뒤에 화면을 바꾼다.** 먼저 바꾸고 나중에 부르면 실패했을
/// 때 「공개 안 됨」으로 보이는데 **남에게는 계속 보인다** — 되돌릴 수 없는
/// 쪽으로 틀리는 것이라 지우기·대표 세우기도 같은 순서다. 그래서 이 파일에는
/// 낙관적 갱신이 **하나도 없다.**
class MyVideosController extends AsyncNotifier<List<MyVideo>> {
  @override
  Future<List<MyVideo>> build() =>
      ref.watch(videoRepositoryProvider).myVideos();

  /// 클립을 올린다. **올라간 줄을 그대로 돌려준다** — 부르는 쪽이 반려 사유와
  /// 중복 안내를 그 자리에서 띄워야 하기 때문이다.
  ///
  /// 🔴 **반려도 목록에 넣는다.** 등록은 성공했고 그 클립이 분석 대상이 아닐
  /// 뿐이다(계약 3-6절). 빼 버리면 반려 사유를 다시 볼 데가 없어진다.
  Future<MyVideo> upload({
    required ClipFile file,
    required ClipMeta meta,
    required String sportCode,
  }) async {
    final saved = await ref.read(videoRepositoryProvider).uploadClip(
          file: file,
          meta: meta,
          sportCode: sportCode,
        );
    // 최근 것이 앞이다 — 서버 목록과 같은 차례를 지킨다.
    state = AsyncData([saved, ...(state.value ?? const [])]);
    return saved;
  }

  /// 대표 영상을 세우거나 내린다.
  Future<void> setFeatured(String videoId, bool on) async {
    final row = await ref
        .read(videoRepositoryProvider)
        .patchVideo(videoId, isFeatured: on);

    /* 🔴 **다른 줄의 대표 표시도 내린다.** 규칙을 흉내 내는 것이 아니라
       **서버가 이미 한 일을 반영하는 것**이다 — 사람당 하나라 세우는 순간
       옛 대표가 내려가는데, 응답에는 **바뀐 한 줄만** 온다. 안 내리면 목록을
       다시 받기 전까지 화면에 대표가 둘로 보인다. */
    state = AsyncData([
      for (final v in state.value ?? const <MyVideo>[])
        if (v.id == videoId)
          row
        else if (on && v.isFeatured)
          v.copyWith(isFeatured: false)
        else
          v,
    ]);
  }

  /// 공개로 돌린다 — **제목과 함께 한 번에 보낸다.**
  ///
  /// 🔴 나눠 보내면 그 사이에 끊겼을 때 **이름 없는 영상이 남에게 보인다.**
  Future<void> publish(
    String videoId, {
    required String title,
    required String description,
  }) async {
    final row = await ref.read(videoRepositoryProvider).patchVideo(
          videoId,
          isPublic: true,
          title: title,
          description: description,
        );
    _replace(row);
  }

  Future<void> unpublish(String videoId) async {
    final row = await ref
        .read(videoRepositoryProvider)
        .patchVideo(videoId, isPublic: false);
    _replace(row);
  }

  /// 지운다 — 저장소의 영상과 그 분석 리포트까지. **되돌릴 수 없다.**
  ///
  /// 🔴 공개·대표를 따로 거둘 것이 없다 — 둘 다 클립의 성질이라 클립이
  /// 사라지면서 같이 없어진다. 여기서 `patchVideo` 를 부르면 **방금 지운
  /// 영상에 PATCH 를 쏘게 되고** 404 다.
  Future<void> remove(String videoId) async {
    await ref.read(videoRepositoryProvider).deleteVideo(videoId);
    state = AsyncData([
      for (final v in state.value ?? const <MyVideo>[])
        if (v.id != videoId) v,
    ]);
  }

  void _replace(MyVideo row) {
    state = AsyncData([
      for (final v in state.value ?? const <MyVideo>[])
        if (v.id == row.id) row else v,
    ]);
  }
}

final myVideosProvider =
    AsyncNotifierProvider<MyVideosController, List<MyVideo>>(
  MyVideosController.new,
);

/// 갈래로 가른 목록 — 🔴 **기준은 `analysis_job_id` 다**(`MyVideo.analyzed`).
///
/// `analysis_status` 로 가르면 **분석을 걸었지만 아직 대기 중인 클립이
/// 「그냥 올린 것」 쪽으로 새어 나간다.**
({List<MyVideo> analyzed, List<MyVideo> uploaded}) splitVideos(
  List<MyVideo> all,
) =>
    (
      analyzed: [
        for (final v in all)
          if (v.analyzed) v,
      ],
      uploaded: [
        for (final v in all)
          if (!v.analyzed) v,
      ],
    );
