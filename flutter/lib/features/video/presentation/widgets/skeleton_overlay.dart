import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../data/models/skeleton.dart';
import 'skeleton_shapes.dart';

/// 영상 위에 **관절을 겹쳐 그린다** (2026-09-25 사용자 요청: 「관절 붙여줘」).
///
/// 🔴 **기기에서 관절을 뽑지 않는다.** 웹 화면은 브라우저에서 MoveNet 을
/// 실시간으로 돌리지만, 그쪽은 tfjs·canvas·`<video>` seek 에 매여 있어 앱으로
/// 옮길 수 없다 — 대신 **서버가 이미 낸 값**을 받아 그린다(계약 3-14절).
///
/// 🔴 **모양 규칙은 여기 없다 — `skeleton_shapes.dart` 한 벌이다.**
/// 비교 카드가 같은 모양을 그려야 해서 2026-09-25 에 그리로 옮겼다. 이 파일은
/// **좌표계와 색**만 맡는다(영상 칸 크기로 0~1 좌표를 편다).
class SkeletonOverlay extends StatelessWidget {
  const SkeletonOverlay({
    super.key,
    required this.skeleton,
    required this.position,
    this.color = _kAccent,
    this.showBox = true,
    this.showJoints = true,
  });

  final Skeleton skeleton;

  /// 지금 재생 위치 — 여기서 프레임을 고른다.
  final Duration position;

  final Color color;

  /// 사람을 두르는 네모와 「LIVE TRACKING」 딱지.
  final bool showBox;

  /// 관절 자리의 **흰 고리**.
  ///
  /// 🔴 **작은 칸에서는 끈다**(2026-09-25 사용자 요청). 고리가 흰 7px 고정이라
  /// 영상 칸이 반으로 줄어든 비교 화면에서는 **뼈대 자체를 덮는다.**
  /// 세 순간 카드는 켠 채로 둔다 — 거기서는 자세를 읽는 데 도움이 된다.
  final bool showJoints;

  @override
  Widget build(BuildContext context) {
    final frame = skeleton.at(position);
    // 🔴 못 잡은 프레임은 **아무것도 안 그린다** — 앞 프레임을 이어 그리면
    //    사람이 없는 자리에 뼈대가 남아 더 이상하다.
    if (frame == null) return const SizedBox.shrink();
    return CustomPaint(
      painter: _SkeletonPainter(
        frame: frame,
        names: skeleton.keypointNames,
        swingLeg: skeleton.swingLeg,
        color: color,
        showBox: showBox,
        showJoints: showJoints,
      ),
    );
  }
}

/// 웹의 `--ss-accent` 와 같은 자리 — 밝은 초록.
const Color _kAccent = Color(0xFF57E389);

/// 이 값보다 확신이 낮은 관절은 **안 그린다.**
///
/// 🔴 **0 으로 내리지 말 것** — 못 잡은 관절이 화면 구석에 찍히면서 팔다리가
/// 엉뚱한 곳으로 뻗는다.
const double _kMinConfidence = 0.3;

class _SkeletonPainter extends CustomPainter {
  const _SkeletonPainter({
    required this.frame,
    required this.names,
    required this.color,
    required this.showBox,
    required this.showJoints,
    this.swingLeg,
  });

  final List<List<double>> frame;
  final List<String> names;
  final Color color;
  final bool showBox;
  final bool showJoints;
  final String? swingLeg;

  Offset? _at(String name, Size size) {
    final i = names.indexOf(name);
    if (i < 0 || i >= frame.length) return null;
    final kp = frame[i];
    if (kp.length < 3 || kp[2] < _kMinConfidence) return null;
    /* 🔴 **0~1 을 벗어나도 자르지 않는다**(계약). 화면 밖으로 나간 관절이
       실제로 있고, 자르면 **발이 가장자리에 붙은 것처럼** 그려진다. */
    return Offset(kp[0] * size.width, kp[1] * size.height);
  }

  @override
  void paint(Canvas canvas, Size size) {
    // 🔴 모양은 공용 한 벌이 짠다 — 여기서는 좌표계만 물린다.
    final shapes = buildSkeletonShapes(
      (name) => _at(name, size),
      swingLeg: swingLeg,
    );

    if (showBox) _paintBox(canvas, size, _stroke);

    paintSkeleton(canvas, shapes, color: color, joints: showJoints);
  }

  static Paint _stroke(double w, Color c) => Paint()
    ..style = PaintingStyle.stroke
    ..strokeWidth = w
    ..strokeCap = StrokeCap.round
    ..strokeJoin = StrokeJoin.round
    ..color = c;

  /// 사람을 두르는 네모와 딱지 — 웹 `.ss-shot-track-box` 자리.
  ///
  /// 🔴 **서버가 네모를 주지 않는다** — 보이는 관절의 최소·최대에서 만든다.
  /// 그래서 관절이 몇 개 안 잡히면 네모도 작아진다(그게 정직한 그림이다).
  void _paintBox(Canvas canvas, Size size, Paint Function(double, Color) stroke) {
    double? l, t, r2, b;
    for (final name in names) {
      final p = _at(name, size);
      if (p == null) continue;
      l = l == null ? p.dx : math.min(l, p.dx);
      r2 = r2 == null ? p.dx : math.max(r2, p.dx);
      t = t == null ? p.dy : math.min(t, p.dy);
      b = b == null ? p.dy : math.max(b, p.dy);
    }
    if (l == null || t == null || r2 == null || b == null) return;
    // 사람을 넉넉히 감싼다 — 딱 붙이면 머리 원과 발끝이 선에 물린다.
    final padX = size.width * 0.03 + 8;
    final padY = size.height * 0.04 + 8;
    final box = Rect.fromLTRB(l - padX, t - padY, r2 + padX, b + padY);
    canvas
      ..drawRect(box, stroke(2.6, kSkeletonHalo))
      ..drawRect(box, stroke(1.6, color));

    // 「LIVE TRACKING」 딱지 — 네모 왼쪽 위에 걸친다.
    const label = 'LIVE TRACKING';
    final tp = TextPainter(
      text: const TextSpan(
        text: label,
        style: TextStyle(
          color: Color(0xFF07230F),
          fontSize: 9,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.6,
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    const dot = 4.0;
    final pillW = tp.width + 22 + dot;
    final pill = Rect.fromLTWH(box.left, box.top - 17, pillW, 15);
    // 위가 잘리면 네모 **안쪽**으로 내린다.
    final shifted = pill.top < 0 ? pill.shift(const Offset(0, 19)) : pill;
    canvas.drawRRect(
      RRect.fromRectAndRadius(shifted, const Radius.circular(7.5)),
      Paint()..color = color,
    );
    canvas.drawCircle(
      Offset(shifted.left + 8, shifted.center.dy),
      dot,
      Paint()..color = const Color(0xFFE5484D),
    );
    tp.paint(canvas, Offset(shifted.left + 14, shifted.center.dy - tp.height / 2));
  }

  @override
  bool shouldRepaint(_SkeletonPainter old) =>
      old.frame != frame ||
      old.color != color ||
      old.names != names ||
      old.swingLeg != swingLeg ||
      old.showBox != showBox ||
      old.showJoints != showJoints;
}
