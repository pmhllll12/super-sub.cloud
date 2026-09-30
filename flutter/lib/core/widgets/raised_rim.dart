import 'dart:ui' as ui;

import 'package:flutter/material.dart';

/// **떠오른 테** — 테두리가 위로 솟은 것처럼 보이게 하는 획 한 줄
/// (2026-09-24 사용자 요청 + 레퍼런스: 「외곽선이 입체적이게 위로 올라와있는
/// 느낌, 그리고 모서리 두 곳은 자연스럽게 안보이고」).
///
/// 🔴 **대각선으로 밝기를 나눈 것이 전부다.** 왼쪽 위에서 해가 든다는 이
/// 저장소의 규칙(`glass_pill.dart` 의 `kSunShadow`)을 그대로 따라, 획을
/// **왼쪽 위 → 오른쪽 아래** 방향의 그러데이션으로 칠한다. 그러면
///
/// - **왼쪽 위 모서리**가 가장 밝고(빛을 받는 쪽),
/// - **오른쪽 아래 모서리**는 옅게 남고(돌아 들어온 빛),
/// - 그 사이인 **오른쪽 위·왼쪽 아래 모서리 둘이 0 이 되어 사라진다.**
///
/// 🔴 **가운데 정지점(0.5)을 투명으로 두는 것이 「모서리 둘이 사라진다」의
/// 전부다.** 지우면 테가 네 변을 고르게 둘러 **판에 그려 넣은 네모**가 된다.
///
/// 🔴 **모서리가 있는 모양에만 쓴다.** [StadiumBorder] 처럼 양 끝이 완전한
/// 반원이면 「사라지는 두 모서리」가 어디인지 눈이 못 집어서, 그냥 **한쪽만
/// 밝은 테**로 보인다.
///
/// ⚠️ **[SilverSweepBorder] 와 다른 것이다.** 저쪽은 **도는** 빛이라 「여기를
/// 보라」는 표시이고, 이것은 **가만히 있는** 재질 표현이다. 여럿에 달아도
/// 산만해지지 않는 것이 그 차이다 — 저쪽은 「한 화면에 하나」가 규칙이다.
class RaisedRim extends StatelessWidget {
  const RaisedRim({
    super.key,
    required this.child,
    required this.radius,
    this.lit = 0.72,
    this.shade = 0.3,
    this.width = 1,
    this.litColor = _silver,
    this.shadeColor = _silver,
  });

  final Widget child;

  /// 감싸는 모양의 모서리 반지름 — **감싸는 쪽과 같은 값이어야 한다.**
  /// 다르면 획이 모양에서 어긋나 두 겹으로 보인다.
  final double radius;

  /// 빛을 받는 쪽(왼쪽 위)의 진하기 0~1.
  final double lit;

  /// 그늘 쪽(오른쪽 아래)의 진하기 0~1. 🔴 **0 으로 두지 말 것** — 그러면
  /// 테가 반쪽만 남아 「솟았다」가 아니라 「빛이 스쳤다」로 보인다.
  final double shade;

  final double width;

  /// 빛을 받는 쪽의 색. 안 주면 한 끗 차가운 실버.
  final Color litColor;

  /// 그늘 쪽의 색. 안 주면 [litColor] 와 같은 실버 — **어두운 바탕**에서는
  /// 그것이 맞다(빛이 돌아 들어온 것으로 읽힌다).
  ///
  /// 🔴 **밝은 바탕에서는 여기에 어두운 색을 준다.** 밝은 판 위에 밝은 조각이
  /// 놓이면 실버 획이 양쪽 다 묻혀 **모양 자체가 안 읽힌다** — 그때는
  /// 「왼쪽 위 흰 하이라이트 + 오른쪽 아래 어두운 그림자」가 솟아 보이게 하는
  /// 유일한 조합이고, 이 위젯은 **획 하나로** 그 둘을 낸다(가운데가 투명이라
  /// 한 그러데이션 안에서 색이 갈려도 이어져 보인다).
  final Color shadeColor;

  @override
  Widget build(BuildContext context) => CustomPaint(
    foregroundPainter: _RaisedRimPainter(
      radius: radius,
      lit: lit,
      shade: shade,
      width: width,
      litColor: litColor,
      shadeColor: shadeColor,
    ),
    child: child,
  );

  /// 🔴 **순백을 안 쓴다** — 가는 획에서 순백은 형광등처럼 튄다
  /// (`silver_sweep_border.dart` 가 같은 이유로 한 끗 차가운 실버를 쓴다).
  static const Color _silver = Color(0xFFE8F0F4);
}

class _RaisedRimPainter extends CustomPainter {
  const _RaisedRimPainter({
    required this.radius,
    required this.lit,
    required this.shade,
    required this.width,
    required this.litColor,
    required this.shadeColor,
  });

  final double radius;
  final double lit;
  final double shade;
  final double width;
  final Color litColor;
  final Color shadeColor;

  @override
  void paint(Canvas canvas, Size size) {
    // 획이 상자 안쪽으로만 그려지게 반 굵기를 줄인다 — 안 줄이면 바깥 절반이
    // 잘려 **선이 반쪽만** 보인다.
    final r = (Offset.zero & size).deflate(width / 2);
    if (r.isEmpty) return;

    canvas.drawRRect(
      RRect.fromRectAndRadius(r, Radius.circular(radius)),
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = width
        ..shader = ui.Gradient.linear(
          r.topLeft,
          r.bottomRight,
          [
            litColor.withValues(alpha: lit),
            /* 🔴 **가운데 두 정지점이 모두 투명이다.** 한 점만 두면 두 색이
               그 한 점에서 맞부딪혀 **색이 섞이는 띠**가 보인다 — 투명 구간을
               짧게 벌려 두면 양쪽이 각자 0 으로 내려가 모서리에서 깨끗이
               사라진다. */
            litColor.withValues(alpha: 0),
            shadeColor.withValues(alpha: 0),
            shadeColor.withValues(alpha: shade),
          ],
          const [0.0, 0.42, 0.58, 1.0],
        ),
    );
  }

  @override
  bool shouldRepaint(_RaisedRimPainter old) =>
      old.radius != radius ||
      old.lit != lit ||
      old.shade != shade ||
      old.width != width ||
      old.litColor != litColor ||
      old.shadeColor != shadeColor;
}
