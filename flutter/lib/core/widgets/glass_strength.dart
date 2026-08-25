import 'dart:async';

import 'package:flutter/foundation.dart' show ValueListenable;
import 'package:flutter/widgets.dart';

/// 스크롤이 움직이면 1로 올리고, 멈추면 잠시 기다렸다가 0으로 되돌린다.
///
/// 굴절은 항상 켜져 있으므로 이 값은 **분산과 채움에만** 곱해진다.
class GlassStrength {
  /// 마지막 스크롤 후 이만큼은 그대로 두었다가 내려가기 시작한다.
  static const hold = Duration(milliseconds: 1200);

  /// 내려가는 데 걸리는 시간.
  static const fall = Duration(milliseconds: 800);

  final AnimationController _ctrl;
  Timer? _holdTimer;

  GlassStrength({required TickerProvider vsync})
      : _ctrl = AnimationController(vsync: vsync, duration: fall, value: 0);

  ValueListenable<double> get value => _ctrl;

  /// 스크롤이 움직였다. 즉시 1로 올리고 대기 시계를 다시 감는다.
  void bump() {
    _holdTimer?.cancel();
    _ctrl.value = 1.0;
    _holdTimer = Timer(hold, () => _ctrl.reverse(from: 1.0));
  }

  void dispose() {
    _holdTimer?.cancel();
    _ctrl.dispose();
  }
}

/// 화면 전체가 같은 유리 강도를 쓰도록 아래로 흘려 준다.
///
/// 하단 바만 굴절 유리를 쓰던 동안엔 값을 직접 넘기면 됐다. 탭 안쪽의
/// 위젯까지 같은 유리를 쓰기 시작하면서, 중간에 있는 위젯 전부가 쓰지도
/// 않는 값을 손에서 손으로 넘겨야 하는 상황이 됐다.
class GlassStrengthScope extends InheritedWidget {
  final ValueListenable<double> strength;

  const GlassStrengthScope({
    super.key,
    required this.strength,
    required super.child,
  });

  /// 위에 아무도 없으면 null. 그때 쓰는 쪽은 흐림 유리로 물러선다.
  static ValueListenable<double>? maybeOf(BuildContext context) => context
      .dependOnInheritedWidgetOfExactType<GlassStrengthScope>()
      ?.strength;

  @override
  bool updateShouldNotify(GlassStrengthScope old) => old.strength != strength;
}
