import 'package:flutter/widgets.dart';

/// 목업 캔버스의 가로 픽셀 수. Lottie 파일(1080×2112)을 그대로 따른다.
const double _kDesignWidth = 1080;

/// 목업 좌표를 이 화면의 논리 픽셀로 옮긴다.
///
/// 세로 좌표도 폭으로 환산한다 — 목업의 비율을 지키려면 한 축으로만 재야
/// 한다. 기기마다 남거나 모자라는 세로 몫은 작업대(회색 박스)가 흡수한다.
extension DesignScale on BuildContext {
  double d(double designPx) =>
      MediaQuery.sizeOf(this).width * designPx / _kDesignWidth;
}
