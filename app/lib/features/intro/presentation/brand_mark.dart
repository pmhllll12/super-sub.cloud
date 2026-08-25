import 'package:flutter/material.dart';

import '../../../core/theme/app_theme.dart';

/// 앱 이름. 인트로와 로그인이 같은 글자를 쓴다.
const String kBrandText = 'SUPERSUB';

/// 착지한 뒤의 글자 크기. 로그인 화면과 비행이 같은 값을 봐야 앉는 순간
/// 크기가 안 튄다.
const double kBrandLandedSize = 40;

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
