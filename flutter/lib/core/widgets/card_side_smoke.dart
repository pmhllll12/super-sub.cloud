import 'dart:math' as math;

import 'package:flutter/material.dart';

/// 카드 **둘레를 한 바퀴** 아주 천천히 흐르는 연기 — 색 둘은 **그 카드의
/// 바탕색과 자국색**이다(2026-09-22, 사용자 요청: 「딱 2가지만 은은하게
/// 퍼지게 … 아주 천천히 부드럽게 연기처럼 흘러가게」).
///
/// ⚠️ 처음엔 **양옆에만** 뒀는데 카드 위아래가 비어 **양옆에 세운 두 기둥**
/// 처럼 보였다 — 사용자 정정으로 둘레 전체가 됐다(「카드 주위 전체적으로」).
///
/// 🔴 **전면 빛무리(`AuroraBackground`)와 다른 물건이다.** 그쪽은 화면 전체를
/// 물들이다가 동심원 띠가 보여 꺼졌고(`kAuroraGlow = false`), 이것은 **카드
/// 둘레에만** 산다. 같은 것을 되살린 것이 아니므로 그 스위치와 무관하게 돈다.
///
/// 🔴 **두 곳이 쓴다**(2026-09-22): 프로필의 카드 둘레와, 홈의 스쿼드 판
/// 안쪽이다. 그래서 `features/profile` 이 아니라 `core/widgets` 에 산다.
/// 홈은 [cardWidth] 를 **0** 으로 줘서 가운데를 비우지 않는다 — 비울 카드가
/// 없고 판 전체에 퍼져야 하기 때문이다.
///
/// 🔴 **카드가 연기를 가린다 — 그것이 설계다.** 카드는 불투명이라 뒤로 지나는
/// 연기는 안 보이고, **카드 밖으로 삐져나온 부분만** 보인다. 그래서 위·아래
/// 덩이도 카드를 가로질러 놓아도 된다.
class CardSideSmoke extends StatefulWidget {
  const CardSideSmoke({
    super.key,
    required this.colors,
    required this.cardWidth,
  });

  /// 퍼질 색 **둘뿐이다** — `a` 는 카드 바탕색, `b` 는 자국색.
  ///
  /// ⚠️ **바탕색이 검정인 카드는 한 색만 보인다.** 검은 연기는 검은 화면에서
  /// 안 보이기 때문인데, 이건 결함이 아니라 「카드 색을 쓴다」의 결과다.
  final ({Color a, Color b}) colors;

  /// 가운데를 비워 둘 폭 — 카드가 앉는 자리다. **0 이면 안 비운다**(홈).
  ///
  /// 🔴 **높이는 안 받는다** — 부모가 준 자리를 그대로 채운다(`Positioned` 가
  /// 카드보다 위아래로 넉넉히 잡아 준다). 여기서 따로 높이를 정하면 그 값과
  /// 부모의 자리가 **어긋날 때 잘린 자리가 가로선**으로 드러난다.
  final double cardWidth;

  /// 한 바퀴 도는 시간.
  ///
  /// 🔴 **아주 길다**(사용자 요청: 「아주 천천히」). 짧으면 옆에서 무언가
  /// 움직이는 것이 눈에 잡혀 **카드에서 눈이 끌려간다** — 배경은 보고 있지
  /// 않을 때만 움직여야 한다.
  static const Duration period = Duration(seconds: 96);

  @override
  State<CardSideSmoke> createState() => _CardSideSmokeState();
}

class _CardSideSmokeState extends State<CardSideSmoke>
    with SingleTickerProviderStateMixin {
  late final AnimationController _drift = AnimationController(
    vsync: this,
    duration: CardSideSmoke.period,
  )..repeat();

  @override
  void dispose() {
    _drift.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    /* 🔴 **「애니메이션 줄이기」를 켠 사람에게는 멈춰 선다** — 전면 빛무리와
       같은 판단이다. 움직이는 배경은 어지럼증을 일으킬 수 있고 운영체제가 그
       뜻을 이미 받아 뒀다. 그때도 **연기는 그린다**(위상만 0 으로 고정) —
       안 그리면 카드 둘레가 갑자기 허전해진다. */
    final still = MediaQuery.disableAnimationsOf(context);

    /* 🔴 **색이 바뀔 때 부드럽게 건너간다** — 카드 색을 고치고 돌아오면 툭
       갈리는 대신 스며든다. `TweenAnimationBuilder` 는 `end` 가 바뀌면
       **그리고 있던 값에서** 새 목표로 이어 준다(직접 0→1 을 감으면 두 번째
       변경에서 기본색으로 한 번 튕긴다). */
    return IgnorePointer(
      child: SizedBox.expand(
        child: TweenAnimationBuilder<Color?>(
          tween: ColorTween(end: widget.colors.a),
          duration: const Duration(milliseconds: 1200),
          curve: Curves.easeInOut,
          builder: (context, a, _) => TweenAnimationBuilder<Color?>(
            tween: ColorTween(end: widget.colors.b),
            duration: const Duration(milliseconds: 1200),
            curve: Curves.easeInOut,
            builder: (context, b, _) => AnimatedBuilder(
              animation: _drift,
              builder: (context, _) => CustomPaint(
                painter: _SmokePainter(
                  a: a ?? widget.colors.a,
                  b: b ?? widget.colors.b,
                  cardWidth: widget.cardWidth,
                  phase: still ? 0 : _drift.value,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// 연기 한 덩이 — 좌우 띠 **안에서의** 비율 좌표다.
class _Blob {
  const _Blob(this.side, this.useB, this.x, this.y, this.radius, this.alpha);

  /// -1 이면 왼쪽 띠, 1 이면 오른쪽 띠, **0 이면 화면 폭 전체**(카드 위·아래).
  final int side;

  /// 참이면 자국색, 거짓이면 카드 바탕색.
  final bool useB;

  /// 제 띠 안에서의 자리(0~1)와, 띠 높이 대비 세로 자리(0~1).
  final double x;
  final double y;

  /// 띠 높이 대비 반경.
  final double radius;
  final double alpha;
}

class _SmokePainter extends CustomPainter {
  const _SmokePainter({
    required this.a,
    required this.b,
    required this.cardWidth,
    required this.phase,
  });

  final Color a;
  final Color b;
  final double cardWidth;
  final double phase;

  /// 🔴 **여섯을 넘기지 않는다** — 겹칠수록 두 색이 섞여 탁한 제3의 색이 된다.
  /// 두 색만 쓰기로 한 요청이 그때 깨진다.
  ///
  /// 🔴 **카드 둘레를 한 바퀴 두른다**(2026-09-22 정정, 사용자 요청:
  /// 「카드 주위 전체적으로」). 처음엔 좌우 띠 안에만 뒀더니 카드 **위아래가
  /// 비어** 연기가 아니라 양옆에 세운 두 기둥처럼 보였다. 이제 위·아래 몫이
  /// 따로 있고, 그것들은 **카드 폭을 가로질러** 놓인다.
  /// 🔴 **두 번 올렸다**(2026-09-22, 사용자 요청: 「더 잘 보이게」 →
  /// 「훨씬 밝게」). 0.18~0.30 → 0.34 → **0.55~0.82**. 「은은하게」와
  /// 어긋나 보이지만, 아래 [_fade] 가 **흰 선 쪽으로 갈수록 빠르게 걷어
  /// 내므로** 짙은 것은 카드를 감싸는 자리뿐이다.
  static const _blobs = [
    // 왼쪽 띠.
    _Blob(-1, false, 0.42, 0.26, 0.54, 0.82),
    _Blob(-1, true, 0.28, 0.66, 0.48, 0.72),
    // 오른쪽 띠.
    _Blob(1, true, 0.58, 0.32, 0.52, 0.82),
    _Blob(1, false, 0.72, 0.72, 0.46, 0.72),
    // 카드 위·아래 — 가로로는 카드까지 걸치고 세로로는 밖으로 빠진다.
    _Blob(0, true, 0.34, 0.05, 0.40, 0.62),
    _Blob(0, false, 0.68, 0.94, 0.44, 0.55),
  ];


  /// 세로 자리에 따른 세기 — 🔴 **위가 짙고 아래로 갈수록 걷힌다**
  /// (2026-09-22, 사용자 요청: 「그 흰색 선 위로는 훨씬 밝게」).
  ///
  /// 연기 상자의 아래쪽 끝은 닉네임을 지나 **흰 선에 닿는다.** 그 언저리까지
  /// 같은 세기로 깔면 선이 연기에 묻혀 **가르는 일을 못 한다** — 선 쪽으로
  /// 갈수록 빠르게 옅어지게 해서 위쪽만 짙게 남긴다.
  ///
  /// 🔴 **0 까지 내린다**(맨 아래). 여기서 안 내리면 상자 끝에서 값이 남아
  /// **가로선**으로 드러난다.
  ///
  /// ⚠️ **한 번 「두 색으로 꽉 채우기」로 갔다가 되돌렸다**(2026-09-22,
  /// 사용자: 「방금 바꾸기 전으로 되돌려」). 검정을 안 보이게 하려고 바닥을
  /// 불투명으로 깔았었는데 **되돌린 쪽이 맞다** — 다시 채우지 말 것.
  static double _fade(double y) {
    if (y <= 0.58) return 1.0;
    final t = ((y - 0.58) / 0.42).clamp(0.0, 1.0);
    // 끝에서 기울기가 0 이 되게 — 툭 끊기지 않는다.
    return (1 - t) * (1 - t);
  }

  /// 덩이마다 다른 **흔들림 배수와 어긋난 출발점**.
  ///
  /// 🔴 **배수가 정수다.** 소수로 두면 한 바퀴가 끝나는 지점에서 값이 제자리로
  /// 안 돌아와 **화면이 툭 튄다.** 정수 배수 + 서로 다른 출발점이면 이음매
  /// 없이 돌면서도 규칙이 안 읽힌다(전면 빛무리에서 배운 것을 그대로 쓴다).
  static const _wobble = [
    // (가로 배수, 세로 배수, 밝기 배수, 출발점)
    (1, 2, 1, 0.00),
    (2, 1, 2, 1.70),
    (1, 3, 1, 3.10),
    (3, 2, 2, 4.60),
    (2, 3, 1, 2.35),
    (1, 1, 2, 5.20),
  ];

  /// 떠다니는 폭 — 제 띠 대비. 🔴 **작게 둔다.** 크면 덩이가 띠 밖으로 나가
  /// 잘린 자리가 **직선**으로 드러난다(이 화면이 오늘 내내 쫓던 그 증상이다).
  static const _amp = 0.12;

  /// 옅어지는 바닥 — 🔴 **0 까지 안 내린다.** 완전히 꺼졌다 켜지면 연기가
  /// 흐르는 것이 아니라 **깜빡이는** 것으로 보인다.
  static const _dim = 0.45;

  @override
  void paint(Canvas canvas, Size size) {
    // 카드가 가운데를 차지하고 남는 한쪽 폭. 좁으면 그릴 자리가 없다.
    final sideW = (size.width - cardWidth) / 2;
    if (sideW <= 8) return;

    final w = phase * 2 * math.pi;

    for (var i = 0; i < _blobs.length; i += 1) {
      final g = _blobs[i];
      final d = _wobble[i % _wobble.length];

      final dx = phase == 0 ? 0.0 : _amp * math.sin(w * d.$1 + d.$4);
      final dy = phase == 0 ? 0.0 : _amp * math.cos(w * d.$2 + d.$4);
      final breath =
          phase == 0 ? 1.0 : 0.5 + 0.5 * math.sin(w * d.$3 + d.$4);
      final alpha =
          g.alpha * (_dim + (1 - _dim) * breath) * _fade(g.y + dy);

      /* 자리를 정하는 띠는 셋이다.
         · -1 — 왼쪽(0..sideW) · 1 — 오른쪽(width-sideW..width)
         · 0 — 🔴 **화면 폭 전체.** 카드 위·아래 몫이라 카드를 가로질러야
           한다. 카드는 불투명이라 겹치는 부분은 어차피 가려지고, 보이는
           것은 카드 위아래로 삐져나온 부분뿐이다. */
      final bandLeft = switch (g.side) {
        < 0 => 0.0,
        > 0 => size.width - sideW,
        _ => 0.0,
      };
      final bandW = g.side == 0 ? size.width : sideW;
      final center = Offset(
        bandLeft + (g.x + dx) * bandW,
        (g.y + dy) * size.height,
      );
      final r = size.height * g.radius;
      final color = g.useB ? b : a;

      canvas.drawCircle(
        center,
        r,
        Paint()
          ..shader = RadialGradient(
            /* 🔴 **곧게 떨어뜨리지 않는다.** 가운데에서 가장자리까지 일정하게
               옅어지면 색이 256단이라 같은 폭마다 한 단씩 끊기고, 그 경계가
               **동심원 띠**로 보인다(전면 빛무리가 그것 때문에 꺼졌다).
               종 모양으로 떨어뜨리면 변화가 가운데에 몰리고 바깥은 거의
               평평해져, 띠가 생길 만한 바깥에서 한 단 차이가 날 일이 없다. */
            colors: [
              for (final k in const [1.0, 0.880, 0.599, 0.306, 0.102, 0.0])
                // 🔴 같은 색의 **투명**으로 끝낸다. 흰·검정으로 끝내면
                //    가장자리에 테가 생겨 원이 드러난다.
                color.withValues(alpha: alpha * k),
            ],
            stops: const [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
          ).createShader(Rect.fromCircle(center: center, radius: r)),
      );
    }
  }

  @override
  bool shouldRepaint(_SmokePainter old) =>
      old.phase != phase ||
      old.a != a ||
      old.b != b ||
      old.cardWidth != cardWidth;
}
