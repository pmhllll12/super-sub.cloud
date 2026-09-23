import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../design_scale.dart';
import 'silver_sweep_border.dart';

/// 막대의 면 — 🔴 **유리로 돌아왔다 (2026-09-23 두 번째 정정, 사용자 요청:
/// 「안쪽 흰색 하지말고 외곽선 없애고, 글래스로 바꿔」).** 몇 시간 전 흰색
/// 불투명으로 갔던 것을 되돌린 것이고, 외곽선([SilverEdge.onWhite])도 함께
/// 걷었다 — 유리는 제 흐림과 옅은 면으로 경계를 낸다.
///
/// 유리 → 검정 → 진회색 → 반투명 흰색 → 불투명 회색 → 흰색 → **유리** 순으로
/// 왔고, 매번 사용자가 정했다.
///
/// 🔴 **흐림이 있어야 이 값이 뜻을 갖는다** — 면만 반투명으로 두고 흐림을 빼면
/// 그냥 옅은 흰 막이다. [kNavBarBlur] 와 **짝이다.**
const Color kNavBarColor = Color(0x3DFFFFFF);

/// 막대의 **흐림 세기**(2026-09-23 사용자 요청: 「블러 30퍼만 주자」).
///
/// ⚠️ **「30%」를 무엇의 30%로 읽을지 애매하다** — 2026-09-22 에 같은 식으로
/// 「20%」를 받아 6 으로 뒀던 전례를 그대로 늘려 **9** 로 잡았다. 더 흐리게 /
/// 덜 흐리게는 이 한 줄이다.
const double kNavBarBlur = 9;

/// 고른 칸을 두르는 **도는 금빛**(2026-09-23 사용자 요청: 「그 정사각형의
/// 세련된 금색 실버색상이 돌아다니도록」 + 레퍼런스).
///
/// 🔴 **면이 아니라 선이다.** 한 번 반투명 흰 면으로 채웠는데 사용자가
/// 레퍼런스를 다시 보냈다 — 레퍼런스의 인상은 **둥근 정사각형 테두리를 도는
/// 빛**이지 칠한 칸이 아니다.
///
/// 🔴 **실버가 아니라 금빛이다** — 홈에는 「영상 분석 시작하기」 알약이 이미
/// 실버로 돌고 있다. 같은 색이면 둘이 섞여 「어디를 보라는 건지」가 흐려진다
/// (`silver_sweep_border.dart` 의 「한 화면에 하나」가 그 걱정이었다).
const Color kNavActiveSweep = Color(0xFFE6D5AE);

/// 빛이 지나가지 않는 동안에도 남는 바닥 선 — 없으면 빛이 없는 쪽 모서리가
/// 통째로 사라진다.
const Color kNavActiveSweepBase = Color(0x3DE6D5AE);

/// 고른 칸의 한 변 — 둥근 **정사각형**이다(레퍼런스).
const double kNavActiveSide = 118;

/// 유리 막대 위의 아이콘 — 바탕이 어두우므로 **흰색**이다.
const Color kNavOnWhite = Color(0xFFFFFFFF);

/// 칸 사이 세로선.
///
/// ⚠️ **알파를 두 번 올렸다** — 물리 1픽셀짜리 선이라 낮은 알파로는 실기기에서
/// 안 보인다. 굵히지 않고 알파만 올린다 — 굵으면 「그어 놓은 선」이 되고,
/// 레퍼런스의 인상은 가는 실이다. 유리로 바뀌며 **흰색 쪽**으로 뒤집혔다.
const Color kNavDividerColor = Color(0x59FFFFFF);

/// 바가 차지하는 높이(디자인 px).
///
/// 🔴 **155 → 200 (2026-09-23 사용자 요청: 「지금 높이보다 조금 높게 만들고,
/// 바로 위에 있는 판들도 좀 위로 그만큼 올리자」).**
///
/// 🔴 **판을 따로 올릴 필요가 없다** — 홈·영상·프로필이 전부 [heightOf] 로
/// 제 바닥을 재므로 이 한 줄이 셋을 다 밀어 올린다. 화면마다 숫자를 더하면
/// 다음에 이 값을 바꿀 때 그만큼 어긋난다.
const double kBottomBarHeight = 200;

/// 막대가 화면 양옆에서 떨어지는 거리(디자인 px).
///
/// 🔴 **떠 있는 막대다 (2026-09-23 사용자 요청: 「이 하단바는 양쪽 끝까지 굳이
/// 안 가도 됨」).** 옛 바는 **일부러 화면 밖까지** 나가서 어깨가 안 보였다 —
/// 되살리지 말 것.
///
/// ⚠️ 54 → **118** 로 한 번 더 좁혔다(같은 날, 「바 자체가 좌우로 너무 길어」).
const double kBarSideMargin = 118;

/// 막대가 화면 아래(안전 영역 위)에서 뜨는 거리.
const double kBarBottomGap = 18;

/// 막대 위로 남기는 자리 — 이만큼이 판과 막대 사이 틈이 된다.
const double kBarTopGap = 12;

/// 막대 네 모서리의 반경.
const double kBarRadius = 52;

/// 막대 안쪽 좌우 여백 — 🔴 **모서리 곡선이 파고드는 만큼보다 커야 한다.**
/// 작으면 양 끝 칸이 그 곡선에 잘린다.
const double kBarInnerPad = 22;

/// 구분선의 길이 — 막대 안쪽 높이의 절반쯤(레퍼런스가 그 정도다).
const double kBarDividerHeight = 78;


/// 화면 아래에 떠 있는 **한 덩이 둥근 막대**. 로고 칸 · 아이콘 셋 · 메뉴 칸이
/// 한 줄로 들어간다(2026-09-23 사용자 요청 + 레퍼런스).
///
/// ⛔ **되살리지 말 것 — 이전 짜임 셋.** 바는 `com.sumworship` 의 것을 가져와
/// **윗변에서 로고 자리만 파낸 한 장**(`_LogoNotch`)이었고, 그 홈에 `SUPERSUB`
/// **알약이 따로** 앉았으며(`_LogoButton`), 면은 뒤를 흐리는 검은 유리였다.
/// 파냄과 알약을 둘로 나눠 둔 까닭(「알약과 홈 사이 틈이 보여야 알약이
/// 알약으로 읽힌다」)은 **합친 지금 성립하지 않는다.** 고른 아이콘 뒤에 깔던
/// `_SelectedPlate`(흰 반투명 면 + 밝은 실버 두 모서리)도 같이 없어졌다 —
/// 어두운 바 기준이라 흰 막대 위에서 안 보인다. 셋 다 2026-09-23 이전
/// 커밋에서 꺼낸다.
///
/// 좌표는 시안 실측값이고 [DesignScale]이 화면 폭에 맞춰 환산한다.
/// 아래로 화면 밖까지 번지므로 SafeArea *밖*에 놓아야 한다.
class FloatingNavBar extends StatelessWidget {
  const FloatingNavBar({
    super.key,
    required this.currentIndex,
    required this.onTap,
  });

  final int currentIndex;
  final ValueChanged<int> onTap;

  /// **Material Symbols다.** Flutter가 안고 있는 `Icons`는 구형 Material
  /// Icons라 획이 두껍고 이 글리프들이 없다. 굵기·등급·광학크기는 [_navGlyph]가
  /// 한 곳에서 준다 — 아이콘마다 다르면 줄이 들쭉날쭉해진다.
  ///
  /// 글리프는 이 앱의 구획에 맞춰 골랐다. 원본(`com.sumworship`)의 것은
  /// 쇼핑백·북마크라 여기서는 뜻이 안 맞는다.
  ///
  /// 🔴 **0번(홈)이 아이콘으로 돌아왔다 (2026-09-23 사용자 요청: 「supersub 의
  /// 로고 홈 복귀하는 버튼을 그냥 구글 폰트의 이걸로 해줘」 + `home_app_logo`
  /// 그림).** 그 자리에 있던 `SUPERSUB` 알약은 **화면 맨 위 가운데로 옮겼고**,
  /// 거기서는 아무 단추도 아니다 — 옮긴 자리는 홈의 `_brandMark` 다.
  static const _icons = {
    0: Symbols.home_app_logo,
    1: Symbols.videocam,
    // 레슨 · 코치(2026-09-15 — 축구공을 대신한다). 홈의 「레슨 · 코치」 카드가
    // 여기로 옮겨 왔다. 용병 매칭 · 내 팀은 홈의 스쿼드 판이 맡는다.
    2: Symbols.school,
    3: Symbols.id_card,
  };

  /// 탭이 아니라 메뉴를 여는 자리. 인덱스가 아니라 이 표로 가른다.
  static const menuIndex = 4;
  static const _menuIcon = Symbols.format_list_bulleted_add;

  static double iconWidth(BuildContext context) => context.d(160);

  /// 바 메뉴가 제 칸들을 펼치는 간격. 아이콘 하나가 차지하는 폭이면 충분하다 —
  /// 메뉴는 바 **위에** 따로 서므로 바의 실제 배치와 맞물릴 필요가 없다.
  static double iconStep(BuildContext context) => iconWidth(context);

  /// 바가 화면 아래에서 가리는 높이.
  ///
  /// 바는 자리를 차지하지 않고 떠 있다. 바 밑까지 번지는 화면은 자기 내용을
  /// 이만큼 띄워야 버튼이 바에 먹히지 않는다.
  static double heightOf(BuildContext context) =>
      context.d(kBottomBarHeight) + MediaQuery.paddingOf(context).bottom;

  @override
  Widget build(BuildContext context) {
    final barHeight = context.d(kBottomBarHeight);
    final bottomInset = MediaQuery.paddingOf(context).bottom;

    return SizedBox(
      height: barHeight + bottomInset,
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          context.d(kBarSideMargin),
          context.d(kBarTopGap),
          context.d(kBarSideMargin),
          bottomInset + context.d(kBarBottomGap),
        ),
        child: _GlassBar(
          key: const Key('navbar-bar'),
          decoration: BoxDecoration(
            color: kNavBarColor,
            /* 🔴 **완전한 반원 끝이 아니다.** 한 번 스타디움(반경 = 높이)으로
               뒀더니 **메뉴 칸이 그 곡선에 잘렸다** — 칸은 네모라서 양 끝의
               반원 안으로 들어가지 못한다. 반경을 높이의 3할쯤으로 내리고,
               아래 가로 안여백이 남은 곡선을 비켜 준다. */
            borderRadius: BorderRadius.all(
              Radius.circular(context.d(kBarRadius)),
            ),
            /* ⛔ **외곽선을 걷었다**(2026-09-23 사용자 요청: 「외곽선 없애고,
               글래스로 바꿔」). [SilverEdge.onWhite] 를 0.5px 로 둘렀던
               자리다 — 유리가 제 흐림으로 경계를 내므로 선이 겹친다. */
          ),
          child: Padding(
            padding: EdgeInsets.symmetric(horizontal: context.d(kBarInnerPad)),
            child: Row(
              children: [
                /* 🔴 **칸이 모두 같은 몫이다**(2026-09-23 정정, 사용자 지적:
                   「이 레퍼런스랑 너가 만든게 같아보여?」). 앞서 로고 칸에
                   `flex: 5` 를 줬는데, 그 칸이 줄을 다 먹어서 레퍼런스의
                   **고른 네 칸**과 전혀 달라 보였다. 로고가 아이콘이 된 지금
                   칸을 다르게 둘 까닭이 없다.

                   🔴 **구분선은 칸마다** 들어간다 — 레퍼런스가 그렇다. 앞서
                   가운데 둘에만 뒀던 것을 고쳤다. */
                for (final (i, entry) in _icons.entries.indexed) ...[
                  if (i > 0) _Divider(key: Key('navbar-divider-${entry.key}')),
                  Expanded(
                    child: _NavIcon(
                      key: Key('navbar-icon-${entry.key}'),
                      icon: entry.value,
                      active: entry.key == currentIndex,
                      onTap: () => onTap(entry.key),
                    ),
                  ),
                ],
                _Divider(key: const Key('navbar-divider-menu')),
                /* 마지막은 탭이 아니다 — 메뉴를 연다. 그래서 **늘 `active`
                   가 아니다.** 🔴 한때 이 칸만 회색으로 채워 뒀는데, 사용자가
                   「누르지도 않았는데 진한 사각형이 있다」고 짚었다 — 면은
                   이제 고른 칸의 표시이지 이 칸의 차림이 아니다. */
                Expanded(
                  child: _NavIcon(
                    key: const Key('navbar-icon-menu'),
                    icon: _menuIcon,
                    active: false,
                    onTap: () => onTap(menuIndex),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

}


/// 유리 막대 — 제 모양대로 **뒤를 흐린다.**
///
/// 🔴 **[ClipRRect] 안에서 흐린다.** 밖에 두면 막대 밖까지 흐려져 화면 아래가
/// 통째로 뿌옇다.
///
/// 🔴 **유리 안에 유리를 넣지 않는다**(`flutter/CLAUDE.md`) — 안의 칸들은
/// 흐림 없이 **색만** 얹는다([kNavActiveTileColor]).
class _GlassBar extends StatelessWidget {
  const _GlassBar({
    super.key,
    required this.decoration,
    required this.child,
  });

  final BoxDecoration decoration;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: decoration.borderRadius!.resolve(null),
      child: BackdropFilter(
        filter: ui.ImageFilter.blur(sigmaX: kNavBarBlur, sigmaY: kNavBarBlur),
        child: DecoratedBox(decoration: decoration, child: child),
      ),
    );
  }
}

/// 가운데 아이콘들을 가르는 가는 세로선(레퍼런스 그대로).
///
/// 🔴 **칸과 칸 사이마다 하나씩** 들어간다 — 레퍼런스가 그렇다.
class _Divider extends StatelessWidget {
  const _Divider({super.key});

  @override
  Widget build(BuildContext context) {
    /* 🔴 **높이를 직접 준다.** [Padding] 으로 위아래를 밀고 [SizedBox] 에
       **폭만** 주었더니, [Row] 가 세로로 느슨한 제약을 줘서 [ColoredBox] 가
       **높이 0** 이 됐다 — 선이 그려지긴 하는데 **아무것도 안 보인다.**
       실기기 캡처를 확대해서야 알았고, 알파를 올려도 당연히 안 보였다. */
    return SizedBox(
      /* 🔴 **물리 1픽셀을 꽉 채운다.** `1 / dpr` 로 주면 그 픽셀을 일부만
         덮어 연한 회색으로 뜬다 — 프로필의 흰 구분선에서 겪은 그것이다. */
      width: 1 / MediaQuery.devicePixelRatioOf(context),
      height: context.d(kBarDividerHeight),
      child: const ColoredBox(color: kNavDividerColor),
    );
  }
}

/// 굵기·등급·광학크기를 **한 곳에서** 준다 — 아이콘마다 다르면 줄이
/// 들쭉날쭉해진다.
Widget _navGlyph(BuildContext context, IconData icon) => Icon(
  icon,
  color: kNavOnWhite,
  size: context.d(76),
  weight: 200,
  grade: 0,
  opticalSize: 20,
);

/// 가운데 칸의 아이콘.
///
/// 🔴 **고른 자리에 옅은 판이 깔린다.** 전에는 흰 반투명 면 + 밝은 실버 두
/// 모서리(`_SelectedPlate`)로 그렸는데, 그건 **어두운 바 기준**이라 흰 막대
/// 위에서는 아무것도 안 보인다 — 메뉴 칸과 같은 회색을 쓴다.
/// 되살리려면 2026-09-23 이전 커밋에서 꺼낸다.
class _NavIcon extends StatelessWidget {
  const _NavIcon({
    super.key,
    required this.icon,
    required this.active,
    required this.onTap,
  });

  final IconData icon;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Padding(
        padding: EdgeInsets.symmetric(vertical: context.d(18)),
        child: Stack(
          alignment: Alignment.center,
          children: [
            /* 🔴 **고른 칸에만 둘레를 도는 금빛이 뜬다**(레퍼런스).
               자리는 늘 같고 이것만 들고 난다 — 아이콘 크기를 직접 바꾸면
               [Row] 가 매 프레임 다시 배치돼 이웃이 함께 흔들린다.

               🔴 **`if` 로 넣었다 뺀다.** [Opacity] 로 감추면 안 보이는 동안에도
               **초당 60번 다시 그리는 애니메이션이 칸마다 넷** 돈다. */
            if (active)
              SizedBox(
                width: context.d(kNavActiveSide),
                height: context.d(kNavActiveSide),
                child: SilverSweepBorder(
                  radius: context.d(kNavActiveSide) * 0.32,
                  color: kNavActiveSweep,
                  baseColor: kNavActiveSweepBase,
                  strokeWidth: 1.2,
                  child: const SizedBox.expand(),
                ),
              ),
            _navGlyph(context, icon),
          ],
        ),
      ),
    );
  }
}
