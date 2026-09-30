import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:video_player/video_player.dart';

import '../../../video/data/models/public_video.dart';
import '../../../video/data/video_providers.dart';

/// 홈 한가운데의 **공개 영상 줄** (2026-09-24 사용자 요청 + 레퍼런스).
///
/// 소개 두 줄(「함께 뛸 팀을 만들고,…」)이 있던 자리다. 가운데 한 편이 밝게
/// 제 크기로 서고 **양옆으로 두 장씩**, 갈수록 작아지고 어두워진다. 카드끼리
/// **겹친다**(사용자 요청: 「사이가 너무 멀어. 겹쳐줘」).
///
/// 🔴 **좌우로 끝없이 돈다.** 목록의 끝에서 처음으로 이어 붙어 어느 쪽으로
/// 밀어도 계속 나온다(「다 돌면 다시 무한으로 계속 나오게」).
///
/// 🔴 **여기 뜨는 것은 `GET /videos/public` 이다** — 내 것만이 아니라 **누구든
/// 공개해 둔 것**이 온다. 그래서 앱에서 올리든 웹에서 올리든 **공개로 돌리면
/// 양쪽에 똑같이** 뜬다(목록에 드는 조건은 [PublicVideo] 머리말).
///
/// 🔴 **서버가 썸네일을 안 준다.** 그래서 웹과 같은 수를 쓴다 — 영상을 열어
/// **첫 프레임**을 세워 두고, 가운데 것만 튼다(웹은 `<video preload="metadata">`).
///
/// ⛔ **[PageView] 로 되돌리지 말 것** — 겹치면 **가운데가 맨 위로 안 온다.**
/// 그리는 순서가 인덱스 순이라 늘 오른쪽 것이 위를 덮는다. 손짓을 직접 받는
/// 지금 구조라야 **가운데에서 먼 것부터** 그려 층을 맞출 수 있다.
class HomeVideoStrip extends ConsumerStatefulWidget {
  const HomeVideoStrip({super.key, required this.height});

  /// 카드 높이 — 홈이 **남는 자리를 재서** 넘긴다(판 아랫변 ~ 흰 판 윗변).
  final double height;

  /// 가운데에서 한 칸 떨어질 때마다 카드 **중심**이 옮겨 가는 거리 — 카드 폭에
  /// 대한 비율이다. 🔴 **1 보다 작아야 겹친다**(사용자 요청).
  static const stepRatio = 0.52;

  /// 한 칸 떨어질 때마다 곱해지는 크기.
  static const stepScale = 0.84;

  /// 한 칸·두 칸 떨어진 카드를 덮는 검정의 진하기.
  static const dim1 = 0.45;
  static const dim2 = 0.65;

  /// 🔴 **양옆 두 장씩, 다섯이 보인다**(사용자 요청).
  static const side = 2;

  /// 그리는 범위 — 보이는 것보다 한 장 더 그려서 **가장자리에서 튀어나오지**
  /// 않게 한다. 🔴 **여는 것은 [side] 까지다**(아래 `_open`).
  static const drawSide = 3;

  static const radius = 18.0;

  @override
  ConsumerState<HomeVideoStrip> createState() => _HomeVideoStripState();
}

class _HomeVideoStripState extends ConsumerState<HomeVideoStrip>
    with SingleTickerProviderStateMixin {
  /// 지금 자리(칸 단위, 소수). 🔴 **끝이 없다** — 목록을 넘어가면 그냥 계속
  /// 커지거나 작아지고, 어느 영상인지는 나눗셈 나머지로 정한다.
  double _pos = 0;

  /* 🔴 **`late final … = AnimationController(…)` 로 두지 말 것.** 그 꼴은
     **게으르다** — 한 번도 안 민 화면에서는 `dispose()` 의 `_snap.dispose()`
     가 **그제서야** 컨트롤러를 만들고, 이미 트리에서 떨어진 자리에서
     `vsync` 를 찾다가 터진다(「Looking up a deactivated widget's ancestor」,
     2026-09-24 에 라우터 시험 46개가 이것으로 깨졌다). 여기서 못 박는다. */
  late final AnimationController _snap;
  Animation<double>? _snapAnim;

  @override
  void initState() {
    super.initState();
    _snap = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 340),
    );
  }

  /// 손가락이 닿아 있는 동안은 거짓 — 🔴 **휙휙 넘기는 내내 헛되이 틀지
  /// 않으려는 것이다**(사용자 결정: 「멈춘 뒤에만 재생」).
  bool _settled = true;

  /// 전체화면 영상으로 **나가 있는 동안** 참 (2026-09-24 사용자 지적: 「다 보고
  /// 뒤로 나와서 홈페이지 갔을때, 가운데 영상이 멈춘다」).
  ///
  /// 🔴 **고치는 일이 둘인데 한 값으로 된다.**
  /// ⑴ **나가 있는 동안 홈의 재생기를 닫는다** — 안 닫으면 전체화면 재생기와
  ///    **디코더를 놓고 다툰다**(안드로이드는 동시에 몇 개 못 연다). 홈 것은
  ///    보이지도 않으면서 자리만 차지하고, 그 탓에 전체화면 쪽이 못 열리기도 한다.
  /// ⑵ **돌아오면 저절로 다시 열린다** — 이 값이 거짓으로 돌아가면 `open` 이
  ///    참이 되고, [_VideoCard] 의 `didUpdateWidget` 이 늘 하던 대로 연다.
  ///    따로 「되살리기」 길을 안 만들어도 되는 것이 이 방식의 이점이다.
  ///
  /// ⚠️ **돌아왔을 때 포스터가 먼저 뜨고 영상이 뒤따른다** — 다시 여는 데
  /// 시간이 걸려서다. 검은 칸은 안 보인다(포스터가 늘 깔려 있다).
  bool _away = false;

  double get _cardWidth => widget.height * 16 / 9;
  double get _step => _cardWidth * HomeVideoStrip.stepRatio;

  /// 가운데에 **멈춰 선** 칸.
  int get _center => _pos.round();

  @override
  void dispose() {
    _snap.dispose();
    super.dispose();
  }

  void _onDragStart(DragStartDetails _) {
    _snap.stop();
    if (_settled) setState(() => _settled = false);
  }

  void _onDragUpdate(DragUpdateDetails d) {
    setState(() => _pos -= d.delta.dx / _step);
  }

  void _onDragEnd(DragEndDetails d) {
    /* 세게 튕기면 그 방향으로 한 칸 더 간다 — 안 그러면 빠르게 쓸어도 늘
       제자리 옆 칸에 멈춰 「무겁다」로 느껴진다. */
    final v = d.velocity.pixelsPerSecond.dx;
    var target = _pos.round();
    if (v.abs() > 320) target = (v < 0 ? _pos.ceil() : _pos.floor()) + (v < 0 ? 1 : -1);
    _animateTo(target.toDouble());
  }

  void _animateTo(double target) {
    final anim = Tween(begin: _pos, end: target)
        .animate(CurvedAnimation(parent: _snap, curve: Curves.easeOutCubic));
    _snapAnim?.removeListener(_onSnap);
    _snapAnim = anim..addListener(_onSnap);
    _snap
      ..reset()
      ..forward().whenComplete(() {
        if (mounted) setState(() => _settled = true);
      });
  }

  void _onSnap() {
    final a = _snapAnim;
    if (a != null) setState(() => _pos = a.value);
  }

  /// 화면에서 그 칸의 **중심 x**(줄 안에서의 좌표).
  double _dx(int i, double width) => width / 2 + (i - _pos) * _step;

  void _onTapUp(TapUpDetails d, double width, List<PublicVideo> videos) {
    /* 🔴 **가운데에서 가까운 것부터 맞춰 본다** — 겹쳐 있으므로 눈에 보이는
       층(가운데가 맨 위)과 같은 순서로 집어야 누른 대로 걸린다. */
    for (var k = 0; k <= HomeVideoStrip.side; k += 1) {
      for (final i in {_center - k, _center + k}) {
        final scale = _scaleOf((i - _pos).abs());
        final w = _cardWidth * scale;
        final cx = _dx(i, width);
        if ((d.localPosition.dx - cx).abs() <= w / 2) {
          if (i == _center) {
            /* 🔴 **누른 그 영상으로 간다**(2026-09-24 사용자 요청: 「그 영상으로
               영상페이지로 바로 나와야해」). 전에는 `go('/videos')` — 영상
               **분석** 화면이었고 **어떤 영상인지가 전달되지 않았다.**

               🔴 **`go` 가 아니라 `push` 다.** 얹어야 뒤로 가기로 홈에 돌아오고,
               **돌아오는 시점을 여기서 알 수 있다**(아래 `then`). */
            setState(() => _away = true);
            /* 🔴 **돌아오면 다시 튼다** — [_away] 머리말의 ⑵. `push` 가 주는
               Future 는 **어떻게 나왔든**(단추·시스템 뒤로 가기) 끝난다. */
            context.push('/videos/${_videoAt(i, videos).id}').then((_) {
              if (mounted) setState(() => _away = false);
            });
          } else {
            _animateTo(i.toDouble());
          }
          return;
        }
      }
    }
  }

  /// 그 칸에 서는 영상 — 🔴 **`_slot` 과 같은 식이어야 한다.** 다르면 **보이는
  /// 것과 다른 영상**이 열린다.
  PublicVideo _videoAt(int i, List<PublicVideo> videos) =>
      videos[((i % videos.length) + videos.length) % videos.length];

  double _scaleOf(double d) =>
      math.pow(HomeVideoStrip.stepScale, d.clamp(0.0, 2.0)).toDouble();

  double _dimOf(double d) {
    final a = d.clamp(0.0, 1.0);
    final b = (d - 1).clamp(0.0, 1.0);
    return HomeVideoStrip.dim1 * a +
        (HomeVideoStrip.dim2 - HomeVideoStrip.dim1) * b;
  }

  /// 칸 하나 — 🔴 **키가 여기 붙는다**(위 주석의 까닭).
  Widget _slot(
    BuildContext context,
    int i,
    double width,
    List<PublicVideo> videos,
  ) {
    final d = (i - _pos).abs();
    final scale = _scaleOf(d);
    final w = _cardWidth * scale;
    final h = widget.height * scale;
    /* 🔴 **나머지로 영상을 고른다 — 여기가 「무한」의 전부다.** `%` 는 음수에서
       음수를 주므로 한 번 더 더해 준다. 목록 전체가 차례로 돌고, 끝에서 처음으로
       이어진다(사용자 요청: 「올려져 있는 공개된 영상들이 다 무한으로」).

       🔴 **누를 때도 같은 식을 쓴다**([_videoAt]) — 둘이 갈라지면 **보이는 것과
       다른 영상**이 열린다. */
    final v = _videoAt(i, videos);
    return Positioned(
      key: ValueKey(i),
      left: _dx(i, width) - w / 2,
      top: (widget.height - h) / 2,
      width: w,
      height: h,
      child: _VideoCard(
        video: v,
        dim: _dimOf(d),
        // 🔴 **멈춰 선 그 한 칸만 튼다.** 나가 있는 동안은 아무것도 안 튼다.
        playing: !_away && _settled && i == _center,
        /* 🔴 **영상은 가운데 하나만 연다.** 나머지 넷은 포스터(작은 JPEG)로
           충분하고, 그 편이 훨씬 빠르다 — 원본을 여는 데 한 장에 1.9초가
           걸렸다(실기기 실측). 디코더도 하나만 쓴다. */
        open: !_away && i == _center,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(publicVideosProvider);
    final videos = async.value ?? const <PublicVideo>[];

    /* 🔴 **못 받은 것을 감추지 않는다** (2026-09-25, 사용자: 「아니 대체 왜
       영상 홈페이지에서 안보이냐고」).

       그날 실측으로 원인은 **서버**였다 — `/videos/public` 이 30초를 넘겨도
       답이 없었고 `/regions` 는 0.5초에 답했다. 그런데 화면은 실패도 빈 자리로
       그려서, **어느 쪽 문제인지 아무도 알 수 없었다.** `.value` 는 오류일 때도
       `null` 이라 「아직 오는 중」과 「못 받았다」가 같아 보인다.

       🔴 **[publicVideosProvider] 는 재시도를 안 한다**(그쪽 머리말 — 무한
       재시도가 느린 서버를 더 때린다). 그래서 **사람이 다시 시킬 길**이 여기
       있어야 한다. ⛔ 조용한 빈 자리로 되돌리지 말 것. */
    if (async.hasError && videos.isEmpty) {
      return SizedBox(
        height: widget.height,
        width: double.infinity,
        child: Center(
          child: GestureDetector(
            key: const Key('home-videos-failed'),
            behavior: HitTestBehavior.opaque,
            onTap: () => ref.invalidate(publicVideosProvider),
            child: const Padding(
              padding: EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              child: Text(
                '영상을 불러오지 못했습니다 · 눌러서 다시',
                style: TextStyle(color: Color(0x99FFFFFF), fontSize: 12.5),
              ),
            ),
          ),
        ),
      );
    }

    /* 🔴 **자리는 늘 차지한다.** 아직 못 받았거나 한 편도 없을 때 접히면,
       목록이 도착하는 순간 아래 것들이 통째로 밀려 **화면이 덜컥거린다.**
       ⚠️ **한 편도 없는 것은 오류가 아니다** — 그때는 조용히 자리만 지킨다. */
    if (videos.isEmpty) {
      return SizedBox(height: widget.height, width: double.infinity);
    }

    return LayoutBuilder(
      builder: (context, box) {
        final width = box.maxWidth;
        // 가운데에서 먼 것부터 그린다 — 마지막에 그린 가운데가 맨 위에 온다.
        /* 🔴 **동점을 번호로 깨뜨린다.** 거리만으로 정렬하면 ±k 가 같은 값이라
           `List.sort` 가 프레임마다 순서를 뒤집을 수 있고, 그러면 아래 키 매칭이
           매번 다시 일어난다. */
        final slots = [
          for (var k = -HomeVideoStrip.drawSide; k <= HomeVideoStrip.drawSide; k += 1)
            _center + k,
        ]..sort((a, b) {
            final c = (b - _pos).abs().compareTo((a - _pos).abs());
            return c != 0 ? c : a.compareTo(b);
          });

        return GestureDetector(
          behavior: HitTestBehavior.opaque,
          onHorizontalDragStart: _onDragStart,
          onHorizontalDragUpdate: _onDragUpdate,
          onHorizontalDragEnd: _onDragEnd,
          onTapUp: (d) => _onTapUp(d, width, videos),
          child: SizedBox(
            height: widget.height,
            width: width,
            child: Stack(
              clipBehavior: Clip.none,
              children: [
                /* 🔴 **키는 바깥(여기)에 단다.** [Stack] 의 자식 목록이 매
                   프레임 **순서를 바꾸기** 때문이다(가운데를 맨 위로 올리려고
                   먼 것부터 그린다). 키를 안쪽 [_VideoCard] 에만 달면 Flutter 가
                   바깥을 **자리로** 맞추고 안쪽 키가 어긋나, **카드 상태가
                   통째로 버려졌다 다시 만들어진다** — 영상이 열리다 말고 계속
                   버려져서 **끝내 아무것도 안 떴다**(2026-09-24 에 실제로 겪었다).
                   ⛔ 키를 안쪽으로 되돌리지 말 것. */
                for (final i in slots)
                  _slot(context, i, width, videos),
              ],
            ),
          ),
        );
      },
    );
  }
}

/// 카드 한 장 — 영상 첫 프레임(또는 재생 중인 화면)을 둥근 칸에 담는다.
///
/// 🔴 **[open] 이 거짓이면 컨트롤러를 아예 안 만들고, 있던 것은 버린다.**
/// 안드로이드는 **동시에 열 수 있는 디코더가 몇 개 안 된다** — 넘긴 만큼
/// 쌓아 두면 몇 편 지나서부터 **아무것도 안 열린다**(`clip_player.dart` 가
/// 같은 데서 데였다). 그래서 살아 있는 것은 **보이는 다섯**뿐이다.
///
/// ⚠️ **처음엔 셋만 열었다**(가운데 ±1). 그랬더니 사용자가 「넘기지 않으면
/// 검정으로 보이는 게 너무 많다」고 했다 — 보이는 칸을 안 열어 두면 **넘겨야
/// 비로소 뜨기** 때문이다. 🔴 **보이는 수와 여는 수를 어긋나게 두지 말 것.**
class _VideoCard extends ConsumerStatefulWidget {
  const _VideoCard({
    required this.video,
    required this.dim,
    required this.playing,
    required this.open,
  });

  final PublicVideo video;
  final double dim;
  final bool playing;

  /// 영상을 열 것인가 — 🔴 **가운데 한 칸만 참이다.** 나머지는 포스터만 쓴다.
  final bool open;

  @override
  ConsumerState<_VideoCard> createState() => _VideoCardState();
}

/* 🔴 **컨트롤러는 「속성이 실제로 바뀔 때」만 건드린다 — `build` 에서 하지
   않는다.** 처음에 `build` 안에서 `addPostFrameCallback` 으로 열고·틀고·
   버렸는데(`clip_player.dart` 의 관용구), **실기기에서 앱이 통째로 죽었다**
   (`Fatal signal 6 (SIGABRT) in MediaCodec_loop`, 2026-09-24).

   까닭: 이 줄은 손가락을 따라 크기·어둡기가 이어지므로 **초당 60번 리빌드된다.**
   `clip_player.dart` 는 거의 리빌드가 없어 같은 관용구로도 멀쩡했지만, 여기서는
   프레임마다 재생·정지·해제 요청이 네이티브 디코더로 쏟아진다.

   ⛔ **`build` 에서 컨트롤러를 만지는 방식으로 되돌리지 말 것.** */
class _VideoCardState extends ConsumerState<_VideoCard> {
  VideoPlayerController? _c;

  /// 지금 컨트롤러가 물고 있는 주소 — 같은 주소로 두 번 만들지 않는다.
  String? _for;

  /// 🔴 **여는 일과 버리는 일을 줄 세운다.** 겹치면 아직 초기화 중인 것을
  /// 버리게 되고, 그게 네이티브에서 터지는 자리다.
  Future<void> _work = Future.value();

  /* 🔴 **처음 세워질 때도 한 번 맞춘다.** 처음 보이는 카드들은 [didUpdateWidget]
     이 안 불리고, 아래 `ref.listen` 은 **값이 바뀔 때만** 울려서 이미 받아 둔
     주소로는 안 울린다 — 둘만 두면 첫 카드들이 영영 안 열린다. */
  @override
  void initState() {
    super.initState();
    if (widget.open) _sync();
  }

  @override
  void didUpdateWidget(_VideoCard old) {
    super.didUpdateWidget(old);
    // 🔴 `dim` 은 프레임마다 바뀐다 — 그걸로는 아무것도 하지 않는다.
    if (widget.open != old.open || widget.video.id != old.video.id) _sync();
    if (widget.playing != old.playing) _queue(_apply);
  }

  @override
  void dispose() {
    _c?.dispose();
    super.dispose();
  }

  /// 열려 있어야 하는가에 맞춘다.
  void _sync() {
    if (!widget.open) {
      _queue(_close);
      return;
    }
    final url = ref.read(playbackUrlProvider(widget.video.id)).value;
    if (url != null) _queue(() => _open(url));
  }

  void _queue(Future<void> Function() job) {
    _work =
        _work.then((_) => mounted ? job() : Future.value()).catchError((_) {});
  }

  Future<void> _open(String url) async {
    if (_for == url) return;
    _for = url;
    final old = _c;
    _c = null;
    // 🔴 **먼저 비운다** — 새것을 만드는 동안 옛것이 그려지면 안 된다.
    await old?.dispose();
    final next = VideoPlayerController.networkUrl(Uri.parse(url));
    try {
      await next.initialize();
      // 🔴 **홈에서 소리가 나면 안 된다**(사용자 결정).
      await next.setVolume(0);
      await next.setLooping(true);
      /* 🔴 **첫 프레임을 세워 둔다.** 0 으로 두면 기기에 따라 **검은 화면**이
         나온다 — 웹이 `#t=0.1` 로 같은 수를 쓴다. */
      await next.seekTo(const Duration(milliseconds: 100));
    } catch (_) {
      // 못 열면 빈 칸으로 둔다 — 나머지 카드는 그대로 그려야 한다.
      await next.dispose();
      _for = null;
      return;
    }
    if (!mounted) {
      await next.dispose();
      return;
    }
    _c = next;
    setState(() {});
    await _apply();
  }

  Future<void> _close() async {
    final old = _c;
    if (old == null) return;
    _c = null;
    _for = null;
    await old.dispose();
    if (mounted) setState(() {});
  }

  /// 틀어야 하는가에 맞춘다 — **이미 그 상태면 아무것도 안 한다.**
  Future<void> _apply() async {
    final c = _c;
    if (c == null || !c.value.isInitialized) return;
    if (widget.playing && !c.value.isPlaying) {
      await c.play();
    } else if (!widget.playing && c.value.isPlaying) {
      await c.pause();
    }
  }

  @override
  Widget build(BuildContext context) {
    /* 🔴 **`watch` 가 아니라 `listen` 이다.** 주소가 도착하는 **그 한 번**만
       받으면 된다 — `watch` 로 두면 리빌드 고리에 컨트롤러 조작이 다시 엮인다. */
    if (widget.open) {
      ref.listen(playbackUrlProvider(widget.video.id), (_, next) {
        final url = next.value;
        if (url != null && widget.open) _queue(() => _open(url));
      });
    }

    /* 🔴 **포스터는 다섯 칸이 모두 본다** — `open` 과 무관하다. 이것이
       「검은 칸」을 없애는 자리다. `watch` 라 도착하면 다시 그린다. */
    final poster = ref.watch(videoPosterProvider(widget.video.id)).value;

    final c = _c;
    final ready = c != null && c.value.isInitialized;

    return ClipRRect(
      borderRadius: BorderRadius.circular(HomeVideoStrip.radius),
      child: Stack(
        fit: StackFit.expand,
        children: [
          /* 🔴 **순검정이 아니라 짙은 회색이다.** 포스터가 오기 전 잠깐 비는데,
             순검정이면 「고장난 칸」처럼 보인다. */
          const ColoredBox(color: Color(0xFF2A2A2C)),
          /* 🔴 **포스터가 바닥에 깔린다.** 다섯 칸 전부 이것으로 그려지고,
             가운데만 그 **위로** 영상이 덮는다. 영상이 열리는 동안에도 카드가
             비지 않는 것이 이 배치의 전부다 — 2초가 눈에 안 띄게 된다. */
          if (poster != null)
            Image.memory(poster, fit: BoxFit.cover, gaplessPlayback: true),
          /* 🔴 **칸을 꽉 채우고 넘치는 것은 자른다**(`cover`). 레퍼런스가
             그렇고, 비율이 제각각인 영상들이 한 줄에 서므로 칸을 영상 비에
             맡기면 카드마다 폭이 달라져 줄이 들쭉날쭉해진다. */
          if (ready)
            FittedBox(
              fit: BoxFit.cover,
              child: SizedBox(
                width: c.value.size.width,
                height: c.value.size.height,
                child: VideoPlayer(c),
              ),
            ),
          // 가운데에서 멀수록 어둡다.
          if (widget.dim > 0)
            ColoredBox(color: Colors.black.withValues(alpha: widget.dim)),
        ],
      ),
    );
  }
}
