import 'package:flutter/material.dart';

/// 인물이 화면에서 차지하는 높이 비율.
const double _kFigureHeightFactor = 0.88;

/// 인물을 검정으로 잦아들게 하는 막.
///
/// 사진 자체가 아래로 갈수록 어둡지만 딱 떨어지지는 않는다. 이 막이 그 나머지를
/// 지워 사진의 아랫변이 선으로 보이지 않게 한다.
const LinearGradient _kFigureFade = LinearGradient(
  begin: Alignment.topCenter,
  end: Alignment.bottomCenter,
  colors: [Color(0x00000000), Color(0x4D000000), Color(0xFF000000)],
  stops: [0.62, 0.88, 1],
);

/// 숨 한 번에 걸리는 시간.
///
/// **느려야 한다.** 빠르면 사진이 흔들리는 것으로 보이고, 유리 너머의 굴절이
/// 같이 출렁여 눈이 피로하다. 9초면 보고 있을 때만 겨우 알아차린다.
const Duration _kBreath = Duration(seconds: 9);

/// 숨 끝에서의 배율과 올라가는 거리(논리 px).
///
/// 배율 1.5%, 6px. 이보다 크면 "움직인다"가 아니라 "떨린다"로 읽힌다.
const double _kBreathScale = 1.015;
const double _kBreathRise = 6;

/// 유리가 굴절시킬 바탕. 홈과 영상 분석이 같은 것을 쓴다.
///
/// **세로를 채우고 오른쪽을 잘라 낸다.** 사진은 세로가 짧아 화면에 맞추면
/// 좌우가 남는데, 왼쪽에 얼굴이 있으므로 왼쪽을 기준으로 붙이고 오른쪽
/// (뒤통수 바깥)이 잘리게 둔다.
class FigureBackground extends StatefulWidget {
  const FigureBackground({super.key, this.breathe = false});

  /// 참이면 인물이 아주 느리게 숨쉰다. 홈에서만 켠다 — 다른 화면은 내용이
  /// 앞에 있어 배경까지 움직이면 산만하다.
  final bool breathe;

  @override
  State<FigureBackground> createState() => _FigureBackgroundState();
}

class _FigureBackgroundState extends State<FigureBackground>
    with SingleTickerProviderStateMixin {
  AnimationController? _ctrl;

  @override
  void initState() {
    super.initState();
    if (widget.breathe) {
      _ctrl = AnimationController(vsync: this, duration: _kBreath)
        ..repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _ctrl?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final figure = Align(
      alignment: Alignment.topCenter,
      child: FractionallySizedBox(
        heightFactor: _kFigureHeightFactor,
        child: const Image(
          image: AssetImage('assets/images/home_figure.jpg'),
          fit: BoxFit.cover,
          alignment: Alignment.centerLeft,
        ),
      ),
    );

    final ctrl = _ctrl;
    return Stack(
      fit: StackFit.expand,
      children: [
        if (ctrl == null)
          figure
        else
          AnimatedBuilder(
            animation: ctrl,
            // 사진은 한 번만 짓고 변환만 매 프레임 바꾼다 — 다시 지으면
            // 큰 이미지를 프레임마다 배치하게 된다.
            child: figure,
            builder: (context, child) {
              final t = Curves.easeInOut.transform(ctrl.value);
              return Transform.translate(
                offset: Offset(0, -_kBreathRise * t),
                child: Transform.scale(
                  scale: 1 + (_kBreathScale - 1) * t,
                  // 위쪽을 붙박아 두고 아래로 자란다 — 가운데를 기준으로
                  // 하면 머리가 화면 위로 밀려 잘린다.
                  alignment: Alignment.topCenter,
                  child: child,
                ),
              );
            },
          ),
        Align(
          alignment: Alignment.topCenter,
          child: FractionallySizedBox(
            heightFactor: _kFigureHeightFactor,
            child: const DecoratedBox(
              decoration: BoxDecoration(gradient: _kFigureFade),
              child: SizedBox.expand(),
            ),
          ),
        ),
      ],
    );
  }
}
