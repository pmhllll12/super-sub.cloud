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
    this.fill = const Color(0xB31C1C1E),
    this.strong = false,
    this.padding,
  });

  final Widget child;
  final double radius;

  /// 면 색 — **반투명**이어야 뒤의 빛무리가 비친다.
  final Color fill;

  /// 눌린 상태·고른 상태처럼 **또렷해야 할 때** 테두리를 한 단 올린다.
  final bool strong;

  final EdgeInsetsGeometry? padding;

  /// 은빛 — 차갑게 기운 아주 옅은 회색.
  static const Color silver = Color(0xFFC9D4D8);

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: fill,
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(
          // 레퍼런스의 `rgba(255,255,255,0.1)` 자리다 — 은빛으로 바꿔 달았다.
          color: silver.withValues(alpha: strong ? 0.38 : 0.16),
          width: 1,
        ),
      ),
      child: padding == null ? child : Padding(padding: padding!, child: child),
    );
  }
}
