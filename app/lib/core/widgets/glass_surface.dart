import 'dart:ui';

import 'package:flutter/material.dart';

/// 유리 표면의 재료. 하단 바와 사이드바가 이 값을 함께 쓴다 — 한쪽만 고치면
/// 둘의 재질이 갈라진다.
const double kGlassBlur = 2.4;

/// 아주 옅은 흰 기 한 겹. 형태를 세우는 건 테두리가 아니라 이 면이다.
///
/// 겹쳐 놓으면 알아서 층이 진다 — 레일 몸통 위의 원 버튼, 토글 트랙 위의
/// 손잡이는 같은 값을 두 번 얹은 것이라 한 겹만큼 더 밝다.
final Color kGlassFill = Colors.white.withValues(alpha: 0.10);

/// 둥근 유리 조각 — 뒤를 살짝 흐리고 그 위에 옅은 흰 기를 얹는다.
/// 테두리는 두르지 않는다.
class GlassSurface extends StatelessWidget {
  final BorderRadius borderRadius;
  final Widget? child;

  const GlassSurface({super.key, required this.borderRadius, this.child});

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: borderRadius,
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: kGlassBlur, sigmaY: kGlassBlur),
        child: ColoredBox(color: kGlassFill, child: child),
      ),
    );
  }
}
