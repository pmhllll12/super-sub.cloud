import 'dart:ui' as ui;

import 'dart:math';

import 'package:flutter/material.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../design_scale.dart';
import '../theme/app_theme.dart';
import '../../features/intro/presentation/brand_mark.dart';

/// 하단 바와 로고 알약의 면 색. 유리 → 검정 → 진회색 → 반투명 흰색 →
/// **판과 같은 밝기의 불투명 회색** 순으로 왔고, 매번 사용자가 정했다.
///
/// 🔴 유리(흐림·굴절)가 아니라 **색만** 얹는다 — 바 안에 아이콘·메뉴가
/// 들어가서 유리로 만들면 「유리 안에 유리」가 된다.
///
/// 🔴 **불투명이다**(사용자 요청: 「하단바랑 로고 알약은 뒤에 안 비치게」).
/// 알약도 이 값을 쓴다 — 알약은 바에서 **파낸 홈** 안이라 둘 사이 틈만 뒤가
/// 비치고, **그 틈이 보이는 것이 알약을 알약으로 만든다.**
///
/// 🔴 **판([kSurfaceWhite])과 같아 보여야 한다**(사용자 요청: 「하단바도
/// 판이랑 똑같이 맞춰줘」). 판은 검은 바탕 위의 흰색 **반투명**이고 이쪽은
/// 불투명이라, 값을 손으로 맞춰 둔다.
///
/// ⚠️ **한 번 판(18%)에 맞춰 `0xFF2E2E2E` 로 올렸다가 사용자가 되돌렸다**
/// (2026-09-22: 「하단바는 방금 바꾸기 전으로 색상 되돌리고」). 지금은 **판보다
/// 한 단 어둡고, 그게 맞다** — 바는 목록 위에 뜨는 층이라 판과 같은 밝기면
/// 경계가 사라진다.
///
/// 🔴 다시 맞출 일이 생기면 규칙은 이렇다: 판이 `Color(0xAAFFFFFF)` 면 바는
/// `Color(0xFFAAAAAA)` — **알파 바이트를 세 색 자리에 그대로** 옮긴다(흰색을
/// 검정 위에 알파 `a` 로 얹으면 결과가 `255 * a` 라서).
///
/// ⚠️ 이 맞춤은 **바탕이 검정일 때만** 성립한다. 프로필 바탕을 바꾸면 불투명인
/// 이쪽은 안 따라간다.
///
/// ⚠️ 홈의 `_kSheetColor`(스쿼드 판 · 영상 분석 판)와 **같은 값이었는데 갈렸다.**
/// 홈 판까지 맞출지는 홈을 만질 때 함께 정한다.
const Color kNavBarColor = Color(0x8C1A1A1A);

/// 하단 바 · 로고 알약의 **흐림 세기**(2026-09-22 사용자 요청: 「둘 다
/// 글래스로 바꾸고, 블러 살짝만 … 20퍼센트만」).
///
/// ⚠️ **「20%」를 무엇의 20%로 읽을지 애매해서 6 으로 뒀다** — 홈의 유리
/// 알약이 7.2 이고, 그보다 한 끗 옅은 값이다. 더 흐리게/덜 흐리게는 이 한 줄.
///
/// 🔴 **면이 같이 반투명이 됐다**(`0xFF1A1A1A` → `0x8C1A1A1A`). 흐림만
/// 주고 면을 불투명으로 두면 **뒤가 안 비쳐 흐림이 하나도 안 보인다.**
const double kNavBarBlur = 6;

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
            /* 면 하나를 로고 홈 모양대로 잘라 깐다 — 색은 [kNavBarColor].
               🔴 **유리다**(2026-09-22 사용자 요청) — 잘라 낸 그 모양 **안**
               에서만 뒤를 흐린다. `ClipPath` 밖에 두면 파낸 홈까지 같이
               흐려져 알약 자리가 안 드러난다. */
            child: ClipPath(
              clipper: notch,
              child: BackdropFilter(
                filter: ui.ImageFilter.blur(
                  sigmaX: kNavBarBlur,
                  sigmaY: kNavBarBlur,
                ),
                child: const ColoredBox(color: kNavBarColor),
              ),
            ),
          ),
          /* ⛔ **바 윤곽의 실버 선을 걷었다**(2026-09-22 정정, 사용자 요청:
             「하단바 로고 알약 버튼까지 외곽선 다 없애줘」).

             붙였던 까닭은 「면이 반투명이라 뒤가 밝으면 바와 파낸 홈이 같은
             밝기로 읽힌다」였다. 🔴 **그 전제를 같이 걷었다** — 면을 불투명
             [kNavBarColor] 로 바꿨으므로 홈(파낸 자리)만 뒤가 비치고 바는
             안 비친다. 선 없이도 경계가 선다.

             🔴 **선만 되살리지 말 것** — 면을 반투명으로 되돌릴 때 같이
             되살려야 뜻이 맞는다. 그리던 `_NotchEdge`(같은 [_LogoNotch] 길을
             `PaintingStyle.stroke` 로 `SilverEdge.barLine` 굵기 0.5 로 긋던
             `CustomPainter`)는 지웠다 — `flutter analyze` 가 안 쓰는 선언을
             경고한다. 되살릴 땐 이 커밋에서 되꺼낸다. */
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
        child: Stack(
          alignment: Alignment.center,
          children: [
            /* 🔴 **고른 자리에만 판이 뜬다**(2026-09-22, 사용자 요청 + 레퍼런스
               두 장). 아이콘만 커지던 것으로는 **어디에 들어와 있는지**가
               약했다. 판은 아래 [_SelectedPlate] 가 그린다. */
            if (active)
              SizedBox(
                width: context.d(128),
                height: context.d(104),
                child: const CustomPaint(painter: _SelectedPlate()),
              ),
            AnimatedScale(
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
          ],
        ),
      ),
    );
  }
}

/// 고른 아이콘 뒤에 깔리는 판 — **두 모서리에만 실버가 걸린다**
/// (2026-09-22, 사용자가 보낸 레퍼런스 두 장).
///
/// 🔴 **네 모서리를 다 두르지 않는다.** 다 두르면 그냥 「테두리 친 상자」이고,
/// 레퍼런스의 인상은 **서로 마주 보는 두 모서리에서만 빛이 흐르는** 것이다.
///
/// 🔴 **선을 길이로 자른다**(`PathMetric`) — 모서리마다 각도가 달라서 각도로
/// 자르면 두 토막의 길이가 갈린다. `SilverSweepBorder` 에서 배운 것과 같다.
class _SelectedPlate extends CustomPainter {
  const _SelectedPlate();

  /// 판의 면 — 아주 옅게. 🔴 진하게 깔면 바에서 **네모가 떠 보이고**,
  /// 레퍼런스의 「빛만 남은」 인상이 사라진다.
  static const Color _fill = Color(0x14FFFFFF);

  /// 밝은 실버. 순백은 어두운 바에서 형광등처럼 튄다.
  static const Color _silver = Color(0xFFE8F0F4);

  /// 빛이 걸리는 두 자리 — 테두리 길이에 대한 **중심 위치**다.
  ///
  /// `Path.addRRect` 는 **오른쪽 변 가운데**에서 시작해 시계 방향으로 돈다.
  /// 그래서 0.125 언저리가 오른쪽 아래 모서리, 0.625 가 왼쪽 위 모서리다 —
  /// **마주 보는 두 모서리**다.
  static const List<double> _at = [0.125, 0.625];

  /// 한 토막이 차지하는 길이의 몫.
  ///
  /// 🔴 **짧게 둔다**(0.17 → 0.13). 선이 얇아진 만큼 길면 **가는 실이 길게
  /// 늘어진** 것처럼 보인다 — 모서리를 감싸는 만큼만 남긴다.
  static const double _span = 0.13;

  static const int _segments = 40;

  @override
  void paint(Canvas canvas, Size size) {
    final r = size.shortestSide * 0.34;
    final rect = Offset.zero & size;
    final rrect = RRect.fromRectAndRadius(rect.deflate(1), Radius.circular(r));

    canvas.drawRRect(rrect, Paint()..color = _fill);

    final metrics = (Path()..addRRect(rrect)).computeMetrics().toList();
    if (metrics.isEmpty) return;
    final m = metrics.first;
    final len = m.length;
    if (len <= 0) return;

    final stroke = Paint()
      ..style = PaintingStyle.stroke
      /* 🔴 **아주 얇다**(2026-09-22, 사용자 요청: 「훨씬 더 샤프하게 두께
         줄여서 좀 세련되게」). 1.4 → 0.7. 굵으면 「그어 놓은 선」이고,
         얇아야 **빛이 모서리를 스친 자국**으로 읽힌다. */
      ..strokeWidth = 0.7
      // 🔴 맞대는 끝이다 — 둥근 끝은 이웃 조각과 겹쳐 두 번 칠해지고
      //    그 마디가 「잘린 프레임」으로 보인다(실버 테두리에서 겪었다).
      ..strokeCap = StrokeCap.butt;

    for (final centre in _at) {
      for (var i = 0; i < _segments; i += 1) {
        final u0 = i / _segments;
        final u1 = (i + 1) / _segments;
        // 양 끝에서 0 이 되는 곡선 — 빛이 툭 끊기지 않고 스며 사라진다.
        final sn = sin(pi * (u0 + u1) / 2);
        final a = sn * sn;
        if (a <= 0.01) continue;
        var t0 = (len * (centre - _span / 2 + _span * u0)) % len;
        var t1 = (len * (centre - _span / 2 + _span * u1)) % len;
        stroke.color = _silver.withValues(alpha: a);
        if (t1 >= t0) {
          canvas.drawPath(m.extractPath(t0, t1), stroke);
        } else {
          canvas.drawPath(m.extractPath(t0, len), stroke);
          canvas.drawPath(m.extractPath(0, t1), stroke);
        }
      }
    }
  }

  @override
  bool shouldRepaint(_SelectedPlate old) => false;
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
      /* 🔴 **테두리는 없고 면은 [kNavBarColor] 다**(2026-09-22 정정, 사용자
         지적: 「하단바와 알약 버튼 사이에 벌어져 있는 부분들을 대체 왜
         채워놓은거야?」).

         🔴 **면까지 비웠던 것이 그 지적의 원인이다.** 알약은 바에서 **파낸
         홈** 안에 앉는데, 면이 없으면 알약 자리와 그 둘레의 홈이 **똑같이
         뒤가 비쳐** 한 덩어리 구멍으로 읽힌다 — 사이의 틈이 사라진 것을
         「채웠다」로 보신 것이다. 알약이 제 면을 가져야 그 틈이 다시 난다.

         🔴 **바와 같은 값**이다 — 알약은 홈 안이라 바에 겹치지 않고 **뒤를
         직접** 깔고 앉으므로, 같은 알파를 써도 둘 사이 틈(알파 0)이 셋 중
         가장 어둡다. 그 차이가 틈을 보이게 한다. 값을 갈라 놓으면 알약이
         바에서 떠 보인다. */
      child: LayoutBuilder(
        // 🔴 **바와 같은 유리다** — 둘이 한 재질이어야 알약이 바에서 안 뜬다.
        builder: (context, box) => ClipRRect(
          // 알약은 좌우가 반원인 스타디움 — 높이의 절반이 반경이다.
          borderRadius: BorderRadius.circular(box.maxHeight / 2),
          child: BackdropFilter(
            filter: ui.ImageFilter.blur(
              sigmaX: kNavBarBlur,
              sigmaY: kNavBarBlur,
            ),
            child: ColoredBox(
              color: kNavBarColor,
              // 알약이 좁아 크기를 못 박는다 — `FittedBox`가 남는 폭에 맞춰
              // 줄인다. 날아오는 동안에도 같은 방식이라 착지가 안 튄다.
              child: Padding(
                padding: EdgeInsets.symmetric(
                  horizontal: context.d(44),
                  vertical: context.d(38),
                ),
                child: FittedBox(
                  child: brandHero(
                    child: Text(
                      kBrandText,
                      style: BrandMark.styleFor(
                        kBrandLandedSize,
                        AppTheme.seed,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
