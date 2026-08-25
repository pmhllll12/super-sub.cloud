import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show rootBundle;

/// 순백 구간이 끝나는 컨트롤러 값. 700ms / 3600ms.
///
/// **`glitch_intro_screen.dart`의 `kIntroDuration`(지금 3600ms)과 이 3.6이
/// 서로를 모른다.** 전체 길이를 바꾸면 이 나눗셈의 분모도 같이 바꿔야
/// 한다 — 안 그러면 순백·번짐 구간의 비율이 조용히 어긋난다. 테스트에도
/// 3600이 그대로 박혀 있다(`test/core/ink_bleed_test.dart`).
const double _kDryEnd = 0.70 / 3.6;

/// 번짐이 끝나는 컨트롤러 값. 3100ms / 3600ms. 위 [_kDryEnd]와 같은 주의.
const double _kWetEnd = 3.10 / 3.6;

/// 컨트롤러 값 [t](0~1)를 잉크 진행도(0~1)로 옮긴다.
///
/// 선형이 아니다. 참조 영상에서 잰 밝기 곡선이 번짐 구간 **절반 지점에
/// 65%**가 젖어 있었다(선형이면 50%). `easeOutQuad`(75%)와 선형을 0.6:0.4로
/// 섞으면 그 값이 나온다. `easeOutQuad - 선형 = u - u²`이므로
/// `p = u + 0.6(u - u²) = 1.6u - 0.6u²`이다.
///
/// **`easeOutCubic`을 쓰면 안 된다** — 같은 지점이 88%가 되어 `p=0.6`이
/// 0.8초에 와 버린다. 글자가 읽히기도 전에 글리치가 터진다.
double inkProgress(double t) {
  if (t <= _kDryEnd) return 0;
  if (t >= _kWetEnd) return 1;
  final u = (t - _kDryEnd) / (_kWetEnd - _kDryEnd);
  return 1.6 * u - 0.6 * u * u;
}

/// 잉크 셰이더와 그 지도를 한 번만 로드해 들고 있다.
///
/// **`ImageFilter.isShaderFilterSupported`로 막지 않는다.** 옆의
/// `ChipGlassShader`·`GlassShader`는 `ImageFilter.shader`(Impeller 전용)를
/// 쓰기 때문에 그 빗장이 필요하지만, 여기는 `Paint.shader`라 Skia에서도
/// 돈다. 그대로 베껴 오면 Skia 기기에서 잉크가 통째로 사라진다.
class InkBleedShader {
  InkBleedShader._();

  static ui.FragmentProgram? _program;
  static ui.Image? _field;

  static bool get isReady => _program != null && _field != null;

  /// 앱 시작 때 한 번 부른다. 실패해도 예외를 밖으로 내보내지 않는다 —
  /// 못 쓰면 [InkBleedPainter]가 밋밋한 페이드로 물러선다.
  static Future<void> load() async {
    if (isReady) return;
    try {
      _program ??= await ui.FragmentProgram.fromAsset('shaders/ink_bleed.frag');
      final data = await rootBundle.load('assets/images/ink_field.png');
      final codec = await ui.instantiateImageCodec(data.buffer.asUint8List());
      _field = (await codec.getNextFrame()).image;
    } catch (_) {
      _program = null;
      _field = null;
    }
  }

  /// **메인에 다 들어온 뒤** 지도를 놓아준다. 1080×2340 RGBA = 9.64MB가
  /// 일회성 연출을 위해 앱 종료까지 상주할 이유가 없다.
  ///
  /// **인트로가 끝날 때 놓아주면 안 된다.** 로그인 → 메인 전환도 같은
  /// 잉크를 쓰는데, 그때 지도가 없으면 [InkBleedPainter]가 조용히 물러섬
  /// 경로(밋밋한 색 페이드)로 떨어진다 — 아무도 안 터지고 그냥 다른
  /// 연출이 나온다. 실제로 그렇게 한 번 새어 나갔다.
  ///
  /// `_field`가 null이 되면 [isReady]가 false다. 필요해지면 [load]를 다시
  /// 부르면 된다(가드가 이미 재로드를 허용한다) — 로그아웃하고 인트로로
  /// 돌아가는 길이 그렇다.
  static void release() {
    _field?.dispose();
    _field = null;
  }
}

/// 끓음 최대 폭. 문턱값을 이만큼 흔든다.
const double _kBoil = 0.06;

/// 문턱 경계 폭. 참조의 알갱이는 점으로 딱딱 떨어진다 — 최소한만 준다.
const double _kEdge = 0.02;

/// 잉크를 그린다. 흰 바탕 위에 검정을 알파로 얹는다.
class InkBleedPainter extends CustomPainter {
  /// 잉크 진행도 0~1.
  final double progress;

  /// 프레임마다 바뀌는 씨앗. 이게 안 바뀌면 잉크가 안 끓는다.
  final int seed;

  /// 참이면 잉크가 **물러난다** — 가운데부터 점으로 구멍이 뚫려 넓어지고,
  /// 그 틈으로 뒤가 드러난다. 인트로에서 다음 화면으로 넘어갈 때 쓴다.
  final bool erase;

  /// 잉크 색. 부르는 쪽이 정한다 — 검정이 아니어도 된다.
  final Color ink;

  const InkBleedPainter({
    required this.progress,
    required this.seed,
    required this.ink,
    this.erase = false,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;

    if (!InkBleedShader.isReady) {
      // 물러섬 — 잉크 없이 진행도만큼 검게 덮는다. 밋밋하지만 안 깨진다.
      final cover = progress.clamp(0.0, 1.0);
      canvas.drawRect(
        rect,
        Paint()..color = ink.withValues(alpha: erase ? 1 - cover : cover),
      );
      return;
    }

    // **논리 픽셀을 넘긴다. dpr을 곱하지 않는다.**
    //
    // `FlutterFragCoord()`의 좌표계는 셰이더를 다는 경로에 따라 다르다.
    // `glass_chips`·`liquid_glass`는 `ImageFilter.shader` 경로라 레이어의
    // **물리** 픽셀을 받고 주석도 그렇게 적혀 있다. 그걸 베끼면 안 된다.
    //
    // 같은 `Paint.shader` 경로의 선례가 이미 이 저장소에 있다 —
    // `ai_mode_button.frag`이고, 그 주석이 "이 셰이더를 Paint로 문지르는
    // 캔버스의 지역 좌표(논리 px)"라고 못박아 뒀다. 호출부
    // `chip_face.dart:160`도 `size.width`를 그대로 넘긴다.
    final shader = InkBleedShader._program!.fragmentShader()
      ..setFloat(0, size.width)
      ..setFloat(1, size.height)
      ..setFloat(2, progress)
      ..setFloat(3, seed.toDouble())
      ..setFloat(4, _kBoil)
      ..setFloat(5, _kEdge)
      ..setFloat(6, erase ? 1 : 0)
      ..setFloat(7, ink.r)
      ..setFloat(8, ink.g)
      ..setFloat(9, ink.b)
      ..setImageSampler(0, InkBleedShader._field!);

    canvas.drawRect(rect, Paint()..shader = shader);
  }

  @override
  bool shouldRepaint(InkBleedPainter old) =>
      old.progress != progress ||
      old.seed != seed ||
      old.erase != erase ||
      old.ink != ink;
}

/// 다음 화면 위에 잉크를 **덮었다가 걷어 내는** 전환.
///
/// 밝은 화면과 어두운 화면을 그냥 겹쳐 페이드하면 둘이 섞여 뿌예진다.
/// 대신 다음 화면을 처음부터 온전히 깔고, 그 위의 잉크를 거둔다 — 지도가
/// "가운데부터 젖는 순서"라 글자 있던 자리부터 구멍이 뚫려 넓어진다.
///
/// [coverUntil]은 **덮는 데 쓰는 앞 구간**이다. 인트로처럼 이미 잉크로
/// 덮여 있는 화면에서 나올 때는 0을 준다(바로 걷기 시작). 로그인처럼
/// 안 덮인 화면에서 나올 때는 앞을 조금 떼어 그 사이에 잉크가 배어들게
/// 한다 — 0으로 두면 첫 프레임에 화면이 통째로 잉크색으로 뚝 바뀐다.
class InkPeel extends StatelessWidget {
  final Animation<double> animation;
  final Color ink;

  /// 잉크가 배어드는 앞 구간(0~1).
  final double coverUntil;

  /// 걷히는 진행에 씌우는 곡선.
  final Curve peel;

  final Widget child;

  const InkPeel({
    super.key,
    required this.animation,
    required this.ink,
    required this.child,
    this.coverUntil = 0,
    this.peel = Curves.easeOutQuad,
  });

  /// 이 전환의 두 몫 — 덮인 정도와 걷힌 정도.
  ///
  /// 그리기와 떼어 두어 테스트가 숫자만 볼 수 있게 했다.
  static ({double cover, double peeled}) split(double t, double coverUntil) {
    if (coverUntil <= 0) return (cover: 1, peeled: t.clamp(0.0, 1.0));
    return (
      cover: (t / coverUntil).clamp(0.0, 1.0),
      peeled: ((t - coverUntil) / (1 - coverUntil)).clamp(0.0, 1.0),
    );
  }

  @override
  Widget build(BuildContext context) => Stack(
        fit: StackFit.expand,
        children: [
          // **다 덮이기 전에는 다음 화면을 감춘다.**
          //
          // 잉크가 배어드는 동안 이걸 켜 두면, 잉크가 아직 투명한 첫
          // 순간에 다음 화면이 그대로 비친다 — "메인이 먼저 잠깐 나왔다가
          // 점이 나와서 사라진다"가 그 증상이었다. 이 자리에는 아직
          // 떠나는 화면이 보여야 한다(아래 라우트가 그대로 그려진다).
          //
          // 켜는 순간 잉크는 완전히 불투명하므로 바뀌는 게 안 보인다.
          // 감추는 동안에도 배치는 살아 있어(투명도 0) 다음 화면은
          // 그사이에 다 지어진다.
          Opacity(
            opacity: InkPeel.split(animation.value, coverUntil).cover >= 1
                ? 1
                : 0,
            child: child,
          ),
          IgnorePointer(
            child: AnimatedBuilder(
              animation: animation,
              builder: (_, _) {
                final s = split(animation.value, coverUntil);
                return Opacity(
                  opacity: s.cover,
                  child: CustomPaint(
                    painter: InkBleedPainter(
                      ink: ink,
                      progress: peel.transform(s.peeled),
                      // 걷히는 동안에도 알갱이가 끓어야 들어올 때와 같은
                      // 재질로 읽힌다. 매 프레임 새 씨앗이 필요하다.
                      seed: (animation.value * 3000).round(),
                      erase: true,
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      );
}
