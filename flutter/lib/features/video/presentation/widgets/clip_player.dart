import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:video_player/video_player.dart';

import '../../data/video_providers.dart';

/// 한 편을 트는 자리.
///
/// 🔴 **키가 고정된 자리다**(웹이 사용자 요청으로 그렇게 갔다: "세로영상이든
/// 가로영상이든 단추 위치가 안 바뀌게"). 영상은 자기 비 그대로 이 안에서
/// 가운데 서고 남는 자리는 비워 둔다 — 자리를 영상 키에 맡기면 세로 영상에서
/// 아래 것들이 통째로 내려간다. **영상을 늘리거나 자르지 않는다.**
///
/// 🔴 **재생 주소가 없어도 이 자리는 그대로 둔다.** 저장소가 안 붙은 배포에서
/// 그렇다 — 비면 판이 접혀서 무엇이 잘못됐는지보다 **화면이 깨진 것처럼**
/// 보인다.
class ClipPlayer extends ConsumerStatefulWidget {
  const ClipPlayer({super.key, required this.videoId});

  final String videoId;

  /// 16:9 기준으로 잡은 고정 높이.
  static const double height = 200;

  @override
  ConsumerState<ClipPlayer> createState() => _ClipPlayerState();
}

class _ClipPlayerState extends ConsumerState<ClipPlayer> {
  VideoPlayerController? _controller;

  /// 지금 컨트롤러가 물고 있는 주소 — 같은 주소로 두 번 만들지 않는다.
  String? _for;

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  /// 🔴 **넘길 때마다 옛 컨트롤러를 버린다.** 안 버리면 넘긴 만큼 디코더가
  /// 쌓이고, 안드로이드는 동시 디코더가 몇 개 안 돼서 **몇 편 넘기면 그
  /// 다음부터 아무것도 안 열린다.**
  Future<void> _open(String url) async {
    if (_for == url) return;
    _for = url;
    final old = _controller;
    final next = VideoPlayerController.networkUrl(Uri.parse(url));
    _controller = next;
    try {
      await next.initialize();
    } catch (_) {
      // 못 열면 빈 자리로 둔다 — 아래 나머지는 그대로 그려야 한다.
    }
    await old?.dispose();
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final asyncUrl = ref.watch(playbackUrlProvider(widget.videoId));
    final url = asyncUrl.value;
    if (url != null) {
      // 그리는 도중에 상태를 바꾸지 않는다 — 한 프레임 뒤로 미룬다.
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _open(url);
      });
    }

    final c = _controller;
    final ready = c != null && c.value.isInitialized;

    return Container(
      height: ClipPlayer.height,
      decoration: BoxDecoration(
        color: Colors.black,
        borderRadius: BorderRadius.circular(12),
      ),
      clipBehavior: Clip.antiAlias,
      child: Center(
        child: switch (true) {
          _ when ready => AspectRatio(
              aspectRatio: c.value.aspectRatio,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  VideoPlayer(c),
                  // 🔴 막대를 늘 켜 두면 멈춰 있는 동안 영상 아래를 덮은 채로
                  //    남는다. 눌러서 틀고 멈춘다.
                  _PlayToggle(controller: c),
                ],
              ),
            ),
          _ when asyncUrl.isLoading =>
            const CircularProgressIndicator(strokeWidth: 2),
          _ => Text(
              '이 영상은 지금 재생할 수 없습니다.',
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.6),
                fontSize: 13,
              ),
            ),
        },
      ),
    );
  }
}

class _PlayToggle extends StatefulWidget {
  const _PlayToggle({required this.controller});

  final VideoPlayerController controller;

  @override
  State<_PlayToggle> createState() => _PlayToggleState();
}

class _PlayToggleState extends State<_PlayToggle> {
  @override
  Widget build(BuildContext context) {
    final playing = widget.controller.value.isPlaying;
    return GestureDetector(
      key: const Key('clip-play'),
      behavior: HitTestBehavior.opaque,
      onTap: () async {
        if (playing) {
          await widget.controller.pause();
        } else {
          await widget.controller.play();
        }
        if (mounted) setState(() {});
      },
      child: AnimatedOpacity(
        opacity: playing ? 0 : 1,
        duration: const Duration(milliseconds: 180),
        child: Container(
          width: 52,
          height: 52,
          decoration: BoxDecoration(
            color: Colors.black.withValues(alpha: 0.45),
            shape: BoxShape.circle,
          ),
          child: const Icon(Icons.play_arrow, color: Colors.white, size: 30),
        ),
      ),
    );
  }
}
