import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../features/profile/presentation/widgets/player_card_view.dart'
    show kCardBg;

/// 화면 바탕 — **흰 바탕 위로 카드의 두 색이 가장자리에서 번져 든다**
/// (2026-09-22 사용자 요청 + 레퍼런스 이미지).
///
/// 🔴 **사선으로 가르던 것을 걷었다 — 두 번 틀렸다.**
///
/// | 회 | 무엇을 했나 | 왜 틀렸나 |
/// |---|---|---|
/// | 1 | [CardSideSmoke] 를 화면 전체에 | 두 색이 **겹쳐 섞여** 탁한 제3의 색이 됐다 |
/// | 2 | 사선 그라디언트로 **갈라** 각자 제 구역 | **경계선이 그대로 보였고**, 화면이 「두 색으로 칠한 판」이 됐다 |
///
/// 🔴 **레퍼런스의 정체는 「경계 없는 번짐」이다.** 바탕은 거의 **검정**이고,
/// 색은 **가장자리에서 아주 넓게** 배어들 뿐 어디에도 선이 없다.
///
/// 🔴 **그래서 빛무리의 중심을 화면 밖에 둔다.** 안에 두면 아무리 부드러워도
/// **동그란 덩어리**로 읽힌다(2번의 실패와 같은 종류다) — 밖에 두면 보이는
/// 것은 **꼬리뿐**이라 「어디선가 번져 온다」가 된다.
///
/// 🔴 **둘을 마주 보는 쪽에 둔다** — 그래야 서로 안 겹쳐 「각자 제 영역」이
/// 지켜진다(사용자 정정: 「서로의 영역에만 있어」).
class ScreenTint extends StatelessWidget {
  /// 카드의 두 색이 검은 바탕에 번져 드는 본래의 바탕 — **프로필이 쓴다.**
  const ScreenTint({super.key, required this.a, required this.b})
    : base = const Color(0xFF000000),
      glows = _darkGlows;

  /// 🔴 **홈 전용 — 카드 색을 안 쓴다**(2026-09-23 사용자 요청: 「그냥
  /// 홈페이지는 카드에서 뽑아낸 2가지 색상 말고」).
  ///
  /// 누가 보든 **같은 한 벌**이다. 그래서 글자 대비를 한 번만 맞추면 되고,
  /// 카드 색이 진한 사람에게서 바탕이 탁해지는 일도 없다.
  ///
  /// 🔴 **색은 [kCardBg] 그대로다**(사용자가 색을 집어 줬는데 **앱에 이미
  /// 있던 값**이었다 — 기본 카드 바탕이자 카드 편집기의 첫 견본이다).
  /// 새 상수를 만들지 않는다 — 두 벌이 되면 한쪽만 바뀐다.
  ///
  /// ⚠️ **살구빛이었다 (2026-09-23 같은 날 정정).** 처음엔 레퍼런스 그림에서
  /// 뽑은 크림→살구빛이었는데, 사용자가 **앱 초록으로 바꿨다**. 빛무리 자리는
  /// 그대로 두고 색과 세기만 갈았다.
  ///
  /// 🔴 **밝은 쪽으로 뒤집힌 갈래라 빛무리 자리도 다르다.** 본래 것은 색이
  /// **아래·옆**에서 배어 들지만(검은 바탕을 덜 가리려고), 이쪽은 **위가
  /// 물들고 아래로 갈수록 희어진다** — 화면 아래 절반은 흰 판이 차지하므로
  /// 거기서 색이 빠져야 판과 안 부딪힌다.
  const ScreenTint.mint({super.key})
    : a = kCardBg,
      b = _kMintGlowSoft,
      base = _kMintBase,
      glows = _mintGlows;

  /// 밝은 갈래의 바탕색 — 🔴 **홈이 [AuroraBackground] 에도 같은 값을 준다.**
  /// 그쪽은 하단 바 뒤까지 칠하므로, 다르면 화면 아래에 다른 색 띠가 남는다.
  static const Color mintBase = _kMintBase;

  /// 카드 바탕색 · 자국색. [ScreenTint.mint] 에서는 고정된 초록 둘이다.
  final Color a;
  final Color b;

  /// 색이 얹히기 전의 바탕.
  final Color base;

  /// `(자국색인가, 중심 x, 중심 y, 반경, 세기)` 목록 — 아래 두 상수 중 하나.
  final List<(bool, double, double, double, double)> glows;

  /// 🔴 **상태 바 글자의 밝기를 이 위젯이 정한다**(2026-09-22, 사용자 지적:
  /// 「스크롤 하면 상단바의 검은색 바가 튀어나와」).
  ///
  /// 바탕이 흰색이 되면서 안드로이드가 **시계·배터리를 읽히게 하려고 상태 바
  /// 뒤에 검은 막**을 깔았다. 이 앱은 그 막을 `MainActivity.kt` 에서 껐는데,
  /// 그건 「막을 깔지 마라」일 뿐이고 **글자 색은 여전히 밝은 쪽**이라 최신
  /// 안드로이드가 대비를 못 맞춰 도로 깐다.
  ///
  /// 🔴 **글자를 어둡게 하면 막을 깔 까닭 자체가 없어진다** — 막는 것이
  /// 아니라 **필요를 없애는** 쪽이다.
  ///
  /// ⚠️ **이 바탕을 쓰는 화면에만 붙는다.** 어두운 화면(인트로 · 로그인 ·
  /// 영상)에 같이 걸면 상태 바 글자가 통째로 안 보인다 — 그래서 앱 전체가
  /// 아니라 이 위젯이 들고 있다.
  ///
  /// 🔴 **밝기를 [base] 에서 스스로 정한다 (2026-09-23).** 전에는 「어두운
  /// 아이콘」으로 **박혀 있었다** — 바탕이 흰색이던 시절의 값이라, 갈래가
  /// 늘어난 지금 그대로 두면 **검은 바탕 위에 검은 시계**가 된다.
  /// 바탕을 또 갈아도 여기는 안 따라와도 된다.
  @override
  Widget build(BuildContext context) {
    final lightBg = base.computeLuminance() > 0.5;
    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        // 안드로이드 — 밝은 바탕이면 어두운 아이콘.
        statusBarIconBrightness: lightBg ? Brightness.dark : Brightness.light,
        // iOS — 같은 뜻인데 **반대로 적는다**(바탕의 밝기를 말한다).
        statusBarBrightness: lightBg ? Brightness.light : Brightness.dark,
      ),
      child: CustomPaint(
        painter: _ScreenTintPainter(a: a, b: b, base: base, glows: glows),
      ),
    );
  }
}

/// 🔴 **사용자가 집어 준 파스텔 딥그린이다 (2026-09-23 여섯 번째 정정:
/// 「좀 더 파스텔 색상」 + 색 견본).** 하루 사이 흰색(`#F6FAF5`) → 순검정 →
/// `#131213` → 밝은 회색(`#EFEFEF`) → 딥그린(`#0F2E1F`) → **이 값**으로 왔다.
///
/// ⚠️ **앞선 값은 [kCardBg](`#91EA92`)를 그대로 어둡게 내린 것이었다** —
/// 색상각(120°)을 지킨 값. 이번 것은 사용자가 고른 것이라 **채도가 더 낮고
/// 색상각도 조금 다르다**(134°). 앱 초록과 계열을 맞추는 규칙을 이 값이
/// 대신하므로, 다음에 또 갈 때 「초록을 어둡게 내려라」로 되돌리지 말 것.
///
/// 🔴 **지름길 알약 셋이 같은 값을 쓴다**(`home_screen.dart` 의 `_kPillFill`).
/// 여기만 갈면 알약도 따라온다 — 그러라고 한 곳에 뒀다.
///
/// ⚠️ **어두운 쪽이라 흰 글자가 산다.** 밝은 쪽으로 갈 일이 있으면 홈의
/// 「내 프로필」 흰 글자와 순백 흰 판의 경계를 같이 봐야 한다.
const Color _kMintBase = Color(0xFF38483D);

/// 옅은 쪽 — [kCardBg] 를 흰색 쪽으로 끌어올린 값이다. 마주 보는 자리에
/// 놓이므로 진한 쪽과 같은 세기면 화면이 양옆에서 조여 보인다.
const Color _kMintGlowSoft = Color(0xFFC6F1C7);

/// `(자국색인가, 중심 x, 중심 y, 반경, 세기)` — x·y 는 화면 대비 비율이고
/// **1 을 넘거나 0 보다 작다**(중심이 화면 밖이라는 뜻이다). 반경은 폭 대비.
///
/// ⚠️ **중심은 화면 밖에 둔다** — 안으로 들이면 넓어지는 게 아니라
/// **덩어리가 커지는** 것이 되어, 이 갈래를 만든 까닭이 무너진다.
/// 두 벌 다 그 규칙을 지킨다.
///
/// 🔴 **넓혔다**(2026-09-22 사용자 요청: 「2개 색상 조금 더 넓게」).
/// 반경 0.95 → **1.30**, 셋째는 0.70 → 0.95.
const List<(bool, double, double, double, double)> _darkGlows = [
  // 왼쪽 아래에서 — 레퍼런스에서 가장 밝은 자리다.
  (true, -0.18, 0.74, 1.30, 0.62),
  // 오른쪽 가운데에서 — 마주 보는 쪽이라 위의 것과 안 겹친다.
  (false, 1.20, 0.34, 1.30, 0.55),
  // 아래에서 아주 옅게 — 바닥이 뚝 검어지는 것을 막는다.
  (false, 0.62, 1.16, 0.95, 0.30),
];

/// 홈의 갈래([ScreenTint.mint]) — 🔴 **지금은 비어 있다. 바탕색 하나뿐이다.**
///
/// 🔴 **사용자가 「그냥 이 색상으로」라고 정했다 (2026-09-23).** 같은 날
/// 오후에 위가 진하고 아래로 희어지는 초록 빛무리 셋을 넣었었다 —
/// `(false, 0.50, -0.34, 1.45, 0.46)` · `(false, -0.14, 0.04, 1.05, 0.26)` ·
/// `(true, 1.14, 0.12, 1.05, 0.22)`. 되살리려면 이 세 줄을 도로 넣으면 된다.
///
/// ⚠️ **이름(`mint`)은 그대로 둔다** — 부르는 쪽(`home_screen.dart`)과 시험이
/// 그 이름을 쓰고, 색은 또 바뀔 수 있다.
const List<(bool, double, double, double, double)> _mintGlows = [];

class _ScreenTintPainter extends CustomPainter {
  const _ScreenTintPainter({
    required this.a,
    required this.b,
    required this.base,
    required this.glows,
  });

  final Color a;
  final Color b;
  final Color base;
  final List<(bool, double, double, double, double)> glows;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRect(Offset.zero & size, Paint()..color = base);

    for (final g in glows) {
      final center = Offset(g.$2 * size.width, g.$3 * size.height);
      final r = size.width * g.$4;
      final color = g.$1 ? b : a;
      canvas.drawCircle(
        center,
        r,
        Paint()
          ..shader = RadialGradient(
            /* 🔴 **종 모양으로 떨어뜨린다.** 곧게 옅어지면 색이 256단이라
               같은 폭마다 한 단씩 끊기고 그 경계가 **동심원 띠**로 드러난다
               (전면 빛무리 `kAuroraGlow` 가 그것 때문에 꺼져 있다).
               [CardSideSmoke] 에서 쓰는 것과 **같은 눈금**이다. */
            colors: [
              for (final k in const [1.0, 0.880, 0.599, 0.306, 0.102, 0.0])
                // 같은 색의 **투명**으로 끝낸다 — 흰·검정으로 끝내면 가장자리에
                // 테가 생겨 원이 드러난다.
                color.withValues(alpha: g.$5 * k),
            ],
            stops: const [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
          ).createShader(Rect.fromCircle(center: center, radius: r)),
      );
    }
  }

  @override
  bool shouldRepaint(_ScreenTintPainter old) =>
      old.a != a || old.b != b || old.base != base || old.glows != glows;
}
