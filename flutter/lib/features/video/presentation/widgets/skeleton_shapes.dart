/// 뼈대의 **모양 규칙 한 벌** — 영상 위 오버레이와 비교 카드가 **같은 것을 쓴다.**
///
/// 🔴 **정본은 웹 `www/src/lib/skeleton.ts` 다** (2026-09-25 사용자 지적:
/// 「웹이랑 똑같이 못함?」). 여기 있는 규칙은 전부 거기서 온 것이고, 고치려면
/// 웹도 같이 고친다 — 한쪽만 바꾸면 같은 자세가 두 화면에서 다르게 보인다.
///
/// 🔴 **왜 한 곳인가**: 처음엔 오버레이 안에만 있었는데, 비교 카드가 같은 모양을
/// 그려야 해서 그대로 두면 규칙이 **두 벌**이 된다. 웹이 정확히 그래서 데였다 —
/// 머리를 원으로 바꿨을 때 한쪽만 바뀌어 딴판이 됐다.
library;

import 'dart:ui';

/// 어두운 테 — 밝은 코트 위에서도 선이 살아 있게 (웹은 `drop-shadow` 로 한다).
const Color kSkeletonHalo = Color(0xB3000000);

/// 🔴 웹 CSS 와 같은 값 — `.ss-shot-bone` 2.5, `.ss-shot-bone-kick` 4.5.
const double kBoneWidth = 2.5;
const double kKickBoneWidth = 4.5;

/// 관절 **고리** — 흰 획 7 위에 바탕색 3 을 덧그어 가운데를 판다(웹과 같다).
const double kJointOuter = 7;
const double kJointCore = 3;

/// 한 자세에서 뽑아낸, **그리기만 하면 되는** 경로들.
class SkeletonShapes {
  const SkeletonShapes({
    required this.bones,
    required this.kick,
    required this.joints,
  });

  /// 보통 굵기로 그릴 선 전부 — 팔·어깨·골반·척추·목·머리 원.
  final Path bones;

  /// 🔴 **차는 다리만** 굵게 — 어느 쪽인지는 서버가 준다(`swing_leg`).
  final Path kick;

  /// 관절 고리를 찍을 자리 — 🔴 **몸의 마디 열둘만**(얼굴은 머리 원이 대신한다).
  final List<Offset> joints;
}

/// 🔴 **얼굴은 안 찍는다** — 머리 원이 대신한다(웹 `BODY_JOINTS`).
const List<String> kBodyJoints = [
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

/// 머리 반지름 — 🔴 **몸통 길이의 0.22배**(웹 `HEAD_BY_TORSO`).
///
/// ⛔ 어깨 폭으로 재지 말 것 — 옆으로 선 자세(차는 순간이 대개 그렇다)에서는
/// 두 어깨가 겹쳐 폭이 0 에 가까워 **머리가 사라진다.**
const double kHeadByTorso = 0.22;

/// 몸통을 못 재면 — 어깨 폭의 0.3배(웹 `HEAD_BY_SHOULDERS`).
const double kHeadByShoulders = 0.3;

/// 이름으로 점을 찾아 **화면 좌표**로 주는 함수. 없으면 `null`.
typedef JointResolver = Offset? Function(String name);

/// 자세 하나를 경로로 짠다.
///
/// [resolve] 가 좌표계를 정한다 — 영상 위면 영상 칸 크기를, 비교 카드면
/// 정규화 격자를 물린다. **모양 규칙은 좌표계와 무관하다.**
SkeletonShapes buildSkeletonShapes(JointResolver resolve, {String? swingLeg}) {
  final bones = Path();
  final kick = Path();

  void edge(Path into, String a, String b) {
    final p = resolve(a);
    final q = resolve(b);
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

  Offset? mid(String a, String b) {
    final p = resolve(a);
    final q = resolve(b);
    return (p == null || q == null) ? null : (p + q) / 2;
  }

  /* 🔴 **몸통은 척추 한 줄이다** — 어깨 가운데 → 골반 가운데. 옆선 둘로 그리면
     몸통이 **빈 네모**로 보인다(웹이 그래서 바꿨다). */
  final neck = mid('left_shoulder', 'right_shoulder');
  final pelvis = mid('left_hip', 'right_hip');
  if (neck != null && pelvis != null) {
    bones
      ..moveTo(neck.dx, neck.dy)
      ..lineTo(pelvis.dx, pelvis.dy);
  } else {
    edge(bones, 'left_shoulder', 'left_hip');
    edge(bones, 'right_shoulder', 'right_hip');
  }

  for (final leg in ['left', 'right']) {
    for (final (a, b) in _kLegs[leg]!) {
      edge(leg == swingLeg ? kick : bones, a, b);
    }
  }

  /* 머리 — 🔴 **두 귀 가운데.** 옆모습이라 귀가 하나면 **코와 그 귀의 가운데**
     (코는 얼굴 앞, 귀는 머리 뒤라 둘의 가운데가 머리 중심에 가깝다).
     그것도 없으면 보이는 점 하나. */
  final nose = resolve('nose');
  final ear = resolve('left_ear') ?? resolve('right_ear');
  final center = mid('left_ear', 'right_ear') ??
      ((ear != null && nose != null) ? (ear + nose) / 2 : (nose ?? ear));
  final ls = resolve('left_shoulder');
  final rs = resolve('right_shoulder');
  final r = (neck != null && pelvis != null)
      ? (neck - pelvis).distance * kHeadByTorso
      : (ls != null && rs != null)
      ? (ls - rs).distance * kHeadByShoulders
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

  return SkeletonShapes(
    bones: bones,
    kick: kick,
    joints: [
      for (final name in kBodyJoints) ?resolve(name),
    ],
  );
}

/// 짜 놓은 [shapes] 를 칠한다 — **어두운 테를 통째로 깐 뒤 그 위에 색을 얹는다.**
///
/// [scale] 은 선 굵기만 줄이고 늘린다(비교 카드는 격자가 작아 같은 굵기면
/// 뼈대가 뭉개진다). ⚠️ 좌표는 이미 [shapes] 안에 들어 있어 안 건드린다.
void paintSkeleton(
  Canvas canvas,
  SkeletonShapes shapes, {
  required Color color,
  double scale = 1,
  bool joints = true,
  bool halo = true,
}) {
  Paint stroke(double w, Color c) => Paint()
    ..style = PaintingStyle.stroke
    ..strokeWidth = w * scale
    ..strokeCap = StrokeCap.round
    ..strokeJoin = StrokeJoin.round
    ..color = c;

  /* 🔴 **어두운 테를 끌 수 있다.** 두 뼈대를 겹쳐 그리는 카드에서 위에 오는
     쪽이 테를 두르면, 자세가 비슷할 때 **아래 뼈대를 지워 버린다**
     (2026-09-25 사용자 지적: 「3관절 카드에는 선수꺼 관절 자체도 사라졌다」 —
     두 자세가 116° 대 114° 로 거의 같았던 회차다). */
  if (halo) {
    canvas
      ..drawPath(shapes.bones, stroke(kBoneWidth + 2, kSkeletonHalo))
      ..drawPath(shapes.kick, stroke(kKickBoneWidth + 2, kSkeletonHalo));
  }
  canvas
    ..drawPath(shapes.bones, stroke(kBoneWidth, color))
    ..drawPath(shapes.kick, stroke(kKickBoneWidth, color));

  if (!joints) return;

  /* 관절 — 🔴 **고리다.** 흰 획 위에 같은 자리를 어두운 획으로 한 번 더 찍어
     가운데를 판다(웹 `.ss-shot-joint` + `.ss-shot-joint-core`).
     ⛔ 속을 채우지 말 것 — 점이 뭉쳐 보인다. */
  final ring = Path();
  for (final p in shapes.joints) {
    ring
      ..moveTo(p.dx, p.dy)
      ..lineTo(p.dx, p.dy);
  }
  canvas
    ..drawPath(ring, stroke(kJointOuter + 1.5, kSkeletonHalo))
    ..drawPath(ring, stroke(kJointOuter, const Color(0xFFFFFFFF)))
    ..drawPath(ring, stroke(kJointCore, const Color(0xCC000000)));
}
