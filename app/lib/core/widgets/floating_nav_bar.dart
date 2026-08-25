import 'dart:math';
import 'dart:ui';

import 'package:flutter/foundation.dart' show ValueListenable;
import 'package:flutter/material.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../design_scale.dart';
import '../theme/app_theme.dart';
import '../../features/intro/presentation/brand_mark.dart';
import 'glass_surface.dart';
import 'refractive_glass.dart';

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
    this.refraction,
  });

  final int currentIndex;
  final ValueChanged<int> onTap;

  /// 유리 세기. null이면 셰이더를 아예 쓰지 않고 흐림 유리로 그린다.
  /// 0과 null은 뜻이 다르다 — 0은 "굴절 중, 분산만 없음"이고 null은 "이
  /// 화면은 이 유리를 안 씀"이다.
  final ValueListenable<double>? refraction;

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
    2: Symbols.sports_soccer,
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
            child: ClipPath(
              clipper: notch,
              // 유리는 홈 모양대로 잘린다. ClipPath가 없으면 BackdropFilter가
              // 화면 전체에 걸린다.
              child: refraction == null
                  ? BackdropFilter(
                      filter: ImageFilter.blur(
                        sigmaX: kGlassBlur,
                        sigmaY: kGlassBlur,
                      ),
                      child: ColoredBox(color: kGlassFill),
                    )
                  : RefractiveGlass(
                      notch: GlassNotch(
                        left: notch.left,
                        right: notch.right,
                        depth: notch.depth,
                        radius: notch.radius,
                      ),
                      strength: refraction!,
                    ),
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
              refraction: refraction,
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
  const _LogoButton({super.key, required this.onTap, this.refraction});

  final VoidCallback onTap;
  final ValueListenable<double>? refraction;

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
          if (refraction == null) {
            return GlassSurface(
              borderRadius: BorderRadius.circular(radius),
              child: logo,
            );
          }
          return ClipRRect(
            borderRadius: BorderRadius.circular(radius),
            child: RefractiveGlass(
              notch: GlassNotch(
                left: 0,
                right: box.maxWidth,
                depth: box.maxHeight,
                radius: radius,
                pill: true,
              ),
              strength: refraction!,
              child: logo,
            ),
          );
        },
      ),
    );
  }
}
