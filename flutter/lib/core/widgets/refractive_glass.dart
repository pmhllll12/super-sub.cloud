import 'dart:ui' as ui;

import 'package:flutter/foundation.dart' show ValueListenable;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';

import 'glass_shader.dart';
import 'glass_strength.dart';
import 'glass_surface.dart';

/// 정지 상태의 흰 겹. `kGlassFill`(0.10)보다 훨씬 옅다. 유리의 존재는
/// 굴절이 드러내지, 흰 막이 드러내는 게 아니다.
final Color kGlassFillIdle = Colors.white.withValues(alpha: 0.02);

/// 유리 조각의 기하. 값의 출처는 언제나 Dart 한 곳이다. 단위는 논리 픽셀.
@immutable
class GlassNotch {
  final double left;
  final double right;
  final double depth;
  final double radius;

  /// 참이면 홈 파인 바가 아니라 그냥 둥근 사각형이다(로고 알약). 그때
  /// [left]는 쓰지 않고 [right]·[depth]가 폭·높이가 된다.
  final bool pill;

  const GlassNotch({
    required this.left,
    required this.right,
    required this.depth,
    required this.radius,
    this.pill = false,
  });
}

/// 굴절하는 유리 한 겹.
///
/// 셰이더를 쓸 수 없으면(Impeller가 아니거나 로드 전) 기존 흐림 유리로
/// 물러선다 — 예외를 던지지 않고, 사용자는 오늘과 같은 바를 본다.
class RefractiveGlass extends StatelessWidget {
  final GlassNotch notch;
  final ValueListenable<double> strength;
  final double warpScale;
  final double warp;
  final double dispersion;
  final bool debug;
  final Widget? child;

  const RefractiveGlass({
    super.key,
    required this.notch,
    required this.strength,
    this.warpScale = 45,
    this.warp = 5,
    this.dispersion = 0.35,
    this.debug = false,
    this.child,
  });

  @override
  Widget build(BuildContext context) {
    if (!GlassShader.isSupported) {
      return BackdropFilter(
        filter: ui.ImageFilter.blur(sigmaX: kGlassBlur, sigmaY: kGlassBlur),
        child: ColoredBox(color: kGlassFill, child: child),
      );
    }
    final dpr = MediaQuery.devicePixelRatioOf(context);
    // 자리가 움직이는데 **다시 칠해지지 않는** 두 자리를 여기서 함께 막는다.
    //
    // 라우트 전환과 스크롤 뷰포트는 둘 다 내용을 다시 칠하지 않고 레이어만
    // 옮긴다. 유리는 자기 화면 자리를 페인트할 때 읽으므로, 그냥 두면 옛
    // 자리를 문 채 그려진 내용만 흘러 어긋난다(전환에서 최대 90px). 그
    // 애니메이션을 듣고 매 프레임 다시 지으면 페인트가 돌면서 그 시점의
    // 누적 변환에서 원점을 새로 읽는다.
    //
    // 쓰는 쪽마다 붙일 일이 아니라 여기서 한 번에 한다 — 이 위젯을 쓰는
    // 자리가 스크롤 안인지 아닌지를 쓰는 쪽이 신경 쓸 이유가 없다.
    final moving = <Listenable>[
      ?ModalRoute.of(context)?.animation,
      ?Scrollable.maybeOf(context)?.position,
    ];
    if (moving.isEmpty) return _build(context, dpr);
    return ListenableBuilder(
      listenable: Listenable.merge(moving),
      builder: (context, _) => _build(context, dpr),
    );
  }

  Widget _build(BuildContext context, double dpr) {
    return ValueListenableBuilder<double>(
      valueListenable: strength,
      builder: (context, s, child_) => _RefractiveBackdrop(
        notch: notch,
        devicePixelRatio: dpr,
        warpScale: warpScale,
        warp: warp,
        dispersion: dispersion,
        strength: s,
        debug: debug,
        // 흰 겹은 세기를 따라 진해진다. 그래서 빌더 **안**에 있다 — 밖에
        // 두면(=아래 child로 넘기면) 세기가 바뀌어도 다시 안 그려진다.
        child: ColoredBox(
          color: Color.lerp(kGlassFillIdle, kGlassFill, s)!,
          child: child_,
        ),
      ),
      child: child,
    );
  }
}

/// 셰이더를 유니폼째로 들고 있는 BackdropFilter.
///
/// 그냥 [BackdropFilter]를 쓰지 못하는 이유는 좌표계 하나다. 필터 안에서
/// `FlutterFragCoord()`가 주는 좌표는 **화면의 물리 픽셀**이지 이 위젯의
/// 지역 논리 픽셀이 아니다. 위젯이 화면 어디에 놓였는지는 페인트 시점에만
/// 알 수 있으므로(빌드 때는 아직 배치 전이다) 렌더 객체가 그 자리를
/// `uOrigin`으로 넘긴다.
class _RefractiveBackdrop extends SingleChildRenderObjectWidget {
  final GlassNotch notch;
  final double devicePixelRatio;
  final double warpScale;
  final double warp;
  final double dispersion;
  final double strength;
  final bool debug;

  const _RefractiveBackdrop({
    required this.notch,
    required this.devicePixelRatio,
    required this.warpScale,
    required this.warp,
    required this.dispersion,
    required this.strength,
    required this.debug,
    super.child,
  });

  _GlassParams get _params => (
        notch: notch,
        devicePixelRatio: devicePixelRatio,
        warpScale: warpScale,
        warp: warp,
        dispersion: dispersion,
        strength: strength,
        debug: debug,
      );

  @override
  _RenderRefractiveBackdrop createRenderObject(BuildContext context) =>
      _RenderRefractiveBackdrop(_params);

  @override
  void updateRenderObject(
    BuildContext context,
    _RenderRefractiveBackdrop renderObject,
  ) {
    renderObject.params = _params;
  }
}

/// 셰이더에 넘길 값 한 벌.
typedef _GlassParams = ({
  GlassNotch notch,
  double devicePixelRatio,
  double warpScale,
  double warp,
  double dispersion,
  double strength,
  bool debug,
});

class _RenderRefractiveBackdrop extends RenderProxyBox {
  _RenderRefractiveBackdrop(this._params);

  _GlassParams _params;
  ui.FragmentShader? _shader;

  /// 값이 바뀌었는지 따지지 않고 언제나 다시 칠한다. 이 위젯은 세기가 바뀔
  /// 때만 다시 만들어지므로, 비교를 아끼는 것보다 코드가 짧은 편이 낫다.
  set params(_GlassParams value) {
    _params = value;
    markNeedsPaint();
  }

  @override
  BackdropFilterLayer? get layer => super.layer as BackdropFilterLayer?;

  @override
  bool get alwaysNeedsCompositing => child != null;

  @override
  void paint(PaintingContext context, Offset offset) {
    if (child == null) {
      layer = null;
      return;
    }
    // 셰이더는 화면의 물리 픽셀로 말한다. 논리 픽셀로 재는 이쪽 값은 전부
    // 여기서 한 번에 환산한다 — 셰이더 안에는 환산이 없다.
    //
    // 환산에 dpr만 쓰면 안 된다. 페인트의 offset은 "지금 레이어"의 좌표라,
    // 중간에 변환이 끼면 화면 자리와 어긋난다. 그래서 여기까지 쌓인 변환을
    // 통째로 따라간다. (Transform.scale(0.8)로 재보면 dpr만 쓸 때 원점이
    // 108px, 배율이 0.8배 틀린다.)
    //
    // getTransformTo(null)은 RenderView를 건너뛰므로(object.dart의 walk가
    // 마지막 한 칸을 빼고 돈다) dpr이 안 들어 있다. 앞에 곱해 준다.
    //
    // 이 계산은 paint가 도는 순간에만 맞다. 변환이 **다시 칠하지 않고**
    // 레이어에만 걸리는 자리(라우트 전환, 스크롤 뷰포트)에서는 이 함수가
    // 아예 안 불려 유니폼이 얼어붙는다. 그래서 쓰는 쪽이 그 애니메이션을
    // 듣고 다시 짓게 한다 — 위 build의 ListenableBuilder와 말씀 상자의
    // ScrollPosition 리스너가 그 일을 한다.
    final dpr = _params.devicePixelRatio;
    final toDevice = Matrix4.diagonal3Values(dpr, dpr, 1.0)
      ..multiply(getTransformTo(null));
    final origin = MatrixUtils.transformPoint(toDevice, Offset.zero);
    // 배율도 dpr 단독이 아니라 누적 스케일이다. SDF가 등방이라 한 축만 쓴다 —
    // 회전이나 축마다 다른 스케일이 끼면 이 한 값으로는 못 버틴다.
    final s = (MatrixUtils.transformPoint(toDevice, const Offset(1.0, 0.0)) -
            origin)
        .distance;
    final notch = _params.notch;
    final shader = _shader ??= GlassShader.program!.fragmentShader();
    shader
      // 0,1은 엔진이 uSize로 채운다.
      ..setFloat(2, origin.dx)
      ..setFloat(3, origin.dy)
      ..setFloat(4, notch.left * s)
      ..setFloat(5, notch.right * s)
      ..setFloat(6, notch.depth * s)
      ..setFloat(7, notch.radius * s)
      ..setFloat(8, _params.warpScale * s)
      ..setFloat(9, _params.warp * s)
      ..setFloat(10, _params.dispersion)
      ..setFloat(11, _params.strength)
      ..setFloat(12, _params.debug ? 1 : 0)
      ..setFloat(13, notch.pill ? 1 : 0);

    layer ??= BackdropFilterLayer();
    layer!.filter = ui.ImageFilter.shader(shader);
    context.pushLayer(layer!, super.paint, offset);
  }

  @override
  void dispose() {
    _shader?.dispose();
    super.dispose();
  }
}

/// 하단 바와 **같은 유리**를 알약·원 모양으로 한 조각.
///
/// 굴절 유리는 강도를 받아야 하는데, 그 값은 화면 맨 위에서 스크롤을 듣고
/// 있다. 쓰는 자리마다 손에서 손으로 넘기지 않도록 여기서 [GlassStrengthScope]를
/// 찾아 쓴다. 위에 아무도 없으면 흐림 유리로 물러선다 — 예외를 던지지 않는다.
///
/// **자식 안에 유리를 또 넣지 않는다.** 안쪽이 아직 안 끝난 바깥을 읽어
/// 내용이 프레임째로 사라진다. 층을 내고 싶으면 흐림 없이 색만 얹는다.
class GlassPill extends StatelessWidget {
  /// 모서리 반지름. 폭·높이의 절반을 주면 원이 된다.
  final double radius;

  /// 가장자리가 뒤를 끌어당기는 정도. 0이면 휘지 않고 흐림·분산만 남는다.
  final double warp;

  final Widget? child;

  const GlassPill({
    super.key,
    required this.radius,
    this.warp = 5,
    this.child,
  });

  @override
  Widget build(BuildContext context) {
    final strength = GlassStrengthScope.maybeOf(context);
    if (strength == null) {
      return GlassSurface(
        borderRadius: BorderRadius.circular(radius),
        child: child,
      );
    }
    return ClipRRect(
      borderRadius: BorderRadius.circular(radius),
      child: LayoutBuilder(
        builder: (context, box) => RefractiveGlass(
          notch: GlassNotch(
            left: 0,
            right: box.maxWidth,
            depth: box.maxHeight,
            radius: radius,
            pill: true,
          ),
          strength: strength,
          warp: warp,
          child: child,
        ),
      ),
    );
  }
}
