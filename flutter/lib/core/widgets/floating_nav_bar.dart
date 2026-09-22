import 'dart:math';

import 'package:flutter/material.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../design_scale.dart';
import 'silver_edge.dart';
import '../theme/app_theme.dart';
import '../../features/intro/presentation/brand_mark.dart';

/// 하단 바와 로고 알약의 면 색 — **진회색**(2026-09-16 사용자 지정.
/// 유리 → 검정 → 진회색 순으로 왔다).
///
/// 🔴 홈 바탕이 완전한 검정이라 바까지 검정이면 바가 안 보인다. 홈의
/// `_kSheetColor`(스쿼드 판 · 영상 분석 판)와 **같은 값**이다 — 넷이 한 켜다.
/// 하단 바·로고 알약의 면 — **반투명**이라 뒤의 빛무리가 비친다(2026-09-21).
///
/// 🔴 유리(흐림·굴절)가 아니라 **색 + 실버 테두리**다(`SilverEdge`) — 바 안에
/// 아이콘·메뉴가 들어가서 유리로 만들면 「유리 안에 유리」가 된다.
const Color kNavBarColor = Color(0x661C1C1E);

/// 바가 차지하는 높이(디자인 px). 시안 실측값이다.
const double kBottomBarHeight = 155;

/// 윗변에서 로고 자리만 아래로 파낸 한 장짜리 바.
///
/// `com.sumworship`의 하단 바를 그대로 가져왔다. 좌표는 시안 실측값이고
/// [DesignScale]이 화면 폭에 맞춰 환산한다.
///
/// 양끝은 둥글게 막히지 않는다 — 시안의 바가 화면 밖까지 나가서 어깨가 화면
/// 밖에 놓인다. 화면 안에서 둥근 것은 **로고가 앉는 홈 하나뿐이다.**
///
/// 아래로 화면 밖까지 번지므로 SafeArea *밖*에 놓아야 한다.
class FloatingNavBar extends StatelessWidget {
  const FloatingNavBar({
    super.key,
    required this.currentIndex,
    required this.onTap,
  });

  final int currentIndex;
  final ValueChanged<int> onTap;

  /// 인덱스 0(홈)은 로고 알약이 가져갔다. 남은 셋만 아이콘으로 그린다.
  ///
  /// **Material Symbols다.** Flutter가 안고 있는 `Icons`는 구형 Material
  /// Icons라 획이 두껍고 이 글리프들이 없다. 굵기·등급·광학크기는 [_NavIcon]이
  /// 한 곳에서 준다 — 아이콘마다 다르면 줄이 들쭉날쭉해진다.
  ///
  /// 글리프는 이 앱의 구획에 맞춰 골랐다. 원본(`com.sumworship`)의 것은
  /// 쇼핑백·북마크라 여기서는 뜻이 안 맞는다.
  static const _icons = {
    1: Symbols.videocam,
    // 레슨 · 코치(2026-09-15 — 축구공을 대신한다). 홈의 「레슨 · 코치」 카드가
    // 여기로 옮겨 왔다. 용병 매칭 · 내 팀은 홈의 스쿼드 판이 맡는다.
    2: Symbols.school,
    3: Symbols.id_card,
  };

  /// 탭이 아니라 메뉴를 여는 자리. 인덱스가 아니라 이 표로 가른다.
  static const menuIndex = 4;
  static const _menuIcon = Symbols.format_list_bulleted_add;

  /// 알약을 시안(290.2×145.8)에서 줄인 비율.
  static const _pillScale = 0.85;

  static double iconWidth(BuildContext context) => context.d(160);

  /// 로고 홈의 오른쪽 끝. 아이콘 줄은 여기서 시작한다.
  static double notchRight(BuildContext context) =>
      context.d(72.7) + context.d(290.2 * _pillScale) + context.d(10.2);

  /// 아이콘 중심 사이의 거리.
  ///
  /// **줄이 `spaceEvenly`라 앞뒤에도 같은 틈이 들어간다.** 오른쪽 여백만 보고
  /// 셈하면 그 틈 하나만큼 어긋난다.
  static double iconStep(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;
    final row = width - context.d(40) - notchRight(context);
    final icon = iconWidth(context);
    const slots = 4;
    return icon + (row - icon * slots) / (slots + 1);
  }

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
    final pill = Rect.fromLTWH(
      context.d(72.7),
      0,
      context.d(290.2 * _pillScale),
      context.d(145.8 * _pillScale),
    );
    // 시안이 남긴 틈: 왼쪽 9.0, 오른쪽 10.2, 아래 8.8. 위는 붙어 있다.
    final notch = _LogoNotch(
      left: pill.left - context.d(9.0),
      right: pill.right + context.d(10.2),
      depth: pill.height + context.d(8.8),
      radius: context.d(80 * _pillScale),
    );

    return SizedBox(
      height: barHeight + bottomInset,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Positioned.fill(
            // 🔴 **완전한 검정이다**(2026-09-15 사용자 요청). 전에는 흐림 유리였다 —
            // 홈 바탕을 흰색으로 바꾸자 유리 위의 흰 아이콘이 묻혔다. 검은 면을
            // 로고 홈 모양대로 자른다.
            child: ClipPath(
              clipper: notch,
              child: const ColoredBox(color: kNavBarColor),
            ),
          ),
          /* 🔴 **바 윤곽에도 실버 선**(2026-09-22, 사용자 요청). 면이
             반투명이라 뒤가 밝으면(프로필의 빛무리) 바와 그 **파낸 홈이 같은
             밝기로 읽혀 「사이가 채워진」 것처럼 보였다** — 선이 있어야 어디가
             바이고 어디가 빈 자리인지 갈린다. 알약의 테두리와 같은 은빛이다. */
          Positioned.fill(
            child: IgnorePointer(
              child: CustomPaint(painter: _NotchEdge(notch)),
            ),
          ),
          // 아이콘은 홈 오른쪽에 균등 배치하고, 세로 중심을 알약에 맞춘다.
          Positioned.fromRect(
            rect: Rect.fromLTRB(
              notch.right,
              pill.top,
              MediaQuery.sizeOf(context).width - context.d(40),
              pill.bottom,
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                for (final entry in _icons.entries)
                  _NavIcon(
                    key: Key('navbar-icon-${entry.key}'),
                    icon: entry.value,
                    active: entry.key == currentIndex,
                    onTap: () => onTap(entry.key),
                  ),
                // 넷째는 탭이 아니다 — 메뉴를 연다. 그래서 활성 표시가 없다.
                _NavIcon(
                  key: const Key('navbar-icon-menu'),
                  icon: _menuIcon,
                  active: false,
                  onTap: () => onTap(menuIndex),
                ),
              ],
            ),
          ),
          Positioned.fromRect(
            rect: pill,
            child: _LogoButton(
              key: const Key('navbar-logo'),
              onTap: () => onTap(0),
            ),
          ),
        ],
      ),
    );
  }
}

/// 윗변에서 로고 자리만 아래로 파낸 바 윤곽.
///
/// 반경은 홈의 네 모서리에 **서로 반대 방향으로** 걸린다. 입구 두 곳은
/// 바깥으로 벌어지는 오목한 필렛이고, 바닥 두 곳은 안으로 말리는 볼록한
/// 라운드다. 둥근사각형을 빼는 방식으로는 이 모양이 안 나온다 — 그쪽은
/// 입구까지 안으로 오므라들어 홈이 조여 보인다.
class _LogoNotch extends CustomClipper<Path> {
  const _LogoNotch({
    required this.left,
    required this.right,
    required this.depth,
    required this.radius,
  });

  final double left;
  final double right;
  final double depth;
  final double radius;

  @override
  Path getClip(Size size) {
    // 반경이 자리보다 크면 위 필렛과 아래 라운드가 겹쳐, 사이의 직선 구간이
    // 음수 길이가 되고 선이 되짚어 올라가며 꼬인다. 들어갈 만큼만 쓴다.
    final r = min(radius, min(depth / 2, (right - left) / 2));
    final arc = Radius.circular(r);
    // 좌·우·아래 경계는 화면 밖에 둔다.
    final outL = -r * 2;
    final outR = size.width + r;
    final outB = size.height + r;
    return Path()
      ..moveTo(outR, 0)
      ..lineTo(right + r, 0)
      ..arcToPoint(Offset(right, r), radius: arc, clockwise: false)
      ..lineTo(right, depth - r)
      ..arcToPoint(Offset(right - r, depth), radius: arc, clockwise: true)
      ..lineTo(left + r, depth)
      ..arcToPoint(Offset(left, depth - r), radius: arc, clockwise: true)
      ..lineTo(left, r)
      ..arcToPoint(Offset(left - r, 0), radius: arc, clockwise: false)
      ..lineTo(outL, 0)
      ..lineTo(outL, outB)
      ..lineTo(outR, outB)
      ..close();
  }

  @override
  bool shouldReclip(covariant _LogoNotch old) =>
      old.left != left ||
      old.right != right ||
      old.depth != depth ||
      old.radius != radius;
}

/// 활성 여부를 크기로만 말하는 아이콘.
///
/// 평상시에는 줄어들어 있고, 고른 것만 제 크기로 선다.
class _NavIcon extends StatelessWidget {
  const _NavIcon({
    super.key,
    required this.icon,
    required this.active,
    required this.onTap,
  });

  /// 평상시 크기의 비율. 활성일 때가 1.0이다.
  static const restingScale = 0.76;

  final IconData icon;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: SizedBox(
        width: FloatingNavBar.iconWidth(context),
        height: context.d(120),
        // 자리는 큰 쪽에 고정해 두고 글리프만 줄인다. 아이콘 크기를 직접
        // 바꾸면 Row가 매 프레임 다시 배치돼 이웃 아이콘들이 함께 흔들린다.
        child: AnimatedScale(
          scale: active ? 1.0 : restingScale,
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOut,
          // 굵기·등급·광학크기를 여기 한 곳에서 준다. 아이콘마다 다르면
          // 줄이 들쭉날쭉해진다.
          child: Icon(
            icon,
            color: Colors.white,
            size: context.d(76),
            weight: 200,
            grade: 0,
            opticalSize: 20,
          ),
        ),
      ),
    );
  }
}

/// 홈 안에 떠 있는 로고 알약. 누르면 홈으로 간다.
///
/// **로그인 화면에서 날아온 `SUPERSUB`가 여기 앉는다.**
class _LogoButton extends StatelessWidget {
  const _LogoButton({super.key, required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      // 알약은 몸통에서 도려낸 홈 안이라 몸통의 흐림이 닿지 않는다. 자기
      // 몫을 따로 건다.
      child: LayoutBuilder(
        builder: (context, box) {
          final radius = box.maxHeight / 2;
          // 알약이 좁아 크기를 못 박는다 — `FittedBox`가 남는 폭에 맞춰
          // 줄인다. 날아오는 동안에도 같은 방식이라 착지가 안 튄다.
          final logo = Padding(
            padding: EdgeInsets.symmetric(
              horizontal: context.d(44),
              vertical: context.d(38),
            ),
            child: FittedBox(
              child: brandHero(
                child: Text(
                  kBrandText,
                  style: BrandMark.styleFor(kBrandLandedSize, AppTheme.seed),
                ),
              ),
            ),
          );
          /* 알약도 바와 같은 면이다. 바에서 파낸 홈 안에 따로 선 조각이라
             제 면을 따로 칠한다. 🔴 **실버 테두리**로 경계를 낸다(2026-09-21) —
             면이 반투명이라 테두리가 없으면 바와 알약이 한 덩어리로 읽힌다. */
          /* 🔴 **면을 비운다**(2026-09-22, 사용자 지적: 「너무 탁한 색상」).
             바와 **같은 반투명 색**을 깔고 있어서 둘이 한 덩어리로 읽혔다 —
             알약 안은 뒤가 그대로 비쳐야 「파낸 자리」로 보인다. 형태는
             실버 테두리가 세운다. */
          return SilverEdge(
            radius: radius,
            fill: Colors.transparent,
            child: logo,
          );
        },
      ),
    );
  }
}

/// 바 윤곽을 따라 그리는 **가는 실버 선**.
///
/// 🔴 [_LogoNotch] 와 **같은 길**을 쓴다 — 따로 그리면 면과 선이 반 픽셀
/// 어긋나 홈 둘레가 두 겹으로 보인다.
class _NotchEdge extends CustomPainter {
  const _NotchEdge(this.notch);

  final _LogoNotch notch;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawPath(
      notch.getClip(size),
      Paint()
        ..style = PaintingStyle.stroke
        // 이 기기에서 그릴 수 있는 가장 얇은 선.
        ..strokeWidth = 0.5
        ..color = SilverEdge.silver.withValues(alpha: 0.55),
    );
  }

  @override
  bool shouldRepaint(_NotchEdge old) => old.notch.shouldReclip(notch);
}
