import 'package:flutter/material.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../design_scale.dart';
import 'silver_edge.dart';

/// 막대의 면 — 🔴 **흰색이다 (2026-09-23, 사용자 요청 + 레퍼런스).**
///
/// 유리 → 검정 → 진회색 → 반투명 흰색 → 불투명 회색 → **흰색** 순으로 왔고,
/// 매번 사용자가 정했다. 마지막 갈이에서 바가 **한 덩이 둥근 막대**로 다시
/// 짜이면서 면도 레퍼런스대로 갔다.
///
/// 🔴 **경계는 [SilverEdge.onWhite] 가 낸다.** 흰 면 위에서는 밝은 은빛
/// ([SilverEdge.silver])이 흰색에 붙어 사라진다 — 홈의 영상 분석 판에서
/// 가장자리 픽셀을 재서 확인한 그것이다.
///
/// ⚠️ **걷은 것 둘** — 흐림(`kNavBarBlur` 6)과, 판([kSurfaceWhite])에 밝기를
/// 맞추던 규칙(「판이 `0xAAFFFFFF` 면 바는 `0xFFAAAAAA`」). 앞은 면이
/// 불투명해서 흐릴 뒤가 없고, 뒤는 **바탕이 검정일 때만** 성립하던 것이라
/// 흰 면에서는 뜻이 없다. 반투명으로 되돌리는 날 둘 다 같이 본다.
const Color kNavBarColor = Color(0xFFFFFFFF);

/// 메뉴 칸의 면 — 레퍼런스의 마지막 칸(회색으로 채운 타일) 자리다.
const Color kNavMenuTileColor = Color(0xFFE9EDEE);

/// 흰 막대 위의 아이콘·글자.
const Color kNavOnWhite = Color(0xFF17181A);

/// 가운데 아이콘들을 가르는 세로선.
///
/// ⚠️ **15%(`0x26`)로 뒀다가 올렸다** — 물리 1픽셀짜리 선이라 그 알파로는
/// 실기기에서 **아예 안 보였다**(확대해서 확인했다). 굵히지 않고 알파만 올린다 —
/// 굵으면 「그어 놓은 선」이 되고, 레퍼런스의 인상은 가는 실이다.
const Color kNavDividerColor = Color(0x4517181A);

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
const double kBarSideMargin = 54;

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
        child: DecoratedBox(
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
            /* 🔴 **경계는 이 선 하나다**(사용자 요청: 「하단바 외곽선에 세련된
               실버 색상」). 흰 면이라 [SilverEdge.silver] 는 안 보인다 —
               홈의 영상 분석 판과 **같은 값**을 나눠 쓴다. */
            border: Border.all(
              color: SilverEdge.onWhite,
              width: SilverEdge.onWhiteWidth,
            ),
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
                // 마지막은 탭이 아니다 — 메뉴를 연다. 그래서 활성 표시가 없다.
                Expanded(
                  child: _MenuTile(
                    key: const Key('navbar-icon-menu'),
                    icon: _menuIcon,
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

/// 마지막 칸 — 메뉴를 연다. 레퍼런스의 **회색으로 채운 타일** 자리다.
///
/// 🔴 **탭이 아니라 메뉴다.** 활성 표시를 두지 않는다 — 여기 「들어와 있는」
/// 상태가 없다.
class _MenuTile extends StatelessWidget {
  const _MenuTile({super.key, required this.icon, required this.onTap});

  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Padding(
        padding: EdgeInsets.symmetric(vertical: context.d(18)),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: kNavMenuTileColor,
            borderRadius: BorderRadius.all(Radius.circular(context.d(40))),
          ),
          child: Center(child: _navGlyph(context, icon)),
        ),
      ),
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
            /* 자리는 늘 같고 판만 들고 난다 — 아이콘 크기를 직접 바꾸면
               [Row] 가 매 프레임 다시 배치돼 이웃이 함께 흔들린다. */
            Positioned.fill(
              child: AnimatedOpacity(
                opacity: active ? 1 : 0,
                duration: const Duration(milliseconds: 180),
                curve: Curves.easeOut,
                child: Padding(
                  padding: EdgeInsets.symmetric(
                    horizontal: context.d(kBarInnerPad),
                  ),
                  child: DecoratedBox(
                    /* 🔴 **채우지 않고 테만 두른다**(레퍼런스의 첫 칸이 그렇다).
                       채우면 메뉴 칸과 **같은 모양**이 되어 「고른 것」과
                       「메뉴」가 안 갈린다. */
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.all(
                        Radius.circular(context.d(40)),
                      ),
                      border: Border.all(
                        color: SilverEdge.onWhite,
                        width: SilverEdge.onWhiteWidth,
                      ),
                    ),
                  ),
                ),
              ),
            ),
            _navGlyph(context, icon),
          ],
        ),
      ),
    );
  }
}
