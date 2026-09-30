/// 위 칸이 **반으로 갈린다** — 왼쪽 선수, 오른쪽 나. 둘 다 뼈대를 겹쳐 그린다.
///
/// 🔴 **폰은 세로라 웹과 배치가 다르다.** 웹은 가로 화면이라 두 영상을 크게
/// 좌우로 놓지만, 여기서는 폭이 반으로 줄어 한 쪽이 200px 안팎이다. 그래도
/// 좌우로 둔 것은 **차는 순간을 동시에 보는 것**이 이 기능의 전부라서다
/// (2026-09-25 사용자 선택).
///
/// 🔴 **선수 영상은 에셋에서 온다** — 서버가 재생 주소를 안 준다
/// (`reference_player.dart` 머리말). 없는 선수면 그 칸은 **비워 둔다.**
///
/// 🔴 **이 화면이 지켜야 하는 것 셋** (2026-09-25 사용자가 세 번 되짚은 것):
///
/// 1. 열리면 **둘 다 처음부터 알아서 돈다**
/// 2. 세 순간 카드를 누르면 **둘 다 그 시점으로 가서 멈춘다**
/// 3. 한 번 더 누르면 **둘 다 거기서 이어 돈다**
library;

import 'dart:io';

import 'package:flutter/material.dart';
import 'package:video_player/video_player.dart';

import '../../data/models/skeleton.dart';
import '../../domain/motion/compare.dart';
import '../../domain/motion/motion.dart';
import 'compare_moments.dart';
import 'skeleton_overlay.dart';

class CompareStage extends StatelessWidget {
  const CompareStage({
    super.key,
    required this.comparison,
    required this.playerAsset,
    required this.userClipPath,
    required this.playerSkeleton,
    required this.userSkeleton,
    this.selected,
  });

  final Comparison comparison;

  /// 선수 영상 에셋 경로 — 🔴 **없을 수 있다**(우리가 안 들고 있는 선수).
  final String? playerAsset;

  /// 내 영상 — 기기에 있는 그 파일.
  final String userClipPath;

  final Skeleton playerSkeleton;
  final Skeleton userSkeleton;

  /// 고른 순간 — 있으면 두 영상이 **그 자리에 멈춰 선다.**
  final MomentKey? selected;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
          child: _Side(
            label: comparison.playerName,
            color: kPlayerColor,
            source: playerAsset == null ? null : _Source.asset(playerAsset!),
            skeleton: playerSkeleton,
            seekTo: selected == null ? null : comparison.playerAt(selected!),
            // 🔴 선수 쪽을 뒤집었으면 **영상도 함께** 뒤집는다 — 뼈대만 뒤집으면
            //    뼈대와 사람이 서로 반대를 본다.
            mirrored: comparison.mirrored,
          ),
        ),
        const SizedBox(width: 6),
        Expanded(
          child: _Side(
            label: '나',
            color: kUserColor,
            source: _Source.file(userClipPath),
            skeleton: userSkeleton,
            seekTo: selected == null ? null : comparison.userAt(selected!),
          ),
        ),
      ],
    );
  }
}

/// 재생할 것이 파일인지 에셋인지.
class _Source {
  const _Source._(this.path, this.isAsset);
  const _Source.file(String path) : this._(path, false);
  const _Source.asset(String path) : this._(path, true);
  final String path;
  final bool isAsset;
}

class _Side extends StatefulWidget {
  const _Side({
    required this.label,
    required this.color,
    required this.source,
    required this.skeleton,
    this.seekTo,
    this.mirrored = false,
  });

  final String label;
  final Color color;
  final _Source? source;
  final Skeleton skeleton;

  /// `null` 이면 **돈다**, 값이 있으면 그 자리로 가서 **멈춘다**.
  final Duration? seekTo;
  final bool mirrored;

  @override
  State<_Side> createState() => _SideState();
}

class _SideState extends State<_Side> {
  VideoPlayerController? _c;

  /// 못 연 까닭 — 🔴 **화면에 보여 준다.** `null` 이면 아직 여는 중이다.
  String? _failed;

  /// 되감는 동안 뼈대를 붙들어 둘 자리. `null` 이면 재생 위치를 그대로 따른다.
  ///
  /// 🔴 **왜 붙드나** (2026-09-25 사용자 지적: 「2 영상이 관절먼저 움직이고,
  /// 관절이 따라가는데 같이 움직이지 못하나?」). `seekTo` 를 걸면 **재생 위치
  /// 값이 즉시** 새 자리로 바뀌는데, 그 값을 보고 그리는 뼈대는 바로 뛰고
  /// **영상은 디코더가 새 그림을 낼 때까지 옛 장면**이다.
  ///
  /// ⛔ 뼈대에 지연을 줘서 맞추지 말 것 — 디코더 속도를 짐작하는 것이라
  /// 기기마다 어긋난다. **되감기가 끝날 때까지 옛 자리를 유지**하는 것이 맞다.
  Duration? _held;

  /* 🔴 **늦게 끝난 옛 명령이 새 명령을 덮는 것을 막는다** (2026-09-25).

     겪은 것: 카드를 한 번 더 눌러도 **영상이 안 돌았다.** 되감기(`seekTo`)는
     느려서, 첫 탭의 `pause() → seekTo()` 가 아직 안 끝난 사이에 두 번째 탭이
     `play()` 를 부르고, **그 뒤에** 첫 탭의 남은 `pause()` 가 실행됐다 —
     재생하자마자 다시 멈춘 것이다.

     표를 한 장씩 끊어 **마지막 표만** 재생기를 건드린다. */
  int _seq = 0;

  @override
  void initState() {
    super.initState();
    _open();
  }

  @override
  void didUpdateWidget(_Side old) {
    super.didUpdateWidget(old);
    if (widget.seekTo != old.seekTo) _drive(++_seq, widget.seekTo);
  }

  @override
  void dispose() {
    // 🔴 표를 무효로 만든다 — 날아오던 명령이 버려진 재생기를 건드리지 않게.
    _seq += 1;
    _c?.dispose();
    super.dispose();
  }

  Future<void> _open() async {
    final src = widget.source;
    if (src == null) return;
    final ticket = ++_seq;
    /* 🔴 **둘이 나란히 돌려면 오디오 포커스를 안 뺏어야 한다** (2026-09-25).

       겪은 것: 두 영상 중 **하나만 돌았다.** 어느 쪽이 이기는지는 그때그때
       달랐다. 재생 위치를 찍어 보니 진 쪽이 `playing=false` · 오류 없음 ·
       위치 68ms 고정 — **누군가 멈춰 세운 것**이고, 그게 우리 코드가 아니었다.

       안드로이드에서 두 번째 재생기가 뜨면 첫 번째가 오디오 포커스를 잃고
       ExoPlayer 가 **스스로 일시정지**한다. 둘 다 `setVolume(0)` 이어도
       **포커스는 잡는다** — 소리를 안 내는 것과 포커스를 안 잡는 것은 다르다.

       ⛔ `mixWithOthers` 를 지우지 말 것 — 지우면 한 쪽이 조용히 멈춘다.
       ⚠️ 디코더 문제로 **오해했었다**(코덱이 둘 다 잡혀 있어 그럴듯했다). */
    final options = VideoPlayerOptions(mixWithOthers: true);
    final next = src.isAsset
        ? VideoPlayerController.asset(src.path, videoPlayerOptions: options)
        : VideoPlayerController.file(
            File(src.path),
            videoPlayerOptions: options,
          );
    try {
      await next.initialize();
      await next.setLooping(true);
      // 🔴 두 영상이 나란히 도는 자리다 — **둘 다 소리 없음.**
      await next.setVolume(0);
    } catch (e) {
      /* 🔴 **삼키지 않는다** (2026-09-25 사용자 지적: 「왜 선수 영상은 알아서
         재생 안됨?」). 조용히 `return` 하면 **영영 도는 동그라미**만 남아서,
         「아직 여는 중」과 「못 열었다」가 화면에서 똑같아 보인다 — `.value` 가
         오류일 때도 `null` 이라 못 가렸던 것과 같은 함정이다. */
      debugPrint('🔎비교 영상 못 열었다 src=${src.path} asset=${src.isAsset}: $e');
      await next.dispose();
      if (mounted) setState(() => _failed = '$e');
      return;
    }
    if (!mounted || ticket != _seq) {
      await next.dispose();
      return;
    }
    setState(() => _c = next);

    /* 🔴 **처음부터 돈다** (2026-09-25 사용자 요청: 「둘 다 영상 알아서
       처음부터 재생되어야 하고」). 어디서 시작할지를 플랫폼에 맡기지 않고
       0 으로 맞춘 뒤 건다. */
    if (widget.seekTo == null) {
      try {
        await next.seekTo(Duration.zero);
      } catch (_) {
        /* 못 맞춰도 재생은 건다 — 시작 지점만 플랫폼에 맡겨질 뿐이다. */
      }
      if (ticket != _seq) return;
    }
    await _drive(ticket, widget.seekTo);
  }

  /// 재생기를 **한 장의 표로만** 움직인다.
  ///
  /// [to] 가 `null` 이면 지금 자리에서 **재생**, 값이 있으면 그 자리로 **가서
  /// 멈춤**. 🔴 매 `await` 뒤에 표를 다시 확인한다 — 그 사이 새 명령이 왔으면
  /// **손을 뗀다**(위 [_seq] 머리말의 그 버그).
  Future<void> _drive(int ticket, Duration? to) async {
    final c = _c;
    if (c == null || !c.value.isInitialized) return;

    if (to == null) {
      // 붙들어 둔 뼈대를 놓는다 — 안 놓으면 옛 자세로 얼어 있다.
      if (mounted && _held != null) setState(() => _held = null);
      await c.play();
      return;
    }

    // 되감는 동안 뼈대는 **지금 보이는 그 프레임**에 붙들어 둔다.
    if (mounted) setState(() => _held = c.value.position);
    await c.pause();
    if (ticket != _seq) return;
    await c.seekTo(to);
    if (ticket != _seq || !mounted) return;
    // 새 그림이 나왔다 — 이제 뼈대도 함께 옮긴다.
    setState(() => _held = null);
  }

  @override
  Widget build(BuildContext context) {
    final c = _c;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          widget.label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            color: widget.color,
            fontSize: 11,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 4),
        Flexible(
          child: (c == null || !c.value.isInitialized)
              ? _Blank(
                  /* 🔴 **셋을 가른다** — 없는 선수(영영 안 옴) · 못 연 것
                     (까닭이 있음) · 아직 여는 중. 스피너 하나로 뭉치면
                     **고장과 기다림이 같아 보인다.** */
                  missing: widget.source == null,
                  failed: _failed,
                )
              : Center(
                  child: AspectRatio(
                    aspectRatio: c.value.aspectRatio,
                    child: _maybeMirror(
                      Stack(
                        fit: StackFit.expand,
                        children: [
                          VideoPlayer(c),
                          if (widget.skeleton.known)
                            ValueListenableBuilder<VideoPlayerValue>(
                              valueListenable: c,
                              builder: (context, v, _) => SkeletonOverlay(
                                skeleton: widget.skeleton,
                                // 🔴 되감는 중이면 **옛 자리**(위 [_held]).
                                position: _held ?? v.position,
                                color: widget.color,
                                // 작은 칸이라 네모와 딱지는 뺀다 — 다 가린다.
                                showBox: false,
                                /* 🔴 **영상 위에는 관절 고리를 안 찍는다**
                                   (2026-09-25 사용자 요청: 「영상에는 관절만
                                   있고, 동그라미는 없애줄 수 있어?」).
                                   고리가 흰 7px 고정이라 칸이 반으로 줄어든
                                   여기서는 **뼈대를 덮어 버린다.**
                                   ⚠️ 세 순간 카드는 그대로 둔다 — 거기서는
                                   고리가 자세를 읽는 데 도움이 된다. */
                                showJoints: false,
                              ),
                            ),
                        ],
                      ),
                    ),
                  ),
                ),
        ),
      ],
    );
  }

  Widget _maybeMirror(Widget child) => widget.mirrored
      ? Transform(
          alignment: Alignment.center,
          transform: Matrix4.identity()..scaleByDouble(-1, 1, 1, 1),
          child: child,
        )
      : child;
}

class _Blank extends StatelessWidget {
  const _Blank({required this.missing, this.failed});
  final bool missing;
  final String? failed;

  @override
  Widget build(BuildContext context) => Center(
    child: missing
        ? const Text(
            '영상 없음',
            style: TextStyle(color: Color(0x55FFFFFF), fontSize: 11),
          )
        : failed != null
        ? const Padding(
            padding: EdgeInsets.all(6),
            child: Text(
              '영상을 열지 못했습니다',
              textAlign: TextAlign.center,
              style: TextStyle(color: Color(0xFFE5484D), fontSize: 11),
            ),
          )
        : const SizedBox(
            width: 16,
            height: 16,
            child: CircularProgressIndicator(
              strokeWidth: 1.6,
              color: Colors.white24,
            ),
          ),
  );
}
