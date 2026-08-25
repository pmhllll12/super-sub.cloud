import 'package:flutter/material.dart';
import 'package:material_symbols_icons/symbols.dart';

import '../design_scale.dart';
import 'glass_surface.dart';

/// 하단 바 넷째 아이콘에서 열리는 메뉴 — **바 바로 위에 가로로** 선다.
///
/// `com.sumworship`의 것을 그대로 가져왔다. 화면 한복판에 모여 있다가
/// 용수철처럼 양옆으로 퍼진다. 퍼지는 폭은 바 아이콘의 칸 간격 그대로다 —
/// 바에서 떨어져 나온 줄로 읽혀야 한다.
class BarMenu extends StatelessWidget {
  const BarMenu({
    super.key,
    required this.open,
    required this.loggedIn,
    required this.step,
    required this.onPick,
  });

  /// 0이면 닫힘, 1이면 다 열림. 밖에서 몰고 온다.
  final Animation<double> open;

  /// 지금 로그인 상태인가. 로그인·로그아웃은 함께 설 수 없다.
  final bool loggedIn;

  /// 칸 중심 사이의 거리. 바 아이콘과 같은 값을 받는다.
  final double step;

  final ValueChanged<BarMenuItem> onPick;

  /// 한 칸의 한 변(목업 px).
  static const double _boxDesign = 118;

  /// 모서리 반지름 ÷ 한 변.
  static const double _radiusRatio = 0.3;

  /// 퍼지는 폭 ÷ 바 아이콘 칸 간격.
  ///
  /// 바와 똑같이(1.0) 뒀더니 칸 사이가 너무 벌어졌다 — 바는 아이콘만 있는데
  /// 여기는 상자가 있어, 같은 간격이라도 더 멀어 보인다.
  static const double _spreadRatio = 0.8;

  /// 닫혀 있어도 이만큼은 자리를 잡아 둔다 — 열릴 때 바가 밀리지 않는다.
  static double heightOf(BuildContext context) => context.d(_boxDesign);

  /// 지금 화면에 설 항목. **로그인·로그아웃이 맨 오른쪽**이고, 상태에 따라
  /// 둘 중 하나만 선다.
  List<BarMenuItem> itemsFor(bool loggedIn) => [
        BarMenuItem.credits,
        BarMenuItem.coach,
        BarMenuItem.settings,
        loggedIn ? BarMenuItem.logout : BarMenuItem.login,
      ];

  @override
  Widget build(BuildContext context) {
    final items = itemsFor(loggedIn);
    final box = context.d(_boxDesign);
    return AnimatedBuilder(
      animation: open,
      builder: (context, _) {
        // 다 닫혔으면 아무것도 세우지 않는다 — 유리는 안 보여도 뒤를 떠 간다.
        if (open.value == 0) {
          return SizedBox(width: double.infinity, height: box);
        }
        // **자리는 용수철로, 밝기는 곧게.** 밝기까지 튀게 하면 깜빡인다.
        //
        // `elasticOut`은 안 된다 — 진행 10%에 이미 목표까지 튀어나가고 그 뒤로
        // 더 나갔다 되돌아온다. 눈에 남는 것은 되돌아오는 쪽이라 **밖에서
        // 가운데로 오는 것**으로 읽힌다. `easeOutBack`은 가운데에서 곧게
        // 퍼져 끝에서 한 번만 살짝 넘친다.
        final spread = Curves.easeOutBack.transform(open.value.clamp(0.0, 1.0));
        final shown = Curves.easeOut.transform(
          (open.value / 0.35).clamp(0.0, 1.0),
        );
        // **폭을 다 써야 한다.** 상자가 내용만큼만 넓으면 좌우로 갈라선 칸이
        // 상자 밖으로 나가, 그려져도 안 눌린다.
        return SizedBox(
          width: double.infinity,
          height: box,
          child: Stack(
            alignment: Alignment.center,
            children: [
              for (var i = 0; i < items.length; i++)
                Transform.translate(
                  // 한복판을 0으로 놓고 좌우로 갈라선다.
                  offset: Offset(
                    (i - (items.length - 1) / 2) * step * _spreadRatio * spread,
                    0,
                  ),
                  child: Opacity(
                    opacity: shown,
                    child: _box(context, items[i], box),
                  ),
                ),
            ],
          ),
        );
      },
    );
  }

  Widget _box(BuildContext context, BarMenuItem item, double side) {
    return SizedBox.square(
      dimension: side,
      child: GlassSurface(
        borderRadius: BorderRadius.circular(side * _radiusRatio),
        child: GestureDetector(
          key: Key('barmenu-${item.name}'),
          behavior: HitTestBehavior.opaque,
          onTap: () => onPick(item),
          // 굵기·등급·광학크기는 하단 바 아이콘과 같다.
          child: Icon(
            item.icon,
            color: Colors.white,
            size: side * 0.46,
            weight: 200,
            grade: 0,
            opticalSize: 20,
          ),
        ),
      ),
    );
  }
}

/// 메뉴에 서는 것들.
enum BarMenuItem {
  credits(Symbols.confirmation_number, '분석 크레딧'),
  coach(Symbols.school, '레슨 · 코치'),
  settings(Symbols.settings, '설정'),
  login(Symbols.login, '로그인'),
  logout(Symbols.logout, '로그아웃');

  const BarMenuItem(this.icon, this.label);

  final IconData icon;
  final String label;
}
