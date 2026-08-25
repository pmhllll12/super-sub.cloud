import 'dart:ui' show lerpDouble;

import 'package:flutter/material.dart';

import '../../../core/theme/app_theme.dart';

/// 앱 이름. 인트로와 로그인이 같은 글자를 쓴다.
const String kBrandText = 'SUPERSUB';

/// 착지한 뒤의 글자 크기. 로그인 화면과 비행이 같은 값을 봐야 앉는 순간
/// 크기가 안 튄다.
const double kBrandLandedSize = 34;

/// 인트로 글자가 날아와 앉는 자리.
///
/// 로그인 화면의 [BrandMark]가 이 키를 단다. 인트로를 라우트가 아니라 겹으로
/// 뒀기 때문에 `Hero`를 못 쓴다 — 대신 이 키로 착지점의 화면 좌표를 읽어
/// 직접 날린다.
final GlobalKey kBrandLandingKey = GlobalKey();

/// 비행 중인지. 참이면 착지점의 글자를 감춘다.
///
/// 안 감추면 날아가는 글자와 착지점의 글자가 동시에 보인다. 착지하는 순간
/// 둘이 정확히 겹치므로, 그때 이 값을 내리면 바뀌는 게 안 보인다.
final ValueNotifier<bool> kBrandFlightInProgress = ValueNotifier<bool>(false);

/// 인트로가 남기고 간 글자.
///
/// 깨진 글꼴(RubikGlitch)로 굳은 모습 그대로다 — 인트로에서 지지직대다 굳은
/// 그 글자가 로그인 화면까지 이어진다.
class BrandMark extends StatelessWidget {
  const BrandMark({
    super.key,
    required this.fontSize,
    this.color = AppTheme.seed,
  });

  final double fontSize;
  final Color color;

  /// 크기 44에서 잰 자간 1.2를 비율로 옮긴다. 크기를 바꿔도 글자 사이가
  /// 같은 비율로 벌어져야 같은 글자로 읽힌다.
  static double letterSpacingFor(double fontSize) => fontSize * 1.2 / 44;

  static TextStyle styleFor(double fontSize, Color color) => TextStyle(
        fontFamily: 'RubikGlitch',
        // **밑줄 없음을 명시한다.** 인트로 겹은 라우트 밖(= Material 조상이
        // 없는 자리)에서 그려지는데, 그러면 Flutter가 기본 스타일로 노란
        // 이중 밑줄을 긋는다. 날아가는 글자에 그 줄이 따라다녔다.
        decoration: TextDecoration.none,
        // 가변 축이 없는 글꼴이라 무시되지만, 가지런한 Rubik과 나란히 둘 때
        // 살집을 맞추려고 900을 준다 — 인트로가 그 둘을 갈아 끼운다.
        fontVariations: const [FontVariation('wght', 900)],
        fontSize: fontSize,
        height: 1,
        letterSpacing: letterSpacingFor(fontSize),
        color: color,
      );

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<bool>(
      valueListenable: kBrandFlightInProgress,
      builder: (context, flying, _) => Opacity(
        opacity: flying ? 0 : 1,
        child: Text(kBrandText, style: styleFor(fontSize, color)),
      ),
    );
  }
}

/// 로그인의 로고가 하단 바의 알약으로 날아갈 때 쓰는 짝지음표.
///
/// **한 화면에 이 표를 단 것이 둘 있으면 터진다.** 붙이는 곳은 화면마다
/// 하나여야 한다 — 로그인에 하나, 홈의 알약에 하나.
const String kBrandHeroTag = 'supersub-brand';

/// 날아가는 동안 그려지는 글자.
///
/// 크기는 [FittedBox]가 상자에 맞춰 줄이므로 **여기 숫자는 비율의 기준일
/// 뿐**이고 화면에 그대로 나오지 않는다.
final TextStyle _kFlightStyle =
    BrandMark.styleFor(kIntroBrandSizeForFlight, AppTheme.seed);

/// 비행 글자의 기준 크기. 큰 쪽에서 줄여 그려야 흐려지지 않는다.
const double kIntroBrandSizeForFlight = 72;

/// 로고를 화면 사이로 날려 보내는 껍데기.
///
/// **비행 중에는 양쪽 위젯을 쓰지 않고 이 껍데기가 직접 그린다.**
///
/// Hero는 자식을 확대·축소하지 않는다 — 보간된 상자에 자식을 다시 배치할
/// 뿐이다. 그래서 큰 글자를 그대로 태우면 작은 상자에 억지로 들어가며 튀고,
/// 기본 동작대로 도착지 위젯을 쓰면 비행이 시작되는 순간 글자가 한 번 팍
/// 바뀐다. [FittedBox]가 상자에 맞춰 실제로 줄여 주면 이어서 작아진다.
///
/// **`createRectTween`을 반드시 준다.** 안 주면 `MaterialApp`이 깔아 둔
/// `MaterialRectArcTween`이 먹는데, 그것은 상자의 모서리를 각각 호를 따라
/// 옮겨 도중에 폭과 높이가 부풀었다 줄어든다.
Widget brandHero({required Widget child}) => Hero(
      tag: kBrandHeroTag,
      createRectTween: (begin, end) => BrandFlight(begin: begin, end: end),
      flightShuttleBuilder: (_, _, _, _, _) => Material(
        // 오버레이에는 Material이 없다. 투명한 것 하나를 깔아 준다 — 없으면
        // 노란 밑줄이 그어진다.
        type: MaterialType.transparency,
        child: FittedBox(
          fit: BoxFit.contain,
          child: Text(kBrandText, style: _kFlightStyle),
        ),
      ),
      child: child,
    );

/// 로고가 날아가는 길.
///
/// **크기는 곧게, 길은 휘게.** 곧은 보간은 글자가 일정한 속도로 비스듬히
/// 미끄러져 기계처럼 보인다. 가운데점만 2차 베지에로 휘고 시간에 완급을 준다.
///
/// 조절점은 `(출발 x, 도착 y)`다 — 먼저 떨어지고 끝에서 옆으로 붙는 길이라,
/// 세로로 긴 이 비행에서 자연스럽다.
class BrandFlight extends Tween<Rect?> {
  BrandFlight({
    required super.begin,
    required super.end,
    this.curve = Curves.easeInOutCubic,
  });

  final Curve curve;

  /// 2차 베지에 위의 점. 조절점은 출발의 가로, 도착의 세로다.
  static Offset bow(Offset from, Offset to, double t) {
    final c = Offset(from.dx, to.dy);
    final u = 1 - t;
    return Offset(
      u * u * from.dx + 2 * u * t * c.dx + t * t * to.dx,
      u * u * from.dy + 2 * u * t * c.dy + t * t * to.dy,
    );
  }

  @override
  Rect? lerp(double t) {
    final a = begin!;
    final b = end!;
    final e = curve.transform(t.clamp(0.0, 1.0));
    return Rect.fromCenter(
      center: bow(a.center, b.center, e),
      width: lerpDouble(a.width, b.width, e)!,
      height: lerpDouble(a.height, b.height, e)!,
    );
  }
}
