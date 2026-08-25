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

/// 유리가 굴절시킬 바탕. 홈과 영상 분석이 같은 것을 쓴다.
///
/// **세로를 채우고 오른쪽을 잘라 낸다.** 사진은 세로가 짧아 화면에 맞추면
/// 좌우가 남는데, 왼쪽에 얼굴이 있으므로 왼쪽을 기준으로 붙이고 오른쪽
/// (뒤통수 바깥)이 잘리게 둔다.
///
/// **가만히 있는다.** 한때 인물이 숨쉬거나 고개를 끄덕이게 해 봤다. 사진을
/// 통째로 돌리면 가장자리가 드러나고, 인물만 알파로 떼어 돌려도 평면이라
/// 몸이 접히는 것처럼 보였다. 제대로 하려면 머리와 몸을 따로 떼야 하는데
/// 그만한 값어치가 없어 걷어냈다(git 이력에 남아 있다).
class FigureBackground extends StatelessWidget {
  const FigureBackground({super.key});

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        Align(
          alignment: Alignment.topCenter,
          child: FractionallySizedBox(
            heightFactor: _kFigureHeightFactor,
            child: const Image(
              image: AssetImage('assets/images/home_figure.jpg'),
              fit: BoxFit.cover,
              alignment: Alignment.centerLeft,
            ),
          ),
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
