import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../data/models/skeleton.dart';

/// 영상 위에 **관절을 겹쳐 그린다** (2026-09-25 사용자 요청: 「관절 붙여줘」).
///
/// 🔴 **기기에서 관절을 뽑지 않는다.** 웹 화면은 브라우저에서 MoveNet 을
/// 실시간으로 돌리지만, 그쪽은 tfjs·canvas·`<video>` seek 에 매여 있어 앱으로
/// 옮길 수 없다 — 대신 **서버가 이미 낸 값**을 받아 그린다(계약 3-14절).
///
/// 🔴 **모양의 정본은 웹 `www/src/lib/skeleton.ts` 다** (2026-09-25 사용자
/// 지적: 「웹이랑 똑같이 못함?」). 처음엔 제 방식대로 그렸다가 웹과 딴판이
/// 됐다 — 얼굴 점이 뭉쳐 보이고, 척추가 없고, 관절이 **속 찬 점**이었다.
/// 아래 규칙은 그 파일에서 그대로 가져온 것이다:
///
/// - **머리는 원 하나.** 얼굴 점 다섯(코·눈·귀)은 **안 찍는다**
/// - **몸통은 척추 한 줄** — 어깨 가운데 → 골반 가운데. 옆선 둘은 그걸 못
///   그을 때만
/// - **목**은 어깨 가운데에서 **머리 원 가장자리까지** — 원 안까지 그으면
///   머리를 가로지른다
/// - **관절 고리는 몸의 마디 열둘만**(어깨·팔꿈치·손목·골반·무릎·발목)
/// - **차는 다리는 굵게**
///
/// 🔴 **머리 크기는 몸통 길이로 잰다**(어깨 폭이 아니라). 옆으로 선 자세
/// (차는 순간이 대개 그렇다)에서는 두 어깨·두 귀가 겹쳐 폭이 0 에 가까워
/// **머리가 사라진다**(웹이 카드 렌더로 확인한 것).
class SkeletonOverlay extends StatelessWidget {
  const SkeletonOverlay({
    super.key,
    required this.skeleton,
    required this.position,
    this.color = _kAccent,
    this.showBox = true,
  });

  final Skeleton skeleton;

  /// 지금 재생 위치 — 여기서 프레임을 고른다.
  final Duration position;

  final Color color;

  /// 사람을 두르는 네모와 「LIVE TRACKING」 딱지.
  final bool showBox;

  @override
  Widget build(BuildContext context) {
    final frame = skeleton.at(position);
    // 🔴 못 잡은 프레임은 **아무것도 안 그린다** — 앞 프레임을 이어 그리면
    //    사람이 없는 자리에 뼈대가 남아 더 이상하다.
    if (frame == null) return const SizedBox.shrink();
    return CustomPaint(
      painter: _SkeletonPainter(
        frame: frame,
        names: skeleton.keypointNames,
        swingLeg: skeleton.swingLeg,
        color: color,
        showBox: showBox,
      ),
    );
  }
}

/// 웹의 `--ss-accent` 와 같은 자리 — 밝은 초록.
const Color _kAccent = Color(0xFF57E389);

/// 어두운 테 — 밝은 코트 위에서도 선이 살아 있게 (웹은 `drop-shadow` 로 한다).
const Color _kHalo = Color(0xB3000000);

/// 🔴 웹 CSS 와 같은 값 — `.ss-shot-bone` 2.5, `.ss-shot-bone-kick` 4.5.
const double _kBone = 2.5;
const double _kKickBone = 4.5;

/// 관절 **고리** — 흰 획 7 위에 바탕색 3 을 덧그어 가운데를 판다(웹과 같다).
const double _kJointOuter = 7;
const double _kJointCore = 3;

/// 이 값보다 확신이 낮은 관절은 **안 그린다.**
///
/// 🔴 **0 으로 내리지 말 것** — 못 잡은 관절이 화면 구석에 찍히면서 팔다리가
/// 엉뚱한 곳으로 뻗는다.
const double _kMinConfidence = 0.3;

/// 머리 반지름 — 🔴 **몸통 길이의 0.22배**(웹 `HEAD_BY_TORSO`).
const double _kHeadByTorso = 0.22;

/// 몸통을 못 재면 — 어깨 폭의 0.3배(웹 `HEAD_BY_SHOULDERS`).
const double _kHeadByShoulders = 0.3;

/// 🔴 **얼굴은 안 찍는다** — 머리 원이 대신한다(웹 `BODY_JOINTS`).
const List<String> _kBodyJoints = [
  'left_shoulder', 'right_shoulder',
  'left_elbow', 'right_elbow',
  'left_wrist', 'right_wrist',
  'left_hip', 'right_hip',
  'left_knee', 'right_knee',
  'left_ankle', 'right_ankle',
];

const List<(String, String)> _kArms = [
  ('left_shoulder', 'left_elbow'),
  ('left_elbow', 'left_wrist'),
  ('right_shoulder', 'right_elbow'),
  ('right_elbow', 'right_wrist'),
];

const Map<String, List<(String, String)>> _kLegs = {
  'left': [('left_hip', 'left_knee'), ('left_knee', 'left_ankle')],
  'right': [('right_hip', 'right_knee'), ('right_knee', 'right_ankle')],
};

class _SkeletonPainter extends CustomPainter {
  const _SkeletonPainter({
    required this.frame,
    required this.names,
    required this.color,
    required this.showBox,
    this.swingLeg,
  });

  final List<List<double>> frame;
  final List<String> names;
  final Color color;
  final bool showBox;
  final String? swingLeg;

  Offset? _at(String name, Size size) {
    final i = names.indexOf(name);
    if (i < 0 || i >= frame.length) return null;
    final kp = frame[i];
    if (kp.length < 3 || kp[2] < _kMinConfidence) return null;
    /* 🔴 **0~1 을 벗어나도 자르지 않는다**(계약). 화면 밖으로 나간 관절이
       실제로 있고, 자르면 **발이 가장자리에 붙은 것처럼** 그려진다. */
    return Offset(kp[0] * size.width, kp[1] * size.height);
  }

  Offset? _mid(String a, String b, Size size) {
    final p = _at(a, size);
    final q = _at(b, size);
    return (p == null || q == null) ? null : (p + q) / 2;
  }

  @override
  void paint(Canvas canvas, Size size) {
    Paint stroke(double w, Color c) => Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = w
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round
      ..color = c;

    // 한 번에 모아 그린다 — 어두운 테를 통째로 깐 뒤 그 위에 색을 얹는다.
    final bones = Path();
    final kick = Path();

    void edge(Path into, String a, String b) {
      final p = _at(a, size);
      final q = _at(b, size);
      if (p == null || q == null) return;
      into
        ..moveTo(p.dx, p.dy)
        ..lineTo(q.dx, q.dy);
    }

    for (final (a, b) in _kArms) {
      edge(bones, a, b);
    }
    edge(bones, 'left_shoulder', 'right_shoulder');
    edge(bones, 'left_hip', 'right_hip');

    /* 🔴 **몸통은 척추 한 줄이다** — 어깨 가운데 → 골반 가운데. 옆선 둘로
       그리면 몸통이 **빈 네모**로 보인다(웹이 그래서 바꿨다). */
    final neck = _mid('left_shoulder', 'right_shoulder', size);
    final pelvis = _mid('left_hip', 'right_hip', size);
    if (neck != null && pelvis != null) {
      bones
        ..moveTo(neck.dx, neck.dy)
        ..lineTo(pelvis.dx, pelvis.dy);
    } else {
      edge(bones, 'left_shoulder', 'left_hip');
      edge(bones, 'right_shoulder', 'right_hip');
    }

    // 🔴 **차는 다리만 굵게** — 어느 쪽인지는 서버가 준다(`swing_leg`).
    for (final leg in ['left', 'right']) {
      for (final (a, b) in _kLegs[leg]!) {
        edge(leg == swingLeg ? kick : bones, a, b);
      }
    }

    /* 머리 — 🔴 **두 귀 가운데.** 옆모습이라 귀가 하나면 **코와 그 귀의
       가운데**(코는 얼굴 앞, 귀는 머리 뒤라 둘의 가운데가 머리 중심에 가깝다).
       그것도 없으면 보이는 점 하나. */
    final nose = _at('nose', size);
    final ear = _at('left_ear', size) ?? _at('right_ear', size);
    final center = _mid('left_ear', 'right_ear', size) ??
        ((ear != null && nose != null) ? (ear + nose) / 2 : (nose ?? ear));
    final ls = _at('left_shoulder', size);
    final rs = _at('right_shoulder', size);
    final r = (neck != null && pelvis != null)
        ? (neck - pelvis).distance * _kHeadByTorso
        : (ls != null && rs != null)
        ? (ls - rs).distance * _kHeadByShoulders
        : 0.0;
    if (center != null && r >= 1) {
      bones.addOval(Rect.fromCircle(center: center, radius: r));
      /* 목 — 🔴 **머리 원 가장자리까지만.** 원 안까지 그으면 머리를 가로지른다. */
      if (neck != null) {
        final d = (neck - center).distance;
        if (d > r) {
          final k = (d - r) / d;
          bones
            ..moveTo(neck.dx, neck.dy)
            ..lineTo(
              neck.dx + (center.dx - neck.dx) * k,
              neck.dy + (center.dy - neck.dy) * k,
            );
        }
      }
    }

    if (showBox) _paintBox(canvas, size, stroke);

    // 어두운 테 → 색 (웹의 `drop-shadow` 자리).
    canvas.drawPath(bones, stroke(_kBone + 2, _kHalo));
    canvas.drawPath(kick, stroke(_kKickBone + 2, _kHalo));
    canvas.drawPath(bones, stroke(_kBone, color));
    canvas.drawPath(kick, stroke(_kKickBone, color));

    /* 관절 — 🔴 **고리다.** 흰 획 위에 같은 자리를 어두운 획으로 한 번 더
       찍어 가운데를 판다(웹 `.ss-shot-joint` + `.ss-shot-joint-core`).
       ⛔ 속을 채우지 말 것 — 점이 뭉쳐 보인다. */
    final ring = Path();
    for (final name in _kBodyJoints) {
      final p = _at(name, size);
      if (p == null) continue;
      ring
        ..moveTo(p.dx, p.dy)
        ..lineTo(p.dx, p.dy);
    }
    canvas
      ..drawPath(ring, stroke(_kJointOuter + 1.5, _kHalo))
      ..drawPath(ring, stroke(_kJointOuter, Colors.white))
      ..drawPath(ring, stroke(_kJointCore, const Color(0xCC000000)));
  }

  /// 사람을 두르는 네모와 딱지 — 웹 `.ss-shot-track-box` 자리.
  ///
  /// 🔴 **서버가 네모를 주지 않는다** — 보이는 관절의 최소·최대에서 만든다.
  /// 그래서 관절이 몇 개 안 잡히면 네모도 작아진다(그게 정직한 그림이다).
  void _paintBox(Canvas canvas, Size size, Paint Function(double, Color) stroke) {
    double? l, t, r2, b;
    for (final name in names) {
      final p = _at(name, size);
      if (p == null) continue;
      l = l == null ? p.dx : math.min(l, p.dx);
      r2 = r2 == null ? p.dx : math.max(r2, p.dx);
      t = t == null ? p.dy : math.min(t, p.dy);
      b = b == null ? p.dy : math.max(b, p.dy);
    }
    if (l == null || t == null || r2 == null || b == null) return;
    // 사람을 넉넉히 감싼다 — 딱 붙이면 머리 원과 발끝이 선에 물린다.
    final padX = size.width * 0.03 + 8;
    final padY = size.height * 0.04 + 8;
    final box = Rect.fromLTRB(l - padX, t - padY, r2 + padX, b + padY);
    canvas
      ..drawRect(box, stroke(2.6, _kHalo))
      ..drawRect(box, stroke(1.6, color));

    // 「LIVE TRACKING」 딱지 — 네모 왼쪽 위에 걸친다.
    const label = 'LIVE TRACKING';
    final tp = TextPainter(
      text: const TextSpan(
        text: label,
        style: TextStyle(
          color: Color(0xFF07230F),
          fontSize: 9,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.6,
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    const dot = 4.0;
    final pillW = tp.width + 22 + dot;
    final pill = Rect.fromLTWH(box.left, box.top - 17, pillW, 15);
    // 위가 잘리면 네모 **안쪽**으로 내린다.
    final shifted = pill.top < 0 ? pill.shift(const Offset(0, 19)) : pill;
    canvas.drawRRect(
      RRect.fromRectAndRadius(shifted, const Radius.circular(7.5)),
      Paint()..color = color,
    );
    canvas.drawCircle(
      Offset(shifted.left + 8, shifted.center.dy),
      dot,
      Paint()..color = const Color(0xFFE5484D),
    );
    tp.paint(canvas, Offset(shifted.left + 14, shifted.center.dy - tp.height / 2));
  }

  @override
  bool shouldRepaint(_SkeletonPainter old) =>
      old.frame != frame ||
      old.color != color ||
      old.names != names ||
      old.swingLeg != swingLeg ||
      old.showBox != showBox;
}
