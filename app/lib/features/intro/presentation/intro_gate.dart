import 'dart:ui' show lerpDouble;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/widgets/ink_bleed.dart';
import 'brand_mark.dart';
import 'screens/glitch_intro_screen.dart';

/// 인트로를 얹을지. 기본은 켜짐.
///
/// **테스트에서 끄라고 있는 것이다.** 인트로가 3.1초 동안 모든 라우트를
/// 덮으므로, 착지 화면을 확인하는 라우터 테스트가 인트로만 보게 된다.
/// 그렇다고 테스트마다 5초를 흘려보내면 스위트가 느려지고, 인트로 길이를
/// 바꿀 때마다 관계없는 테스트가 깨진다.
final introEnabledProvider = Provider<bool>((ref) => true);

/// 인트로 글자가 날아가는 데 씌우는 곡선.
///
/// 잉크는 앞 2/3에서 끝나고(`kIntroExitPeel`) 글자는 끝까지 난다. 가속·감속을
/// 함께 줘야 "떠났다가 자리를 찾아 앉는" 것으로 읽힌다.
const Curve _kFlightCurve = Curves.easeInOutCubic;

/// 앱 화면 위에 인트로를 한 번 얹었다가 잉크를 걷어 내며 물러난다.
///
/// **라우터를 건드리지 않는다.** 인트로를 라우트로 만들면 리다이렉트 분기가
/// 하나 더 늘고, 뒤로가기로 인트로에 돌아오는 길도 막아야 한다. 대신
/// `MaterialApp.router`의 `builder`에 끼워 모든 라우트 위에 겹으로 둔다.
///
/// 덤으로 콜드 스타트의 빈 화면 문제가 가려진다 — 세션 복원이 끝나기 전
/// 홈이 한 번 칠해지는 구간이 인트로에 통째로 덮인다.
///
/// 라우트가 아니라 겹이라 `Hero`를 못 쓴다. 그래서 글자의 비행은 착지점의
/// 화면 좌표를 [kBrandLandingKey]로 직접 읽어 손으로 날린다.
class IntroGate extends StatefulWidget {
  const IntroGate({super.key, required this.child});

  /// 라우터가 그리는 앱 본체.
  final Widget child;

  @override
  State<IntroGate> createState() => _IntroGateState();
}

enum _Phase { intro, peeling, done }

class _IntroGateState extends State<IntroGate>
    with SingleTickerProviderStateMixin {
  late final AnimationController _exit = AnimationController(
    vsync: this,
    duration: kIntroExitDuration,
  );

  _Phase _phase = _Phase.intro;

  /// 글자가 앉을 자리(화면 좌표). 착지점을 못 찾으면 null이고, 그때는 날리지
  /// 않는다 — 로그인이 아닌 화면으로 나가는 경우가 그렇다.
  Rect? _landing;

  @override
  void dispose() {
    kBrandFlightInProgress.value = false;
    _exit.dispose();
    super.dispose();
  }

  void _onIntroDone() {
    if (!mounted) return;

    _landing = _landingRect();
    if (_landing != null) kBrandFlightInProgress.value = true;

    setState(() => _phase = _Phase.peeling);
    _exit.forward().whenComplete(() {
      if (!mounted) return;
      // 날아온 글자와 착지점의 글자가 정확히 겹친 순간에 넘긴다 — 바뀌는 게
      // 안 보인다.
      kBrandFlightInProgress.value = false;
      setState(() => _phase = _Phase.done);
      // **잉크 지도를 여기서 놓아주지 않는다.**
      //
      // 원본(`com.sumworship`)의 주석이 못박아 둔 함정이다 — 인트로가 끝날 때
      // 놓아주면, 같은 잉크를 쓰는 다음 전환에서 지도가 없어 조용히 밋밋한
      // 페이드로 물러난다. 아무도 안 터지고 연출만 달라져서 알아채기 어렵다.
      //
      // 지금 이 앱에는 잉크를 쓰는 다른 전환이 없지만, 화면 전환에 잉크를
      // 더 쓰기로 하면 그때 이 판단을 다시 해야 한다. 놓아줄 자리는 "잉크를
      // 쓰는 마지막 연출이 끝난 뒤"이지 "인트로가 끝난 뒤"가 아니다.
      // 지도는 1080×2340 RGBA = 약 9.6MB다.
    });
  }

  /// 착지점의 화면 좌표. 아직 안 지어졌거나 배치 전이면 null.
  Rect? _landingRect() {
    final ctx = kBrandLandingKey.currentContext;
    if (ctx == null) return null;
    final box = ctx.findRenderObject();
    if (box is! RenderBox || !box.hasSize) return null;
    return box.localToGlobal(Offset.zero) & box.size;
  }

  @override
  Widget build(BuildContext context) {
    switch (_phase) {
      case _Phase.done:
        return widget.child;

      case _Phase.peeling:
        // 이미 잉크로 덮여 있는 상태에서 나온다 — 덮는 구간 없이 바로 걷는다.
        final peeled = InkPeel(
          animation: _exit,
          ink: kIntroInkColor,
          peel: kIntroExitPeel,
          child: widget.child,
        );
        final landing = _landing;
        if (landing == null) return peeled;
        return Stack(
          fit: StackFit.expand,
          children: [peeled, _FlyingBrand(t: _exit, landing: landing)],
        );

      case _Phase.intro:
        // 아래에 본체를 깔아 두면 인트로가 흐르는 동안 다음 화면이 다 지어진다.
        // 인트로 Scaffold가 불투명해서 비치지 않는다. 착지점의 좌표를 읽을 수
        // 있는 것도 이 덕분이다.
        return Stack(
          fit: StackFit.expand,
          children: [
            widget.child,
            GlitchIntroScreen(onDone: _onIntroDone),
          ],
        );
    }
  }
}

/// 화면 한가운데에서 [landing] 자리로 날아가 앉는 글자.
class _FlyingBrand extends StatelessWidget {
  const _FlyingBrand({required this.t, required this.landing});

  final Animation<double> t;
  final Rect landing;

  @override
  Widget build(BuildContext context) {
    final screen = MediaQuery.sizeOf(context);
    final from = Offset(screen.width / 2, screen.height / 2);
    final to = landing.center;

    return IgnorePointer(
      child: AnimatedBuilder(
        animation: t,
        builder: (context, _) {
          final v = _kFlightCurve.transform(t.value);
          final at = Offset.lerp(from, to, v)!;
          final size = lerpDouble(kIntroBrandSize, kBrandLandedSize, v)!;
          return Positioned(
            left: at.dx,
            top: at.dy,
            child: FractionalTranslation(
              translation: const Offset(-0.5, -0.5),
              child: Text(
                kBrandText,
                style: BrandMark.styleFor(size, Colors.white),
              ),
            ),
          );
        },
      ),
    );
  }
}
