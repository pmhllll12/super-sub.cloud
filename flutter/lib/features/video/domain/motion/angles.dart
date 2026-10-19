/// 관절 각도 — 🔴 **가로 좌표에 `aspect` 를 곱해** 화면 비율을 되돌린 뒤 잰다.
///
/// 웹 `www/src/lib/motion/angles.ts` 를 옮긴 것이다. 셈은 한 줄도 안 바꿨고,
/// **읽는 방식만** 번호에서 이름으로 바꿨다(`pose.dart` 머리말).
library;

import 'dart:math' as math;

import 'motion.dart';
import 'pose.dart';

/// 항목 이름 — 🔴 루브릭(`agent/rubrics/football_instep_shot.yaml`)의
/// `criteria[].name` 그대로다. 마음대로 고치면 제안서·리포트와 갈린다.
enum Metric { plantKneeFlexion, swingKneeExtension, trunkLean, followThrough }

extension MetricLabel on Metric {
  String get id => switch (this) {
    Metric.plantKneeFlexion => 'plant_knee_flexion',
    Metric.swingKneeExtension => 'swing_knee_extension',
    Metric.trunkLean => 'trunk_lean',
    Metric.followThrough => 'follow_through',
  };

  String get label => switch (this) {
    Metric.plantKneeFlexion => '디딤발 무릎 굽히기',
    Metric.swingKneeExtension => '차는 다리 뻗기',
    Metric.trunkLean => '상체 기울기',
    Metric.followThrough => '차고 난 뒤 마무리',
  };
}

/// 순간마다 재는 항목 — `after` 는 무릎을 안 본다(이미 차고 난 뒤라 뜻이 없다).
const Map<MomentKey, List<Metric>> kMetricsAt = {
  MomentKey.before: [
    Metric.plantKneeFlexion,
    Metric.swingKneeExtension,
    Metric.trunkLean,
  ],
  MomentKey.impact: [
    Metric.plantKneeFlexion,
    Metric.swingKneeExtension,
    Metric.trunkLean,
  ],
  MomentKey.after: [Metric.trunkLean, Metric.followThrough],
};

/// 한 항목의 두 값 — 비교 한 줄이 되는 단위.
class MetricRow {
  const MetricRow({
    required this.metric,
    required this.player,
    required this.user,
  });

  final Metric metric;

  /// 🔴 **둘 다 도(°) 이고 이미 반올림되어 있다** — 화면이 다시 굴리지 않는다.
  final int player;
  final int user;

  String get label => metric.label;
}

/// b 에서 잰 a–b–c 각(도, 0~180). 셋 중 하나라도 안 보이면 `null`.
double? jointAngle(Joint? a, Joint? b, Joint? c, double aspect) {
  if (!seen(a) || !seen(b) || !seen(c)) return null;
  final ux = (a!.x - b!.x) * aspect;
  final uy = a.y - b.y;
  final vx = (c!.x - b.x) * aspect;
  final vy = c.y - b.y;
  final nu = math.sqrt(ux * ux + uy * uy);
  final nv = math.sqrt(vx * vx + vy * vy);
  if (nu == 0 || nv == 0) return null;
  final cos = math.max(-1.0, math.min(1.0, (ux * vx + uy * vy) / (nu * nv)));
  return math.acos(cos) * 180 / math.pi;
}

/// 엉덩이–무릎–발목 각.
double? kneeAngle(Pose pose, String leg, double aspect) {
  final j = legOf(leg);
  return jointAngle(pose[j.hip], pose[j.knee], pose[j.ankle], aspect);
}

/// 골반 중점 → 어깨 중점 선이 수직에서 **차는 방향으로** 넘어간 각. 뒤로면 음수.
double? trunkLean(Pose pose, int direction, double aspect) {
  final s = midJoint(pose['left_shoulder'], pose['right_shoulder']);
  final h = midJoint(pose['left_hip'], pose['right_hip']);
  if (s == null || h == null) return null;
  final dx = (s.x - h.x) * aspect * direction;
  final up = h.y - s.y;
  if (up == 0 && dx == 0) return null;
  return math.atan2(dx, up) * 180 / math.pi;
}

/// 차는 다리 엉덩이 굴곡 — 몸통과 허벅지가 곧게 이어지면 0, 앞으로 들수록 커진다.
double? hipFlexion(Pose pose, String leg, double aspect) {
  final s = midJoint(pose['left_shoulder'], pose['right_shoulder']);
  final j = legOf(leg);
  final a = jointAngle(s, pose[j.hip], pose[j.knee], aspect);
  return a == null ? null : 180 - a;
}

/// 한 사람의 한 순간 — 각도를 재는 데 필요한 전부.
class Side {
  const Side({
    required this.pose,
    required this.kickingLeg,
    required this.direction,
    required this.aspect,
  });

  final Pose pose;
  final String kickingLeg;
  final int direction;
  final double aspect;
}

/// 그 순간의 [Side]. 🔴 **그 프레임을 못 잡았으면 `null`** — 앞뒤 프레임으로
/// 때우지 않는다. 차는 순간은 한 장만 어긋나도 다른 자세가 된다.
Side? sideAt(Motion motion, Moments moments, MomentKey key) {
  final pose = motion.at(moments[key]);
  if (pose == null) return null;
  return Side(
    pose: pose,
    kickingLeg: moments.kickingLeg,
    direction: moments.direction,
    aspect: motion.aspect,
  );
}

double? _valueOf(Metric m, Side s) => switch (m) {
  Metric.plantKneeFlexion => kneeAngle(s.pose, otherLeg(s.kickingLeg), s.aspect),
  Metric.swingKneeExtension => kneeAngle(s.pose, s.kickingLeg, s.aspect),
  Metric.trunkLean => trunkLean(s.pose, s.direction, s.aspect),
  Metric.followThrough => hipFlexion(s.pose, s.kickingLeg, s.aspect),
};

/// 🔴 **두 사람 다 잰 항목만** 행으로 낸다 — 한쪽이 비면 비교가 아니다.
List<MetricRow> metricsAt(MomentKey key, Side player, Side user) {
  final rows = <MetricRow>[];
  for (final m in kMetricsAt[key]!) {
    final a = _valueOf(m, player);
    final b = _valueOf(m, user);
    if (a == null || b == null) continue;
    rows.add(MetricRow(metric: m, player: a.round(), user: b.round()));
  }
  return rows;
}
