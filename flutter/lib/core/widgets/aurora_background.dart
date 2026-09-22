import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// 화면 바탕에 깔리는 **빛무리** — 어두운 바탕 위로 민트빛이 몽환적으로 번진다.
///
/// 🔴 **`ImageFilter.blur` 를 쓰지 않는다.** 방사형 그라데이션은 가장자리가
/// 이미 부드럽게 사라져서 **블러 없이도 뭉개진 빛으로 보인다.** 블러는 매
/// 프레임 화면 전체를 다시 그려 GPU 를 먹는데, 얻는 것이 거의 없다.
/// (같은 이유로 `BackdropFilter` 도 안 쓴다 — 그건 **뒤가 비쳐야 하는** 유리
/// 카드의 몫이다.)
///
/// 🔴 **색은 브랜드 민트에서 나온다**(`AppTheme.seed`). 레퍼런스는 마젠타·퍼플
/// 계열이었지만 그대로 쓰면 **웹과 앱이 갈린다** — 토큰의 원본이 이 폴더이고,
/// 버튼·알약·선택 표시가 전부 민트를 쓰고 있다(사용자 판단, 2026-09-21).
///
/// 🔴 **선수 카드는 이 위에서도 제 색을 지킨다**(연두 바탕). 카드는 밖으로
/// 공유되는 물건이라 어디에 놓여도 같은 얼굴이어야 한다.
class AuroraBackground extends StatelessWidget {
  const AuroraBackground({
    super.key,
    required this.child,
    this.base = const Color(0xFF0A0F0C),
    this.tint,
  });

  final Widget child;

  /// 빛무리 아래에 깔리는 바탕.
  final Color base;

  /// **두 색으로 갈아 끼운다** — 내 프로필이 카드의 바탕색·자국색을 여기 넣는다
  /// (2026-09-22, 사용자 요청). `null` 이면 브랜드 민트 그대로다.
  ///
  /// 🔴 **자리와 알파는 안 바꾼다** — 색만 갈린다. 배치까지 갈리면 화면마다
  /// 다른 그림이 되어 「같은 앱」으로 안 읽힌다.
  final ({Color a, Color b})? tint;

  @override
  Widget build(BuildContext context) {
    final painter = _AuroraPainter(tint: tint);
    return ColoredBox(
      color: base,
      child: Stack(
        fit: StackFit.expand,
        children: [
          /* 🔴 **다시 그리지 않는다.** 빛무리는 움직이지 않으므로 위에서 무엇이
             바뀌든 다시 칠할 이유가 없다 — `RepaintBoundary` 가 그것을 층으로
             떼어 낸다. (색이 갈릴 때는 `shouldRepaint` 가 참을 돌려준다.) */
          RepaintBoundary(child: CustomPaint(painter: painter)),
          child,
        ],
      ),
    );
  }
}

/// 색 둘이 바뀌면 **부드럽게 건너간다**(2026-09-22, 사용자 요청: 「자연스럽고
/// 부드럽게」). 카드 꾸미기에서 색을 고치고 프로필로 돌아오면 배경이 툭
/// 갈리는 대신 스며들 듯 옮겨 간다.
///
/// 🔴 **`ColorTween` 이 지금 값에서 이어간다** — 직접 `0→1` 을 감으면서 앞
/// 색을 고정값으로 잡으면, 색을 **두 번째로** 바꿀 때 기본색으로 한 번
/// 튕겼다가 간다. `TweenAnimationBuilder` 는 `end` 가 바뀌면 **그리고 있던
/// 값에서** 새 목표로 이어 준다.
///
/// 🔴 **둘이 어긋나지 않는다** — 같은 프레임에 둘 다 새 목표를 받고 길이·
/// 곡선이 같으므로 함께 움직인다.
class AnimatedAuroraBackground extends StatelessWidget {
  const AnimatedAuroraBackground({
    super.key,
    required this.child,
    required this.tint,
    this.base = const Color(0xFF0A0F0C),
    this.duration = const Duration(milliseconds: 1200),
  });

  final Widget child;
  final ({Color a, Color b}) tint;
  final Color base;
  final Duration duration;

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<Color?>(
      tween: ColorTween(end: tint.a),
      duration: duration,
      curve: Curves.easeInOut,
      builder: (context, a, _) => TweenAnimationBuilder<Color?>(
        tween: ColorTween(end: tint.b),
        duration: duration,
        curve: Curves.easeInOut,
        builder: (context, b, _) => AuroraBackground(
          base: base,
          // 첫 프레임엔 아직 `null` 이다 — 그때는 목표 색으로 그린다.
          tint: (a: a ?? tint.a, b: b ?? tint.b),
          child: child,
        ),
      ),
    );
  }
}

/// 아무 색도 안 정한 화면의 색 둘 — 프로필이 **카드가 없을 때** 쓰는 값이다.
/// 아래 `_glows` 의 1·3번과 같은 색이라, 기본 배경과 이어 보인다.
const ({Color a, Color b}) kDefaultAuroraTint =
    (a: AppTheme.seed, b: Color(0xFF1B7A8C));

/// 빛무리 하나 — 화면 비율로 놓는다(기기 크기가 달라도 같은 그림).
class _Glow {
  const _Glow(this.color, this.dx, this.dy, this.radius, this.alpha);

  final Color color;

  /// 화면 폭·높이에 대한 비율(0~1). 🔴 **화면 밖까지 걸치게 둔다** — 원이
  /// 통째로 보이면 「동그라미를 그려 놨다」로 읽히고 번진 빛으로 안 보인다.
  final double dx;
  final double dy;

  /// 짧은 변에 대한 비율.
  final double radius;
  final double alpha;
}

class _AuroraPainter extends CustomPainter {
  const _AuroraPainter({this.tint});

  /// `null` 이면 아래 브랜드 배치 그대로. 있으면 **자리와 알파는 두고 색만**
  /// 두 색으로 번갈아 갈아 끼운다.
  final ({Color a, Color b})? tint;

  /// 실제로 칠할 빛무리들.
  List<_Glow> get _painted {
    final t = tint;
    if (t == null) return _glows;
    /* 🔴 **번갈아 준다** — 한 색을 위 둘, 다른 색을 아래 둘에 몰면 화면이
       위아래로 갈린 띠처럼 보인다. 엇갈리게 놓아야 두 색이 섞인다. */
    return [
      for (var i = 0; i < _glows.length; i += 1)
        _Glow(
          i.isEven ? t.a : t.b,
          _glows[i].dx,
          _glows[i].dy,
          _glows[i].radius,
          _glows[i].alpha,
        ),
    ];
  }

  /// 🔴 **넷을 넘기지 않는다.** 겹칠수록 색이 탁해지고, 화면마다 다른 그림이
  /// 되어 「같은 앱」으로 안 읽힌다.
  ///
  /// 🔴 **알파는 0.35 를 넘기지 않는다**(2026-09-21에 0.68까지 올렸다 되돌렸다).
  /// 판이 거의 투명해진 뒤로는 빛이 화면 **전체**에 퍼지는데, 세게 주면
  /// 「은은하게 비치는」 것이 아니라 **화면이 통째로 초록으로 물든다.**
  static const _glows = [
    // 왼쪽 위 — 브랜드 민트.
    _Glow(AppTheme.seed, 0.06, 0.02, 0.98, 0.34),
    // 오른쪽 위 — 청록으로 한 단계 차갑게.
    _Glow(Color(0xFF2ED3B7), 1.06, 0.14, 0.86, 0.26),
    // 왼쪽 아래 — 진한 청. 아래를 눌러 카드가 떠 보이게 한다.
    _Glow(Color(0xFF1B7A8C), -0.10, 0.88, 0.92, 0.30),
    // 오른쪽 아래 — 민트를 옅게 한 번 더(빛이 감싸는 느낌).
    _Glow(AppTheme.seed, 0.98, 1.04, 0.76, 0.20),
  ];

  @override
  void paint(Canvas canvas, Size size) {
    final short = size.shortestSide;
    for (final g in _painted) {
      final center = Offset(size.width * g.dx, size.height * g.dy);
      final r = short * g.radius;
      canvas.drawCircle(
        center,
        r,
        Paint()
          ..shader = RadialGradient(
            colors: [
              g.color.withValues(alpha: g.alpha),
              // 🔴 같은 색의 **투명**으로 끝낸다. 흰·검정으로 끝내면 가장자리에
              //    테가 생겨 원이 드러난다.
              g.color.withValues(alpha: 0),
            ],
            // 가운데를 조금 평평하게 — 한 점에서 터지는 것이 아니라 번진 빛이다.
            stops: const [0.0, 1.0],
          ).createShader(Rect.fromCircle(center: center, radius: r)),
      );
    }
  }

  /// 🔴 **색이 갈리면 다시 칠한다.** 붙박이로 `false` 를 돌려주던 자리인데,
  /// 색을 받게 되면서 그러면 **프로필 배경이 영영 첫 색에 멈춘다.** 자리·
  /// 알파는 상수라 색만 견주면 된다.
  @override
  bool shouldRepaint(_AuroraPainter oldDelegate) =>
      oldDelegate.tint?.a != tint?.a || oldDelegate.tint?.b != tint?.b;
}
