import 'dart:ui' as ui;

import 'package:flutter/material.dart';

/// 🔴 **왼쪽 위에서 해가 든다** — 그림자는 **오른쪽 아래로** 진다
/// (2026-09-22 사용자 요청). 홈·프로필의 알약들이 이것을 나눠 쓴다.
///
/// 🔴 **두 겹이다.** 멀고 옅은 것 하나 + 가깝고 진한 것 하나. 한 겹만 주면
/// 「떠 있다」가 아니라 **판에 그려 넣은 무늬**로 보인다 — 실제 그림자는
/// 닿는 자리가 진하고 멀수록 퍼진다.
///
/// ⚠️ `Material` 의 `elevation` 으로는 못 준다 — 그쪽 그림자는 **곧장 아래**로
/// 지고 방향을 못 정한다.
const List<BoxShadow> kSunShadow = [
  BoxShadow(color: Color(0x4D000000), blurRadius: 18, offset: Offset(6, 9)),
  BoxShadow(color: Color(0x33000000), blurRadius: 5, offset: Offset(2, 3)),
];

/// 같은 그림자를 **옅게** — 걷히는 중인 알약이 쓴다.
///
/// 🔴 그림자를 안 걷으면 알약이 다 사라진 뒤에도 **검은 얼룩만 남는다.**
List<BoxShadow> sunShadow(double show) => [
  for (final sh in kSunShadow)
    BoxShadow(
      color: sh.color.withValues(alpha: sh.color.a * show),
      blurRadius: sh.blurRadius,
      offset: sh.offset,
    ),
];

/// 유리 알약의 흐림 세기 — 🔴 **쓰는 곳이 모두 나눠 쓴다.**
/// 세 번 줄였다(2026-09-22 사용자 요청) — 10 → 9 → **7.2**.
/// ⚠️ **10% 줄였다**(2026-09-23 사용자 요청: 「버튼 블러 10퍼센트 줄이자」).
/// 7.2 → **6.48**.
///
/// 🔴 **홈의 「영상 분석 시작하기」와 프로필의 「내 분석/업로드 영상」이
/// 나눠 쓴다** — 둘이 같은 재질이어야 한다는 규칙이라 값을 여기서 갈았다.
/// 한쪽만 줄이려면 그 규칙부터 다시 정해야 한다.
const double kPillBlur = 6.48;

/// 유리 알약 안쪽의 흰 기 — 0 으로 두면 흐림만 남아 밋밋하다.
const double kPillTint = 0.16;

/// 알약의 모서리. 🔴 **높이의 절반보다 크게 둔다** — 그래야 양 끝이 완전한
/// 반원이다.
const double kPillRadius = 24;

/// **유리 알약** — 뒤를 흐리고 흰 기를 한 겹 얹은 알약.
///
/// 🔴 **재질을 한곳에 둔다**(2026-09-22). 홈의 「위로 올려 내 팀 만들기」·
/// 「영상 분석 시작하기」와 프로필의 「내 분석/업로드 영상」이 **같은 재질**로
/// 보여야 하는데, 값을 각자 적어 두면 한 곳만 고쳤을 때 말없이 갈린다.
///
/// ⚠️ **홈의 두 알약은 이 위젯을 안 쓰고 값만 나눠 쓴다** — 그쪽은 도는
/// 실버 테두리(`SilverSweepBorder`)·누를 때 커지는 것·알파로 걷히는 것 같은
/// 제 사정이 있어서다. 여기 있는 것은 **그 사정이 없는 쪽**을 위한 것이다.
///
/// 🔴 **흐림은 굴러가는 목록 위에서 쓰지 말 것.** 흐림은 가장자리에서 퍼 올
/// 것이 없어 가장자리 값을 늘려 쓰는데, 뒤가 구르면 그 띠가 매 프레임 달라져
/// **흰 직선**으로 보인다(`profile_screen.dart` 의 `_Block` 이 그것 때문에
/// 흐림을 걷었다). 뒤가 **움직이지 않는 사진**일 때만 쓴다.
class GlassPill extends StatelessWidget {
  const GlassPill({
    super.key,
    required this.child,
    this.onTap,

    /// 🔴 **컴팩트가 기본이다**(2026-09-22 사용자 요청: 「그 글자에 컴팩트하게
    /// 버튼을 주라고, 홈페이지에 있는 「위로 올려 내 팀 만들기」의 그 버튼처럼」).
    /// 그 알약과 **같은 값**이다 — 셋이 한 벌로 읽혀야 한다.
    this.padding = const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
    this.blur = true,
  });

  final Widget child;

  /// `null` 이면 안 눌린다 — 생김새만 알약인 이름표로 쓸 수 있다.
  final VoidCallback? onTap;
  final EdgeInsets padding;

  /// 🔴 **굴러가는 목록 안에서는 반드시 `false`**(2026-09-22, 사용자 지적:
  /// 「스크롤 하면 또또또 카드 외곽에 직선이 생겨」).
  ///
  /// 흐림은 뒤를 퍼다 쓰는데 **가장자리에서는 퍼 올 것이 없어 가장자리 값을
  /// 늘려 쓴다.** 뒤가 구르면 그 늘린 띠가 매 프레임 달라져 **흰 직선**으로
  /// 보인다 — 이 저장소가 같은 것을 `_Block`·`_GlassShell` 에서 두 번 겪고
  /// 흐림을 걷었다.
  ///
  /// ⚠️ **나는 이 경고를 이 파일에 적어 두고도 어겼다** — 프로필의 굴러가는
  /// 목록 안에 흐리는 알약을 넣었다. 그래서 기본값에 기대지 말고 **쓰는
  /// 자리가 구르는지**를 보고 정한다.
  ///
  /// 끄면 흐림만 빠지고 **면·그림자·크기는 그대로**라 다른 알약들과 같은
  /// 식구로 읽힌다.
  final bool blur;

  Widget _maybeBlur(Widget child) => blur
      ? BackdropFilter(
          filter: ui.ImageFilter.blur(sigmaX: kPillBlur, sigmaY: kPillBlur),
          child: child,
        )
      : child;

  @override
  Widget build(BuildContext context) {
    const r = Radius.circular(kPillRadius);
    return DecoratedBox(
      decoration: const BoxDecoration(
        borderRadius: BorderRadius.all(r),
        boxShadow: kSunShadow,
      ),
      child: ClipRRect(
        borderRadius: const BorderRadius.all(r),
        child: _maybeBlur(
          Material(
            color: Colors.white.withValues(alpha: kPillTint),
            child: InkWell(
              onTap: onTap,
              child: Padding(padding: padding, child: child),
            ),
          ),
        ),
      ),
    );
  }
}
