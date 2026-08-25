import 'dart:math' show pi;

import 'package:flutter/material.dart';

import 'refractive_glass.dart';

/// 유리 세기. 이 판들은 늘 서 있다.
const Animation<double> kGlassOn = AlwaysStoppedAnimation<double>(1);

/// 가장자리가 뒤를 끌어당기는 정도.
const double kGlassWarp = 7;

/// 뒤를 굴절시키는 유리 한 조각.
///
/// 로그인 시트의 버튼과 달리 이 판은 **진짜 유리를 쓸 수 있다** — 다른 유리
/// 안에 들어 있지 않기 때문이다. 유리 안의 유리가 금지인 이유는
/// `refractive_glass.dart` 주석 참고.
class GlassPanel extends StatelessWidget {
  const GlassPanel({
    super.key,
    required this.radius,
    required this.child,
    this.sheen,
    this.phase = 0,
  });

  final double radius;
  final Widget child;

  /// 테두리를 도는 빛의 위상(0~1을 반복). null이면 도는 빛 없이 옅은 선만.
  final Animation<double>? sheen;

  /// 이 조각만큼 늦게 돈다. 전부 같은 위상이면 한꺼번에 반짝여 기계처럼 보인다.
  final double phase;

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      // 테두리는 유리 **위에** 그린다 — 밑에 두면 굴절에 먹혀 흐려진다.
      foregroundPainter: _TravelingEdge(
        repaint: sheen,
        progress: sheen,
        phase: phase,
        radius: radius,
      ),
      child: ClipRRect(
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
            strength: kGlassOn,
            warp: kGlassWarp,
            child: child,
          ),
        ),
      ),
    );
  }
}

/// 둘레를 도는 얇은 흰 빛.
///
/// 늘 켜져 있는 아주 옅은 선 위에, 한 점만 밝은 띠가 원을 그리며 돈다.
/// 스윕 그라데이션을 회전시켜 만든다 — 점을 좌표로 움직이면 모서리에서
/// 속도가 튀는데, 각도로 돌리면 둘레를 고르게 지난다.
class _TravelingEdge extends CustomPainter {
  const _TravelingEdge({
    required super.repaint,
    required this.progress,
    required this.phase,
    required this.radius,
  });

  final Animation<double>? progress;
  final double phase;
  final double radius;

  /// **아주 얇다.** 굵으면 테두리가 눈에 먼저 들어와 유리가 아니라 상자로
  /// 읽힌다.
  static const double _width = 1.0;

  @override
  void paint(Canvas canvas, Size size) {
    final rrect = RRect.fromRectAndRadius(
      Offset.zero & size,
      Radius.circular(radius),
    ).deflate(_width / 2);

    // 늘 있는 선. 빛이 지나가지 않는 동안에도 모양이 서 있어야 한다.
    canvas.drawRRect(
      rrect,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = _width
        ..color = Colors.white.withValues(alpha: 0.10),
    );

    final anim = progress;
    if (anim == null) return; // 도는 빛 없이 옅은 선만 남긴다.
    final t = (anim.value + phase) % 1.0;
    final shader = SweepGradient(
      colors: const [
        Color(0x00FFFFFF),
        Color(0x00FFFFFF),
        Color(0xE6FFFFFF),
        Color(0x00FFFFFF),
        Color(0x00FFFFFF),
      ],
      // 밝은 구간이 좁아야 "한 점이 지나간다"로 읽힌다.
      stops: const [0, 0.42, 0.5, 0.58, 1],
      transform: GradientRotation(t * 2 * pi),
    ).createShader(Offset.zero & size);

    canvas.drawRRect(
      rrect,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = _width
        ..shader = shader,
    );
  }

  @override
  bool shouldRepaint(_TravelingEdge old) =>
      old.phase != phase || old.radius != radius;
}
