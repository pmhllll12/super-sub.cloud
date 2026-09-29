import 'package:flutter/material.dart';

/// 얇은 **실버 테두리** — 반투명 면 위에 가는 은빛 선 하나로 경계를 낸다.
///
/// 🔴 **유리가 아니다.** 판 안에는 알약이, 알약 안에는 아이콘이 들어가는데
/// 그 층마다 유리를 쓰면 **「유리 안에 유리」**가 되어 안쪽이 프레임째 사라진다
/// (`flutter/CLAUDE.md`). 같은 문서가 적어 둔 방법이 **「흐림 없이 색만 얹는다」**
/// 이고, 여기에 가는 테두리를 더해 경계를 낸다(사용자 제안, 2026-09-21).
///
/// 🔴 **테두리를 흰색 그대로 쓰지 않는다.** 순백은 어두운 화면에서 형광등처럼
/// 튄다 — 아주 옅은 청회색(은빛)이 뒤의 빛무리와 같은 결로 섞인다.
///
/// 굴절·흐림이 없어 **값싸다** — 판마다 써도 프레임이 안 흔들린다.
class SilverEdge extends StatelessWidget {
  const SilverEdge({
    super.key,
    required this.child,
    this.radius = 18,
    this.fill = defaultFill,
    this.strong = false,
    this.padding,
    this.line,
    this.lineWidth,
  });

  final Widget child;
  final double radius;

  /// 면 색 — **반투명**이어야 뒤의 빛무리가 비친다.
  final Color fill;

  /// 눌린 상태·고른 상태처럼 **또렷해야 할 때** 테두리를 한 단 올린다.
  final bool strong;

  final EdgeInsetsGeometry? padding;

  /// 테두리 색·굵기를 직접 준다. 안 주면 아래 기본값.
  final Color? line;
  final double? lineWidth;

  /// 은빛 — 차갑게 기운 아주 옅은 회색.
  /// 🔴 **알약들이 나눠 쓰는 면.** 팀장·팀원 알약과 「팀 매칭」이 같은 값을
  /// 쓴다 — 한쪽만 바꾸면 나란히 선 것들이 다른 재질로 읽힌다.
  static const Color defaultFill = Color(0xB31C1C1E);

  static const Color silver = Color(0xFFC9D4D8);

  /// 🔴 **하단 바 윤곽과 로고 알약이 나눠 쓰는 선**(2026-09-22, 사용자 요청:
  /// 「로고 외곽선 색상 하단바의 외곽선 색상이랑 똑같이」). 한쪽만 고치면
  /// 알약이 바에서 떠 보이거나 묻힌다.
  static const Color barLine = Color(0x8CC9D4D8);
  static const double barLineWidth = 0.5;

  /// 🔴 **흰 면 위에서 쓰는 은빛**(2026-09-23). [silver](`#C9D4D8`)는 **검은
  /// 바탕**에서 경계를 내려고 고른 밝은 값이라, 흰 면 위에서는 흰색에 붙어
  /// 사라진다 — 홈의 영상 분석 판에서 가장자리 픽셀을 재서 확인했다(`#fefefe`).
  ///
  /// 🔴 **홈의 영상 분석 판과 하단 바가 나눠 쓴다.** 둘 다 흰 면 위에 놓인
  /// 같은 성격의 테라서, 값이 갈리면 한 화면에서 두 굵기·두 색이 보인다.
  ///
  /// ⚠️ **굵기는 [barLineWidth] 와 같은 0.5 다** — 사용자 요청의 「제일 얇은」
  /// 이 그 값이다.
  static const Color onWhite = Color(0xFF9AA7AD);
  static const double onWhiteWidth = barLineWidth;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: fill,
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(
          // 레퍼런스의 `rgba(255,255,255,0.1)` 자리다 — 은빛으로 바꿔 달았다.
          color: line ?? silver.withValues(alpha: strong ? 0.38 : 0.16),
          width: lineWidth ?? 1,
        ),
      ),
      child: padding == null ? child : Padding(padding: padding!, child: child),
    );
  }
}
