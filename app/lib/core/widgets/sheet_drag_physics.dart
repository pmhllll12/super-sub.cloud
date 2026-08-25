/// 아래에서 끌어올리는 시트의 물리.
///
/// 위젯을 모른다 — 진행도와 손가락 값만 받아 다음 진행도를 돌려주므로 화면 없이
/// 검증된다.
///
/// 진행도는 0(접힘)에서 1(펼침)이다. 화면 좌표는 아래가 양수라, 위로 끄는 것은
/// [dy]가 음수인 것이고 그때 진행도가 커진다.
class SheetDragPhysics {
  /// 접힘과 펼침 사이의 거리(px). 이만큼 끌면 진행도가 0에서 1이 된다.
  final double travel;

  /// 손을 뗐을 때 펼침으로 갈지 접힘으로 갈지 가르는 진행도.
  static const double settleThreshold = 0.5;

  /// 이 속도(px/s)보다 빠르게 던지면 진행도와 무관하게 방향이 결정된다.
  /// 인트로 화면이 쓰던 값과 같다.
  static const double flingVelocity = 600;

  /// 던져서 펼치려면 최소한 이만큼은 끌어올렸어야 한다. 접힌 채로 화면을
  /// 튕기기만 해도 시트가 열리는 것을 막는다.
  static const double flingMinProgress = 0.08;

  const SheetDragPhysics({required this.travel});

  /// 손가락이 [dy]만큼 움직인 뒤의 진행도.
  double advance(double progress, double dy) =>
      (progress - dy / travel).clamp(0.0, 1.0);

  /// 손을 뗐을 때 펼침으로 안착할지.
  ///
  /// [velocity]는 화면 좌표계라 위로 던지면 음수다.
  bool shouldExpand(double progress, double velocity) {
    if (velocity <= -flingVelocity) return progress > flingMinProgress;
    if (velocity >= flingVelocity) return false;
    return progress >= settleThreshold;
  }
}
