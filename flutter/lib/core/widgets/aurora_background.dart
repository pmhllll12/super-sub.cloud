import 'dart:math' as math;

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
///
/// 🔴 **바탕은 중성 회색이다**(2026-09-22, 사용자가 레퍼런스로 지정).
/// 전에는 `#0A0F0C`(거의 검정에 초록기)였는데, 빛무리를 뺀 나머지가 **검게
/// 꺼져** 판과 배경이 한 덩어리로 읽혔다. 회색으로 올리면 판의 경계가
/// 살아나고 빛무리는 그 위에 그대로 번진다 — **빛무리 색·자리는 안 건드렸다.**
class AuroraBackground extends StatelessWidget {
  const AuroraBackground({
    super.key,
    required this.child,
    this.base = kAuroraBase,
    this.tint,
    this.phase = 0,
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

  /// **떠다니는 위상**(0~1 이 한 바퀴). 🔴 **기본이 0 이라 안 주면 예전
  /// 그림 그대로다** — 홈은 가만히 있어야 한다(`figure_background.dart` 를
  /// 움직이게 했다 걷어낸 것과 같은 판단).
  final double phase;

  @override
  Widget build(BuildContext context) {
    final painter = _AuroraPainter(tint: tint, phase: phase);
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

/// 색 둘이 바뀌면 **부드럽게 건너가고**, 그 사이에도 빛무리가 **천천히
/// 떠다닌다**(2026-09-22, 사용자 요청: 「자연스럽고 부드럽게」 · 「다양한 곳에서
/// 나왔다 사라졌다」 · 「너무 빠르게 하면 눈 아프니까」).
///
/// 🔴 **`ColorTween` 이 지금 값에서 이어간다** — 직접 `0→1` 을 감으면서 앞
/// 색을 고정값으로 잡으면, 색을 **두 번째로** 바꿀 때 기본색으로 한 번
/// 튕겼다가 간다. `TweenAnimationBuilder` 는 `end` 가 바뀌면 **그리고 있던
/// 값에서** 새 목표로 이어 준다.
///
/// 🔴 **둘이 어긋나지 않는다** — 같은 프레임에 둘 다 새 목표를 받고 길이·
/// 곡선이 같으므로 함께 움직인다.
class AnimatedAuroraBackground extends StatefulWidget {
  const AnimatedAuroraBackground({
    super.key,
    required this.child,
    required this.tint,
    this.base = kAuroraBase,
    this.duration = const Duration(milliseconds: 1200),
    this.driftPeriod = const Duration(seconds: 48),
  });

  final Widget child;
  final ({Color a, Color b}) tint;
  final Color base;

  /// 색이 갈릴 때 건너가는 시간.
  final Duration duration;

  /// 빛무리가 한 바퀴 도는 시간.
  ///
  /// 🔴 **길게 둔다**(사용자 요청: 「너무 빠르게 하면 눈 아프니까」). 짧으면
  /// 배경이 꿈틀거려 **읽고 있는 글에서 눈이 끌려간다** — 배경은 알아채지
  /// 못할 만큼만 움직여야 한다.
  final Duration driftPeriod;

  @override
  State<AnimatedAuroraBackground> createState() =>
      _AnimatedAuroraBackgroundState();
}

class _AnimatedAuroraBackgroundState extends State<AnimatedAuroraBackground>
    with SingleTickerProviderStateMixin {
  late final AnimationController _drift = AnimationController(
    vsync: this,
    duration: widget.driftPeriod,
  );

  @override
  void initState() {
    super.initState();
    /* 🔴 **빛무리를 끈 동안에는 안 돈다.** 그리지도 않는 것을 위해 매 프레임
       깨우면 배터리만 먹는다 — 켜면 그때부터 돈다. */
    if (kAuroraGlow) _drift.repeat();
  }

  @override
  void dispose() {
    _drift.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    /* 🔴 **「애니메이션 줄이기」를 켠 사람에게는 멈춰 있는다.** 움직이는
       배경은 어지럼증을 일으킬 수 있고, 운영체제가 그 뜻을 이미 받아 뒀다.
       그때는 `phase: 0` — 예전 그림 그대로다. */
    final still = MediaQuery.disableAnimationsOf(context);

    return TweenAnimationBuilder<Color?>(
      tween: ColorTween(end: widget.tint.a),
      duration: widget.duration,
      curve: Curves.easeInOut,
      builder: (context, a, _) => TweenAnimationBuilder<Color?>(
        tween: ColorTween(end: widget.tint.b),
        duration: widget.duration,
        curve: Curves.easeInOut,
        builder: (context, b, _) => AnimatedBuilder(
          animation: _drift,
          /* 🔴 **자식을 다시 안 짓는다.** 매 프레임 도는 애니메이션이라 자식을
             builder 안에 두면 프로필 목록 전체가 초당 60번 다시 지어진다. */
          child: widget.child,
          builder: (context, child) => AuroraBackground(
            base: widget.base,
            // 첫 프레임엔 아직 `null` 이다 — 그때는 목표 색으로 그린다.
            tint: (a: a ?? widget.tint.a, b: b ?? widget.tint.b),
            phase: still ? 0 : _drift.value,
            child: child!,
          ),
        ),
      ),
    );
  }
}

/// 화면 바탕.
///
/// 레퍼런스 실측은 `#2F2F2F` 였는데 **실기기에서 그보다 밝게 보였다**
/// (2026-09-22, 사용자 확인) — 화면이 밝고 대비가 커서 같은 값이라도 도안
/// 위에서보다 떠 보인다. 두 단 낮춰 **살짝 차가운 어두운 회색**으로 왔다.
///
/// 🔴 **완전한 검정이 아니다.** 검정은 판·테두리와 붙어 한 덩어리로 읽히고,
/// 유기 발광 화면에서 **검정과 그 바로 위 단이 계단처럼** 드러난다.
const Color kAuroraBase = Color(0xFF1C1C1E);

/// **빛무리를 그릴 것인가.**
///
/// 🔴 **지금은 끈 상태다**(2026-09-22, 사용자 요청: 「그냥 그 은은하게
/// 퍼지는거 없애봐」). 번지는 빛이 동심원 띠로 보이는 것을 몇 번 손봤는데,
/// 바탕이 회색이 되면서 **얻는 것보다 거슬리는 것이 커졌다.**
///
/// ⚠️ **끄면 「배경이 내 카드 색을 따라간다」도 같이 멈춘다** — 그 기능이
/// 빛무리의 색을 갈아 끼우는 방식이기 때문이다. 배선(`tint` · 부드러운
/// 전환)은 **그대로 두었으므로** 이 한 줄만 `true` 로 되돌리면 살아난다.
const bool kAuroraGlow = false;

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
  const _AuroraPainter({this.tint, this.phase = 0});

  /// 0~1 이 한 바퀴. 아래 [_painted] 가 이 값으로 자리와 알파를 흔든다.
  final double phase;

  /// `null` 이면 아래 브랜드 배치 그대로. 있으면 **자리와 알파는 두고 색만**
  /// 두 색으로 번갈아 갈아 끼운다.
  final ({Color a, Color b})? tint;

  /// 빛무리마다 다른 **흔들림 배수와 어긋난 출발점**.
  ///
  /// 🔴 **배수가 정수다.** 소수로 두면 「더 랜덤해 보이지만」 한 바퀴가 끝나는
  /// 지점에서 값이 제자리로 안 돌아와 **화면이 툭 튄다.** 정수 배수 + 서로
  /// 다른 출발점이면 이음매 없이 돌면서도 규칙이 안 읽힌다.
  static const _drift = [
    // (가로 배수, 세로 배수, 밝기 배수, 출발점)
    (1, 2, 1, 0.00),
    (2, 1, 2, 1.70),
    (1, 3, 1, 3.10),
    (3, 2, 2, 4.60),
  ];

  /// 빛무리가 돌아다니는 폭 — 화면 대비. 🔴 **너무 크게 두지 않는다**:
  /// 원이 화면 한가운데로 들어오면 「번진 빛」이 아니라 **동그라미**로 읽힌다.
  static const _amp = 0.22;

  /// 밝기가 내려가는 바닥 — 🔴 **0 까지 안 내린다.** 완전히 꺼졌다 켜지면
  /// 깜빡이는 것으로 보인다. 옅어졌다 짙어지는 정도로만 둔다.
  static const _dim = 0.35;

  /// 실제로 칠할 빛무리들 — 색을 갈아 끼우고, 자리와 밝기를 [phase] 로 흔든다.
  List<_Glow> get _painted {
    final t = tint;
    final w = phase * 2 * math.pi;
    return [
      for (var i = 0; i < _glows.length; i += 1)
        () {
          final g = _glows[i];
          final d = _drift[i % _drift.length];
          /* 🔴 **번갈아 준다** — 한 색을 위 둘, 다른 색을 아래 둘에 몰면
             화면이 위아래로 갈린 띠처럼 보인다. 엇갈려야 두 색이 섞인다. */
          final color = t == null ? g.color : (i.isEven ? t.a : t.b);
          if (phase == 0) {
            return _Glow(color, g.dx, g.dy, g.radius, g.alpha);
          }
          final breath = 0.5 + 0.5 * math.sin(w * d.$3 + d.$4);
          return _Glow(
            color,
            g.dx + _amp * math.sin(w * d.$1 + d.$4),
            g.dy + _amp * math.cos(w * d.$2 + d.$4),
            g.radius,
            g.alpha * (_dim + (1 - _dim) * breath),
          );
        }(),
    ];
  }

  /// 🔴 **넷을 넘기지 않는다.** 겹칠수록 색이 탁해지고, 화면마다 다른 그림이
  /// 되어 「같은 앱」으로 안 읽힌다.
  ///
  /// 🔴 **알파는 0.35 를 넘기지 않는다**(2026-09-21에 0.68까지 올렸다 되돌렸다).
  /// 판이 거의 투명해진 뒤로는 빛이 화면 **전체**에 퍼지는데, 세게 주면
  /// 「은은하게 비치는」 것이 아니라 **화면이 통째로 초록으로 물든다.**
  ///
  /// 🔴 **바탕이 회색이 되면서 한 단 더 낮췄다**(2026-09-22). 거의 검정일
  /// 때와 같은 알파를 회색 위에 얹으면 **대비가 커져 더 세게 보이고**, 띠도
  /// 그만큼 눈에 든다.
  static const _glows = [
    // 왼쪽 위 — 브랜드 민트.
    _Glow(AppTheme.seed, 0.06, 0.02, 0.98, 0.26),
    // 오른쪽 위 — 청록으로 한 단계 차갑게.
    _Glow(Color(0xFF2ED3B7), 1.06, 0.14, 0.86, 0.20),
    // 왼쪽 아래 — 진한 청. 아래를 눌러 카드가 떠 보이게 한다.
    _Glow(Color(0xFF1B7A8C), -0.10, 0.88, 0.92, 0.23),
    // 오른쪽 아래 — 민트를 옅게 한 번 더(빛이 감싸는 느낌).
    _Glow(AppTheme.seed, 0.98, 1.04, 0.76, 0.15),
  ];

  @override
  void paint(Canvas canvas, Size size) {
    // 🔴 꺼 두면 바탕색만 남는다 — [kAuroraGlow] 머리말 참고.
    if (!kAuroraGlow) return;
    final short = size.shortestSide;
    for (final g in _painted) {
      final center = Offset(size.width * g.dx, size.height * g.dy);
      final r = short * g.radius;
      canvas.drawCircle(
        center,
        r,
        Paint()
          ..shader = RadialGradient(
            /* 🔴 **곧게 떨어뜨리지 않는다**(2026-09-22, 사용자 지적: 「그 원
               선들이 너무 잘 보여」). 가운데에서 가장자리까지 **일정하게**
               옅어지면, 색은 256단이라 같은 폭마다 한 단씩 끊기고 그 경계가
               **동심원 띠**로 보인다.

               종 모양(`exp(-3t²)`)으로 떨어뜨리면 변화가 가운데에 몰리고
               **바깥은 거의 평평해진다** — 띠가 생길 만한 바깥에서는 한 단
               차이가 날 일이 없어 안 보인다. 끝 값은 0 으로 맞춰(마지막
               항을 빼고 정규화) 가장자리에 테가 안 남는다. */
            colors: [
              for (final k in const [1.0, 0.880, 0.599, 0.306, 0.102, 0.0])
                // 🔴 같은 색의 **투명**으로 끝낸다. 흰·검정으로 끝내면
                //    가장자리에 테가 생겨 원이 드러난다.
                g.color.withValues(alpha: g.alpha * k),
            ],
            stops: const [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
          ).createShader(Rect.fromCircle(center: center, radius: r)),
      );
    }
  }

  /// 🔴 **색이 갈리면 다시 칠한다.** 붙박이로 `false` 를 돌려주던 자리인데,
  /// 색을 받게 되면서 그러면 **프로필 배경이 영영 첫 색에 멈춘다.** 자리·
  /// 알파는 상수라 색만 견주면 된다.
  @override
  bool shouldRepaint(_AuroraPainter oldDelegate) =>
      kAuroraGlow &&
      (oldDelegate.tint?.a != tint?.a ||
          oldDelegate.tint?.b != tint?.b ||
          oldDelegate.phase != phase);
}
