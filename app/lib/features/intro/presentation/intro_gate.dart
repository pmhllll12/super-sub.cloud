import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/widgets/ink_bleed.dart';
import 'screens/glitch_intro_screen.dart';

/// 인트로를 얹을지. 기본은 켜짐.
///
/// **테스트에서 끄라고 있는 것이다.** 인트로가 3.1초 동안 모든 라우트를
/// 덮으므로, 착지 화면을 확인하는 라우터 테스트가 인트로만 보게 된다.
/// 그렇다고 테스트마다 5초를 흘려보내면 스위트가 느려지고, 인트로 길이를
/// 바꿀 때마다 관계없는 테스트가 깨진다.
final introEnabledProvider = Provider<bool>((ref) => true);

/// 앱 화면 위에 인트로를 한 번 얹었다가 잉크를 걷어 내며 물러난다.
///
/// **라우터를 건드리지 않는다.** 인트로를 라우트로 만들면 리다이렉트 분기가
/// 하나 더 늘고, 뒤로가기로 인트로에 돌아오는 길도 막아야 한다. 대신
/// `MaterialApp.router`의 `builder`에 끼워 모든 라우트 위에 겹으로 둔다.
///
/// 덤으로 콜드 스타트의 빈 화면 문제가 가려진다 — 세션 복원이 끝나기 전
/// 홈이 한 번 칠해지는 구간이 인트로에 통째로 덮인다.
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

  @override
  void dispose() {
    _exit.dispose();
    super.dispose();
  }

  void _onIntroDone() {
    if (!mounted) return;
    setState(() => _phase = _Phase.peeling);
    _exit.forward().whenComplete(() {
      if (!mounted) return;
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

  @override
  Widget build(BuildContext context) {
    switch (_phase) {
      case _Phase.done:
        return widget.child;

      case _Phase.peeling:
        // 이미 잉크로 덮여 있는 상태에서 나온다 — 덮는 구간 없이 바로 걷는다.
        return InkPeel(
          animation: _exit,
          ink: kIntroInkColor,
          peel: kIntroExitPeel,
          child: widget.child,
        );

      case _Phase.intro:
        // 아래에 본체를 깔아 두면 인트로가 흐르는 동안 다음 화면이 다 지어진다.
        // 인트로 Scaffold가 불투명해서 비치지 않는다.
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
