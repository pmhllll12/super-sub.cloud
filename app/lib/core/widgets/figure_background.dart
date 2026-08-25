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

/// 한 번 끄덕이는 데 걸리는 시간.
///
/// 9초짜리 숨쉬기였는데 움직이는지 보이지 않아 고개 끄덕임으로 바꿨다.
/// 3.2초면 눈에 들어오면서도 조급해 보이지 않는다.
const Duration _kNodPeriod = Duration(milliseconds: 3200);

/// 끄덕이는 각도(라디안). 약 1.7도.
///
/// **평면 사진을 돌리는 것이므로 크면 안 된다.** 넘어가면 얼굴이 도는 게
/// 아니라 사진이 기우는 것으로 보인다.
const double _kNodAngle = 0.030;

/// 함께 내려가는 거리(논리 px). 각도만 주면 미끄러지는 느낌이라 무게를 준다.
const double _kNodDrop = 10;

/// 돌릴 때 가장자리가 비지 않도록 살짝 키운다.
const double _kNodScale = 1.03;

/// 회전축. 사진에서 목 아래쯤이다(가로 35%, 세로 62%).
///
/// **여기가 축이어야 어깨는 그대로 두고 머리만 움직인다.** 가운데를 축으로
/// 하면 몸통째 기울어 인형처럼 보인다.
const Alignment _kNodPivot = Alignment(-0.30, 0.24);

/// 유리가 굴절시킬 바탕. 홈과 영상 분석이 같은 것을 쓴다.
///
/// **세로를 채우고 오른쪽을 잘라 낸다.** 사진은 세로가 짧아 화면에 맞추면
/// 좌우가 남는데, 왼쪽에 얼굴이 있으므로 왼쪽을 기준으로 붙이고 오른쪽
/// (뒤통수 바깥)이 잘리게 둔다.
///
/// **인물과 배경이 두 장이다.** 한 장을 통째로 돌리면 사진 가장자리가 드러나
/// 검은 바탕이 옆에서 새어 나온다. 인물만 알파로 떼어 두면 배경은 가만히
/// 있고 인물만 움직인다. 배경 판에는 인물 자리를 지운 자국이 옅게 남아 있어,
/// 인물이 끄덕일 때 드러나는 틈에 검정 대신 제 그림자가 보인다.
class FigureBackground extends StatefulWidget {
  const FigureBackground({super.key, this.breathe = false});

  /// 참이면 인물이 천천히 고개를 끄덕인다. 홈에서만 켠다 — 다른 화면은
  /// 내용이 앞에 있어 배경까지 움직이면 산만하다.
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
      _ctrl = AnimationController(vsync: this, duration: _kNodPeriod)
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
    // 두 장이 정확히 같은 자리에 놓여야 겹쳐 보인다 — 같은 비율·같은 정렬.
    Widget layer(String asset) => Align(
          alignment: Alignment.topCenter,
          child: FractionallySizedBox(
            heightFactor: _kFigureHeightFactor,
            child: Image(
              image: AssetImage(asset),
              fit: BoxFit.cover,
              alignment: Alignment.centerLeft,
            ),
          ),
        );

    final figure = layer('assets/images/home_cut.png');

    final ctrl = _ctrl;
    return Stack(
      fit: StackFit.expand,
      children: [
        layer('assets/images/home_bg.jpg'),
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
              return Transform.scale(
                // 돌리면 가장자리가 빌 수 있어 미리 조금 키워 둔다.
                scale: _kNodScale,
                child: Transform.translate(
                  offset: Offset(0, _kNodDrop * t),
                  child: Transform.rotate(
                    angle: _kNodAngle * t,
                    alignment: _kNodPivot,
                    child: child,
                  ),
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
