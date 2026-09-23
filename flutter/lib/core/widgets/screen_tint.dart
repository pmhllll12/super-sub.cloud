import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

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
  const ScreenTint({super.key, required this.a, required this.b});

  /// 카드 바탕색 · 자국색.
  final Color a;
  final Color b;

  @override
  /// 🔴 **상태 바 글자를 어둡게 시킨다**(2026-09-22, 사용자 지적: 「스크롤
  /// 하면 상단바의 검은색 바가 튀어나와」).
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
  Widget build(BuildContext context) => AnnotatedRegion<SystemUiOverlayStyle>(
    value: const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      // 안드로이드 — 어두운 아이콘.
      statusBarIconBrightness: Brightness.dark,
      // iOS — 같은 뜻.
      statusBarBrightness: Brightness.light,
    ),
    child: CustomPaint(
      painter: _ScreenTintPainter(a: a, b: b),
    ),
  );
}

class _ScreenTintPainter extends CustomPainter {
  const _ScreenTintPainter({required this.a, required this.b});

  final Color a;
  final Color b;

  /// `(자국색인가, 중심 x, 중심 y, 반경, 세기)` — x·y 는 화면 대비 비율이고
  /// **1 을 넘거나 0 보다 작다**(중심이 화면 밖이라는 뜻이다). 반경은 폭 대비.
  /// 🔴 **넓혔다**(2026-09-22 사용자 요청: 「2개 색상 조금 더 넓게」).
  /// 반경 0.95 → **1.30**, 셋째는 0.70 → 0.95.
  /// ⚠️ **중심은 그대로 화면 밖에 둔다** — 안으로 들이면 넓어지는 게 아니라
  /// **덩어리가 커지는** 것이 되어, 이 갈래를 만든 까닭이 무너진다.
  static const _glows = [
    // 왼쪽 아래에서 — 레퍼런스에서 가장 밝은 자리다.
    (true, -0.18, 0.74, 1.30, 0.62),
    // 오른쪽 가운데에서 — 마주 보는 쪽이라 위의 것과 안 겹친다.
    (false, 1.20, 0.34, 1.30, 0.55),
    // 아래에서 아주 옅게 — 바닥이 뚝 검어지는 것을 막는다.
    (false, 0.62, 1.16, 0.95, 0.30),
  ];

  @override
  void paint(Canvas canvas, Size size) {
    // 바탕은 검정이다 — 색은 얹히기만 한다.
    canvas.drawRect(
      Offset.zero & size,
      Paint()..color = const Color(0xFF000000),
    );

    for (final g in _glows) {
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
  bool shouldRepaint(_ScreenTintPainter old) => old.a != a || old.b != b;
}
