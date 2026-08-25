import 'dart:math';

import 'package:flutter/material.dart';

import '../../../../core/widgets/ink_bleed.dart';

/// 앱을 켜면 한 번 지나가는 인트로.
///
/// **바탕은 흰 종이다.** 여기에 검은 잉크가 번지고, 그 위에 얹힌 흰 글자가
/// 저절로 드러난다 — 글자는 나타나는 게 아니라 처음부터 그 자리에 있었다.
///
/// 원본(`com.sumworship`)은 아이보리 종이에 와인색 잉크였다. 구조는 그대로
/// 두고 두 색만 바꿨다 — 종이는 순백으로, 잉크는 검정으로.
///
/// 연출은 `com.sumworship/mobile`에서 가져왔다. 그쪽의 `FORMA`·`AuthService`·
/// 홈 색상 의존만 이 프로젝트 것으로 갈아 끼웠고, 잉크의 수치는 건드리지
/// 않았다 — 저쪽 주석이 참조 영상에서 잰 값이라고 못박아 둔 것들이다.

/// 바탕색.
///
/// **글자색과 같은 값이어야 한다.** 잉크가 번져야 글자가 드러나는 연출이라,
/// 둘이 갈리면 글자가 처음부터 보인다.
const Color kIntroPaper = Color(0xFFFFFFFF);

/// 글자색. [kIntroPaper]와 같다 — 위 주의 참고.
const Color kIntroInk = kIntroPaper;

/// 화면을 적시는 잉크의 색.
///
/// 앱 강조색(`AppTheme.seed`, 민트)과는 **다른 색이다.** 잉크는 화면을 통째로
/// 덮는 바탕이라 강조색을 쓰면 강조가 안 된다 — 민트는 버튼처럼 눈이 가야 할
/// 곳에만 남긴다.
const Color kIntroInkColor = Color(0xFF000000);

/// 글자 크기.
///
/// 원본은 다섯 글자(`FORMA`)에 72였다. 여기는 여덟 글자라 같은 크기면 폭이
/// 넘친다. 44로 줄이고, 아래 자간도 같은 비율(44/72)로 줄였다.
const double _kIntroSize = 44;

/// 전체 길이. 순백 200 + 번짐 2400 + 머묾 500.
///
/// **`ink_bleed.dart`의 `_kDryEnd`·`_kWetEnd`가 이 3100을 하드코딩한 3.1로
/// 나눗셈에 쓴다.** 여기를 바꾸면 그쪽도 같이 바꿔야 순백·번짐 구간의 비율이
/// 안 어긋난다. 테스트에도 3100이 그대로 박혀 있다(`test/core/ink_bleed_test.dart`).
const Duration kIntroDuration = Duration(milliseconds: 3100);

/// 인트로에서 앱 화면으로 넘어가는 데 걸리는 시간.
const Duration kIntroExitDuration = Duration(milliseconds: 2000);

/// 잉크가 벗겨지는 진행에 씌우는 곡선.
///
/// **끝을 길게 끈다.** 덮인 넓이가 진행도와 그대로 비례하므로 선형으로 두면
/// 마지막에 남은 성긴 점들이 한순간에 다 사라져 "퐉" 하고 꺼지는 것처럼
/// 보인다. 감속을 주면 넓이가 일찍 줄고 성긴 꼬리에 시간이 많이 배당돼
/// 서서히 걷히는 것으로 읽힌다.
const Curve kIntroExitPeel = Curves.easeOutQuad;

/// 흔들림 값을 붙잡아 두는 시간.
///
/// **매 프레임 새로 뽑으면 글리치가 아니라 지글거림이 된다.** 이 길이만큼
/// 같은 값을 유지해야 툭툭 끊기는 화면 오류로 읽힌다. 60Hz에서 45ms면 세
/// 프레임쯤 한 자리에 머문다.
const int _kHoldMs = 45;

/// 글자를 가로로 몇 개의 띠로 끊을지. 띠마다 어긋나는 양이 달라야 글자가
/// 통째로 밀리는 대신 화면이 찢어진 것처럼 보인다.
const int _kBands = 7;

/// 지지직대는 구간 — (시작, 끝, 세기). **컨트롤러 값이 아니라 잉크 진행도
/// 기준이다.**
///
/// 시각으로 박으면 진행 곡선을 손볼 때마다 어긋난다. 그리고 글리치가
/// 성립하는 조건은 흐른 시간이 아니라 **글자와 잉크의 대비**다 — 잉크가
/// 덜 번진 구간에서 흔들면 글리치로 안 읽히고 잉크가 지저분한 것으로 보인다.
///
/// 창은 `0.60 ~ 0.95`다. 앞은 글자가 읽히기 시작하는 지점이고, 뒤는 머묾
/// 구간을 침범하지 않는 지점이다. 나머지 시간은 **가만히 있는다** — 사이의
/// 정적이 있어야 터지는 순간이 산다.
const List<(double, double, double)> _kBursts = [
  (0.62, 0.71, 1.0),
  (0.76, 0.83, 0.72),
  (0.88, 0.93, 0.4),
];

/// 가지런한 글자가 깨진 글자로 넘어가는 **잉크 진행도.**
///
/// 두 번째 버스트 한가운데(0.76~0.83)다. 정적 구간에서 바꾸면 글꼴이 갈리는
/// 게 그대로 보이고, 흔들리는 동안 바꾸면 그 소란에 묻힌다.
const double _kSwapAt = 0.795;

/// 잉크 진행도 [p]에서 얼마나 세게 흔들릴지(0~1).
@visibleForTesting
double glitchAmplitudeAt(double p) {
  for (final (start, end, power) in _kBursts) {
    if (p < start || p >= end) continue;
    // 버스트 안에서도 뒤로 갈수록 잦아든다. 끝까지 같은 세기로 흔들면
    // 멈추는 순간이 뚝 끊긴 것처럼 보인다.
    final into = (p - start) / (end - start);
    return power * (1 - into * into);
  }
  return 0;
}

/// 가지런한 글자가 지지직대다 깨진 글자로 굳는다.
///
/// Rubik Glitch는 **깨진 모양이 글꼴에 이미 박혀 있어** 그것만으로는 "멀쩡했다가
/// 깨지는" 변화를 못 만든다. 그래서 같은 집안의 가지런한 Rubik으로 시작해
/// 흔드는 도중에 갈아 끼운다.
class GlitchIntroScreen extends StatefulWidget {
  const GlitchIntroScreen({super.key, required this.onDone});

  /// 인트로가 다 흐른 뒤 불린다. 다음 화면으로 넘기는 일은 부르는 쪽이 한다
  /// — 이 화면은 라우터를 모른다.
  final VoidCallback onDone;

  @override
  State<GlitchIntroScreen> createState() => _GlitchIntroScreenState();
}

class _GlitchIntroScreenState extends State<GlitchIntroScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _t = AnimationController(
    vsync: this,
    duration: kIntroDuration,
  );

  @override
  void initState() {
    super.initState();
    _t.forward().whenComplete(() {
      if (mounted) widget.onDone();
    });
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // 이미 실려 있으면 바로 돌아오는 호출이라 그냥 부른다.
    InkBleedShader.load();
  }

  @override
  void dispose() {
    _t.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kIntroPaper,
      body: AnimatedBuilder(
        animation: _t,
        builder: (context, _) {
          final t = _t.value;
          final p = inkProgress(t);
          final amp = glitchAmplitudeAt(p);
          final glitched = p >= _kSwapAt;
          // 시간을 토막 내 그 토막을 씨앗으로 쓴다. 같은 토막 안에서는 같은
          // 값이 나오므로 흔들림이 그 시간만큼 제자리에 붙잡힌다.
          final step = (t * kIntroDuration.inMilliseconds) ~/ _kHoldMs;
          return Stack(
            fit: StackFit.expand,
            children: [
              // 잉크는 매 프레임 새 씨앗을 받아야 끓는다. 글리치의 붙잡는
              // 씨앗(step)과 달리 여기는 프레임마다 바뀌어야 한다.
              CustomPaint(
                painter: InkBleedPainter(
                  ink: kIntroInkColor,
                  progress: p,
                  seed: (t * kIntroDuration.inMilliseconds).round(),
                ),
              ),
              Center(
                child: _GlitchText(
                  glitched: glitched,
                  amplitude: amp,
                  seed: step,
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _GlitchText extends StatelessWidget {
  final bool glitched;
  final double amplitude;
  final int seed;

  const _GlitchText({
    required this.glitched,
    required this.amplitude,
    required this.seed,
  });

  TextStyle get _style => TextStyle(
        fontFamily: glitched ? 'RubikGlitch' : 'Rubik',
        // **900이라야 두 글꼴의 살집이 같다.** 700은 확연히 가늘어 갈아
        // 끼우는 순간이 티가 난다.
        //
        // 가변 폰트라 굵기는 FontVariation으로 준다 — fontWeight만 주면 가변
        // 축이 안 움직인다. Glitch 쪽은 축이 없어 무시된다.
        fontVariations: const [FontVariation('wght', 900)],
        fontSize: _kIntroSize,
        color: kIntroInk,
        height: 1,
        // 가지런한 Rubik이 Glitch보다 좁아, 그 차이를 자간으로 메운다.
        // 원본의 값(2 / 3.4)은 크기 72 기준이므로 크기 비율(44/72)로 줄였다.
        letterSpacing: glitched ? 1.2 : 2.1,
      );

  @override
  Widget build(BuildContext context) {
    const text = 'SUPERSUB';
    final rnd = Random(seed);
    // 띠마다 다른 만큼 어긋난다. 세로로는 밀지 않는다 — 가로로만 찢어져야
    // 신호가 어긋난 화면처럼 보인다.
    final shifts = [
      for (var i = 0; i < _kBands; i++)
        (rnd.nextDouble() * 2 - 1) * amplitude * 14,
    ];
    // 잉크 위에서 RGB 어긋남은 재질이 갈린다 — 잉크는 물성인데 색 분리는
    // 디지털 신호라 한 화면에서 두 매체가 싸운다. 띠 찢김만으로 "아직 안
    // 굳었다"는 말은 그대로 된다.
    final body = Text(text, style: _style);

    if (amplitude <= 0) return body;

    // 같은 글자를 띠 수만큼 겹쳐 놓고, 각 겹은 자기 띠만 남기고 잘라 낸다.
    return Stack(
      alignment: Alignment.center,
      children: [
        for (var i = 0; i < _kBands; i++)
          ClipRect(
            clipper: _BandClipper(i / _kBands, (i + 1) / _kBands),
            child: Transform.translate(
              offset: Offset(shifts[i], 0),
              child: body,
            ),
          ),
      ],
    );
  }
}

/// 자식의 세로 [from]~[to] 구간만 남긴다(둘 다 0~1 비율).
class _BandClipper extends CustomClipper<Rect> {
  final double from;
  final double to;

  const _BandClipper(this.from, this.to);

  @override
  Rect getClip(Size size) =>
      Rect.fromLTRB(0, size.height * from, size.width, size.height * to);

  @override
  bool shouldReclip(_BandClipper old) => old.from != from || old.to != to;
}
