import 'dart:math' as math;

import 'package:flutter/widgets.dart';

/// 선수 카드 뒤에 깔리는 검은 붓자국 — 웹 `www/src/components/PlayerCardBrush.tsx`
/// 를 **수식째** 옮긴 것이다.
///
/// 🔴 **웹과 한 줄도 달라지면 안 된다.** 같은 카드가 웹과 앱에서 다른 무늬면
/// 같은 카드로 안 보인다(`www/docs/2026-08-31-앱-이식-지침.md` §2-4). 그래서
/// 씨앗(카드 슬러그) → 해시 → 난수기 → 획 순서를 웹 그대로 두고, 난수를 꺼내는
/// **순서**까지 맞췄다. `player_card_brush_test.dart` 가 웹에서 뽑은 값과 대조한다.
///
/// `Math.random()` 에 해당하는 것을 쓰지 않는 이유도 웹과 같다 — 사람마다
/// 다르되 같은 사람에게는 늘 같은 모양이어야 한다.

int _i32(int x) => x.toSigned(32);
int _u32(int x) => x & 0xFFFFFFFF;

/// JS `Math.imul` — 32비트 곱의 아래 32비트를 부호 있는 수로.
int _imul(int a, int b) => _i32((a * b) & 0xFFFFFFFF);

/// 문자열 → 32비트 정수(FNV-1a). JS `charCodeAt` 과 같게 **UTF-16 단위**로 돈다.
int brushHash(String text) {
  var h = 2166136261;
  for (final unit in text.codeUnits) {
    h = _i32(h ^ unit);
    h = _imul(h, 16777619);
  }
  return _u32(h);
}

/// mulberry32 — 씨앗 하나로 늘 같은 수열을 뱉는 작은 난수기. 0 이상 1 미만.
double Function() brushRng(int seed) {
  var a = seed;
  return () {
    a = _i32(a);
    a = _i32(a + 0x6d2b79f5);
    var t = _imul(a ^ (_u32(a) >> 15), 1 | a);
    t = _i32(t + _imul(t ^ (_u32(t) >> 7), 61 | t)) ^ t;
    return _u32(t ^ (_u32(t) >> 14)) / 4294967296;
  };
}

/// 붓자국 하나의 윤곽 — 길이 [len], 가운데 두께 [thick] 인 가로 막대. 양 끝이
/// 가늘어진다. 웹 `strokePath` 와 같다(웹은 SVG 경로 문자열, 여기는 [Path]).
Path _strokePath(double len, double thick, double Function() next) {
  const steps = 14;
  final top = <Offset>[];
  final bottom = <Offset>[];
  for (var i = 0; i <= steps; i += 1) {
    final t = i / steps;
    final x = t * len;
    final taper =
        math.pow(math.sin(math.pi * t), 0.55).toDouble() * (0.72 + 0.28 * t);
    final half = (thick / 2) * taper;
    final wobble = (next() - 0.5) * thick * 0.16;
    top.add(Offset(x, -half + wobble));
    bottom.add(Offset(x, half + wobble * 0.6));
  }
  final path = Path()..moveTo(top.first.dx, top.first.dy);
  for (final p in top.skip(1)) {
    path.lineTo(p.dx, p.dy);
  }
  for (final p in bottom.reversed) {
    path.lineTo(p.dx, p.dy);
  }
  return path..close();
}

class _Stroke {
  _Stroke(this.x, this.y, this.angle, this.body, this.bristles);

  final double x;
  final double y;

  /// 도(degree). 음수라 왼쪽 아래 → 오른쪽 위로 지나간다.
  final double angle;
  final Path body;
  final List<(double dy, Path path)> bristles;
}

/// 웹과 같은 순서로 난수를 꺼내 획 셋을 만든다. 값은 viewBox(100×140) 기준이다.
List<_Stroke> _strokesFor(String seed) {
  final next = brushRng(brushHash(seed));
  const count = 3;
  return List.generate(count, (i) {
    // 🔴 위쪽 끝이 카드 절반(y=70)을 넘지 않게 잡은 범위다 — 이유는 웹 주석.
    final angle = -(28 + next() * 10);
    final len = 55 + next() * 25;
    final thick = 3.5 + next() * 3.5;
    final x = -8 + next() * 24 + i * 10;
    final y = 122 + next() * 12;
    final body = _strokePath(len, thick, next);
    final bristleCount = 2 + (next() * 2).floor();
    final bristles = List.generate(bristleCount, (_) {
      final dy = (next() - 0.5) * thick * 1.7;
      final path = _strokePath(len * (0.7 + next() * 0.45), 0.9 + next() * 1.1, next);
      return (dy, path);
    });
    return _Stroke(x, y, angle, body, bristles);
  });
}

/// 카드 전체를 덮는 붓자국. 웹의 `preserveAspectRatio="xMidYMid slice"` 처럼
/// 100×140 판을 **넘치게 채우고 가운데를 맞춘다.**
class PlayerCardBrushPainter extends CustomPainter {
  PlayerCardBrushPainter({required this.seed, required this.color})
      : _strokes = _strokesFor(seed);

  final String seed;
  final Color color;
  final List<_Stroke> _strokes;

  @override
  void paint(Canvas canvas, Size size) {
    final s = math.max(size.width / 100, size.height / 140);
    canvas
      ..save()
      ..translate((size.width - 100 * s) / 2, (size.height - 140 * s) / 2)
      ..scale(s);
    final body = Paint()..color = color;
    final bristle = Paint()..color = color.withValues(alpha: color.a * 0.75);
    for (final stroke in _strokes) {
      canvas
        ..save()
        ..translate(stroke.x, stroke.y)
        ..rotate(stroke.angle * math.pi / 180)
        ..drawPath(stroke.body, body);
      for (final (dy, path) in stroke.bristles) {
        canvas.drawPath(path.shift(Offset(0, dy)), bristle);
      }
      canvas.restore();
    }
    canvas.restore();
  }

  @override
  bool shouldRepaint(PlayerCardBrushPainter old) =>
      old.seed != seed || old.color != color;
}
