import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../../features/auth/presentation/session_controller.dart';
import '../design_scale.dart';
import 'silver_edge.dart';
import 'silver_sweep_border.dart';

/// 막대의 면 — 🔴 **완전한 흰색이다 (2026-09-23 세 번째 정정, 사용자 요청:
/// 「하단 바 그냥 완전 흰색으로 바꾸고」).**
///
/// 유리 → 검정 → 진회색 → 반투명 흰색 → 불투명 회색 → 흰색 → 유리 →
/// **흰색** 순으로 왔고, 매번 사용자가 정했다.
///
/// ⚠️ **흐림(`kNavBarBlur` 9)을 다시 걷었다** — 면이 불투명해서 흐릴 뒤가
/// 없다. 유리로 되돌리는 날 같이 되살린다.
///
/// 🔴 **경계는 [SilverEdge.onWhite] 가 낸다** — 흰 면 위에서는 밝은 은빛
/// ([SilverEdge.silver])이 흰색에 붙어 사라진다. 홈의 영상 분석 판과 **같은
/// 값을 나눠 쓴다.**
const Color kNavBarColor = Color(0xFFFFFFFF);

/// 막대 아래로 지는 그림자(2026-09-23 사용자 요청: 「그림자 자연스럽게 줘.
/// 아래쪽에 그림자 자연스럽게」).
///
/// 🔴 **아래로만 진다.** 사방으로 퍼뜨리면 막대가 「빛나는 판」이 되고,
/// 떠 있는 것으로 안 읽힌다 — 위에서 빛이 오는 것처럼 아래로만 흘린다.
///
/// 🔴 **[ClipRRect] 안에 두지 않는다** — 자르면 그림자가 막대 모양대로
/// 잘려 **아예 안 보인다.**
const List<BoxShadow> kNavBarShadow = [
  // 넓고 옅게 — 「떠 있다」를 만드는 쪽.
  BoxShadow(color: Color(0x40000000), blurRadius: 26, offset: Offset(0, 10)),
  // 좁고 진하게 — 막대 바로 아래에 닿는 그늘.
  BoxShadow(color: Color(0x26000000), blurRadius: 8, offset: Offset(0, 3)),
];

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
///
/// 🔴 **밝은 금빛(`#E6D5AE`)에서 한 단 내렸다** — 막대가 흰색이 되면서 밝은
/// 쪽은 흰 면에 붙어 사라진다. 어두운 막대에서는 **밝을수록** 보였는데 흰
/// 막대에서는 **진할수록** 보인다 — 막대 면을 갈면 이 값도 같이 본다.
const Color kNavActiveSweep = Color(0xFFA8894A);

/// 빛이 지나가지 않는 동안에도 남는 바닥 선 — 없으면 빛이 없는 쪽 모서리가
/// 통째로 사라진다.
const Color kNavActiveSweepBase = Color(0x3DA8894A);

/// 고른 칸의 한 변 — 둥근 **정사각형**이다(레퍼런스).
const double kNavActiveSide = 118;

/// 흰 막대 위의 아이콘 — 바탕이 밝으므로 **검정**이다.
const Color kNavOnWhite = Color(0xFF17181A);

/// 칸 사이 세로선.
///
/// ⚠️ **알파를 두 번 올렸다** — 물리 1픽셀짜리 선이라 낮은 알파로는 실기기에서
/// 안 보인다. 굵히지 않고 알파만 올린다 — 굵으면 「그어 놓은 선」이 되고,
/// 레퍼런스의 인상은 가는 실이다. 막대 면을 따라 흰색 ↔ 검정으로 뒤집힌다.
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
///
/// ⚠️ 54 → **118** 로 한 번 더 좁혔다(같은 날, 「바 자체가 좌우로 너무 길어」).
///
/// 🔴 **118 → 202 (2026-09-25).** 칸이 **다섯에서 넷으로** 줄면서 사용자가
/// 그만큼 좁히라고 정했다: 「5개에서 4개로 줄였으니 가운데 없애고 그만큼
/// 좌우 폭 줄이자」. 844 × 4/5 = 675 폭이 되도록 (1080 − 675) / 2 로 잡았다.
/// 🔴 **칸 수를 또 바꾸면 이 값을 같이 본다.**
const double kBarSideMargin = 202;

/// 막대가 화면 아래(안전 영역 위)에서 뜨는 거리.
const double kBarBottomGap = 18;

/// 막대 위로 남기는 자리 — 이만큼이 판과 막대 사이 틈이 된다.
const double kBarTopGap = 12;

/// 막대 네 모서리의 반경.
///
/// ⚠️ 52 → **34**(2026-09-23 사용자 요청: 「모서리들 너무 곡선이다. 좀 덜
/// 주자」). 🔴 **더 줄일 때는 [kBarInnerPad] 를 같이 본다** — 그 여백은
/// 모서리 곡선이 파고드는 만큼을 비켜 주려고 있는 것이라, 곡선이 얕아지면
/// 남아도는 여백이 된다.
const double kBarRadius = 34;

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
///
/// 🔴 **세션을 스스로 본다 ([ConsumerWidget], 2026-09-25).** 맨 오른쪽 칸이
/// **로그인이냐 로그아웃이냐**를 가르기 때문이다 — 그 한 가지 때문에 화면
/// 넷에게 `loggedIn` 을 받아 오게 하면 넷이 다 같은 줄을 적어야 한다.
class FloatingNavBar extends ConsumerWidget {
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
  ///
  /// ⛔ **2번(레슨 · 코치, `Symbols.school`)을 걷었다** (2026-09-25 사용자
  /// 지시: 「하단 바의 중앙에 있는 레슨 버튼은 없애고」). 그 자리는 아직 어느
  /// 화면에도 안 붙어 있어서 눌러도 「준비 중입니다」만 떴다.
  /// 🔴 **번호를 다시 매기지 않았다** — 3번(프로필)이 그대로 3번이라, 화면
  /// 넷의 `onTap` 갈래를 건드릴 일이 없다.
  static const _icons = {
    0: Symbols.home_app_logo,
    1: Symbols.videocam,
    3: Symbols.id_card,
  };

  /// 맨 오른쪽 칸 — 🔴 **로그인 / 로그아웃이다** (2026-09-25 사용자 지시).
  ///
  /// ⛔ **여기 있던 「메뉴」 칸(`menuIndex` 4 · `format_list_bulleted_add`)을
  /// 걷었다.** 그 칸은 바 위로 판을 띄워 크레딧 · 코치 · 설정 · 로그아웃 넷을
  /// 폈는데, 그중 **셋이 아직 「준비 중입니다」**였다 — 실제로 하는 일은
  /// 로그아웃 하나였고 그걸 **두 번 눌러야** 닿았다. 되살리려면 2026-09-25
  /// 이전 커밋의 `bar_menu.dart` 를 꺼낸다.
  static const _authIcons = (out: Symbols.logout, into: Symbols.login);

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
  Widget build(BuildContext context, WidgetRef ref) {
    final loggedIn = ref.watch(sessionControllerProvider) is SessionLoggedIn;
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
            boxShadow: kNavBarShadow,
            /* 🔴 **완전한 반원 끝이 아니다.** 한 번 스타디움(반경 = 높이)으로
               뒀더니 **메뉴 칸이 그 곡선에 잘렸다** — 칸은 네모라서 양 끝의
               반원 안으로 들어가지 못한다. 반경을 높이의 3할쯤으로 내리고,
               아래 가로 안여백이 남은 곡선을 비켜 준다. */
            borderRadius: BorderRadius.all(
              Radius.circular(context.d(kBarRadius)),
            ),
            /* 🔴 **가장 얇은 은빛 선 하나**(사용자 요청: 「외곽선 제일 얇은
               선으로 실버 색상」). 홈의 영상 분석 판과 **같은 값**이다 —
               갈리면 한 화면에 두 굵기·두 색이 보인다. */
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
                _Divider(key: const Key('navbar-divider-auth')),
                /* 🔴 **마지막은 탭이 아니라 그 자리에서 세션을 끝낸다.**
                   어느 화면에서 눌러도 뜻이 하나라 [onTap] 으로 올려 보내지
                   않는다 — 올려 보내면 화면 넷이 같은 줄을 적어야 한다.
                   🔴 **늘 `active` 가 아니다** — 면은 「지금 보고 있는 칸」의
                   표시이지 이 칸의 차림이 아니다.

                   ⚠️ 로그아웃한 뒤 **어디로 갈지는 여기서 안 정한다** —
                   `app_router.dart` 의 `redirect` 가 로그인 화면으로 보낸다. */
                Expanded(
                  child: _NavIcon(
                    key: const Key('navbar-icon-auth'),
                    icon: loggedIn ? _authIcons.out : _authIcons.into,
                    active: false,
                    /* ⚠️ 로그아웃 상태에서는 **할 일이 없다** — 바가 있는
                       화면은 전부 로그인 뒤에만 보이고, 라우터가 이미 로그인
                       화면으로 보낸 뒤다. 아이콘만 제 뜻을 지킨다. */
                    onTap: loggedIn
                        ? ref.read(sessionControllerProvider.notifier).logout
                        : () {},
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

/// 굵기·등급·광학크기를 **한 곳에서** 준다 — 아이콘마다 다르면 줄이
/// 들쭉날쭉해진다.
///
/// 🔴 **고른 칸의 아이콘은 금빛이다** (2026-09-24 사용자 요청: 「하단바 선택된
/// 아이콘도 똑같이 세련된 골드 색상으로」). **둘레를 도는 빛과 같은 값**
/// ([kNavActiveSweep])을 쓴다 — 테는 금빛인데 글리프만 검정이면 한 칸 안에서
/// 색이 갈린다. 🔴 **테 색을 갈면 여기도 같이 간다.**
Widget _navGlyph(BuildContext context, IconData icon, {bool active = false}) =>
    Icon(
      icon,
      color: active ? kNavActiveSweep : kNavOnWhite,
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
            _navGlyph(context, icon, active: active),
          ],
        ),
      ),
    );
  }
}
