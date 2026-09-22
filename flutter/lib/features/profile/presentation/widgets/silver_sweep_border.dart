import 'dart:math' as math;

import 'package:flutter/material.dart';

/// 테두리를 따라 **밝은 실버가 한 바퀴 돌아다니는** 틀
/// (2026-09-22, 사용자 요청: 「그 내 영상 판만 외곽선으로 세련된 밝은 실버
/// 색상이 돌아다니게」).
///
/// 🔴 **「내 영상」 판 하나만 쓴다.** 여럿에 붙이면 서로 다른 박자로 돌아 화면이
/// 산만해지고, 「여기를 보라」는 뜻이 사라진다 — 이 판이 프로필에서 유일하게
/// 다른 화면으로 밀고 들어가는 입구라서 붙인 것이다.
///
/// 🔴 **선이 흐르는 것이지 판이 빛나는 것이 아니다.** `BoxShadow` 로 번지게
/// 하면 판 둘레에 흐린 띠가 생기고, 그 띠가 목록이 구를 때 프레임마다 달라져
/// **흰 직선**으로 보인다(이 화면이 오늘 내내 겪은 그것). 여기서는 **획
/// 하나**만 그린다.
class SilverSweepBorder extends StatefulWidget {
  const SilverSweepBorder({
    super.key,
    required this.child,
    required this.radius,
    this.period = const Duration(seconds: 6),
  });

  final Widget child;
  final double radius;

  /// 한 바퀴 도는 시간.
  ///
  /// 🔴 **배경 연기(96초)와 다르게 빠르다.** 저쪽은 알아채지 못해야 하는
  /// 배경이고, 이쪽은 **알아채라고** 있는 표시다.
  final Duration period;

  @override
  State<SilverSweepBorder> createState() => _SilverSweepBorderState();
}

class _SilverSweepBorderState extends State<SilverSweepBorder>
    with SingleTickerProviderStateMixin {
  late final AnimationController _spin = AnimationController(
    vsync: this,
    duration: widget.period,
  )..repeat();

  @override
  void dispose() {
    _spin.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    /* 🔴 **「애니메이션 줄이기」를 켠 사람에게는 안 돈다** — 멈춘 실버 테가
       남는다(선 자체를 지우면 그 사람에게는 판의 경계가 사라진다). */
    final still = MediaQuery.disableAnimationsOf(context);

    return AnimatedBuilder(
      animation: _spin,
      /* 🔴 **자식을 다시 안 짓는다.** 매 프레임 도는 애니메이션이라 자식을
         builder 안에 두면 판 내용이 초당 60번 다시 지어진다. */
      child: widget.child,
      builder: (context, child) => CustomPaint(
        foregroundPainter: _SweepPainter(
          radius: widget.radius,
          turn: still ? 0.25 : _spin.value,
        ),
        child: child,
      ),
    );
  }
}

class _SweepPainter extends CustomPainter {
  const _SweepPainter({required this.radius, required this.turn});

  final double radius;

  /// 0~1 이 한 바퀴.
  final double turn;

  /// 밝은 실버 — 순백보다 한 끗 차갑다. 순백은 어두운 화면에서 형광등처럼
  /// 튀고, 「세련된」과는 반대쪽이다.
  static const Color _silver = Color(0xFFE8F0F4);

  /// 가만히 있는 바닥 선 — 도는 빛이 지나가지 않는 동안에도 판의 경계는
  /// 있어야 한다. 🔴 **없으면 빛이 없는 쪽 모서리가 통째로 사라진다.**
  static const Color _base = Color(0x33C9D4D8);

  /// 빛나는 토막이 차지하는 **테두리 길이의 몫**.
  ///
  /// 🔴 **각도가 아니라 길이다**(2026-09-22 정정, 사용자 요청: 「길이 바뀌지
  /// 않게 … 가로에서 길이 줄어들지 않고 그 길이 그대로」).
  ///
  /// ⚠️ **앞서 여기 「각도로 쓸면 한결같다」고 적어 둔 것은 틀렸다.**
  /// `SweepGradient` 는 가운데에서 본 **각도**로 색을 나누는데, 둥근 사각형은
  /// 가운데에서 변까지의 거리가 자리마다 달라서 **같은 각도가 긴 변에서는 긴
  /// 토막, 짧은 변에서는 짧은 토막**이 된다 — 빛이 길어졌다 짧아졌다 했다.
  /// 테두리를 **길이로** 재면 어디서나 같은 토막이고 속도도 일정하다.
  static const double _bandFraction = 0.15;

  /// 토막을 몇 조각으로 나눠 그리는가 — 조각마다 알파가 달라 **머리와 꼬리가
  /// 부드럽게 사라진다.**
  ///
  /// 🔴 **28 → 72 로 늘렸다**(2026-09-22, 사용자 지적: 「앞 뒤로 잘려있는
  /// 프레임들이 너무 잘 보여서 부자연스러워」). 조각이 적으면 이웃한 알파
  /// 차이가 커서 **토막이 몇 개의 도막으로 쪼개져 보인다.**
  static const int _segments = 72;

  @override
  void paint(Canvas canvas, Size size) {
    // 획이 상자 안쪽으로만 그려지게 반 굵기만큼 줄인다 — 안 줄이면 바깥
    // 절반이 잘려 **선이 반쪽만 보인다.**
    const w = 1.5;
    final rect = Rect.fromLTWH(0, 0, size.width, size.height).deflate(w / 2);
    final rrect = RRect.fromRectAndRadius(rect, Radius.circular(radius));

    /* 🔴 **둥근 끝(`StrokeCap.round`)을 쓰지 않는다**(2026-09-22 정정).
       조각마다 끝을 둥글게 하면 이웃 조각과 **겹치는 자리가 두 번 칠해져**
       알파가 도드라지고, 그 마디가 「잘린 프레임」으로 보인다. 맞대는 끝
       (`butt`)은 조각끼리 정확히 이어져 마디가 안 생긴다. */
    final stroke = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = w
      ..strokeCap = StrokeCap.butt;

    canvas.drawRRect(rrect, Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = w
      ..color = _base);

    final path = Path()..addRRect(rrect);
    final metrics = path.computeMetrics().toList();
    if (metrics.isEmpty) return;
    final metric = metrics.first;
    final len = metric.length;
    if (len <= 0) return;

    final bandLen = len * _bandFraction;
    final head = turn * len;

    for (var i = 0; i < _segments; i += 1) {
      final u0 = i / _segments;
      final u1 = (i + 1) / _segments;
      // 🔴 **머리·꼬리에서 0 이 되는 곡선.** 양 끝이 0 이라야 토막이 툭
      //    나타났다 사라지지 않는다.
      /* 🔴 **`sin²` 이다**(2026-09-22 정정). 그냥 `sin` 은 양 끝에서 기울기가
         남아 **머리와 꼬리가 툭 잘린 것처럼** 보인다 — 제곱하면 끝에서
         기울기가 0 이 되어 스르르 사라진다. */
      final sn = math.sin(math.pi * (u0 + u1) / 2);
      final a = sn * sn;
      if (a <= 0.01) continue;

      var t0 = (head + bandLen * u0) % len;
      var t1 = (head + bandLen * u1) % len;
      stroke.color = _silver.withValues(alpha: a);
      if (t1 >= t0) {
        canvas.drawPath(metric.extractPath(t0, t1), stroke);
      } else {
        // 🔴 **한 바퀴를 넘어가는 조각은 둘로 쪼갠다** — 안 쪼개면 그 조각만
        //    테두리를 거꾸로 가로질러 **대각선**이 그어진다.
        canvas.drawPath(metric.extractPath(t0, len), stroke);
        canvas.drawPath(metric.extractPath(0, t1), stroke);
      }
    }
  }

  @override
  bool shouldRepaint(_SweepPainter old) =>
      old.turn != turn || old.radius != radius;
}
