/// 두 뼈대를 겹치는 셈 — 🔴 **골반 중점 원점 · 몸통 길이 1.**
///
/// 키와 카메라 거리를 지우고 **자세 차이만** 남긴다. 가로 좌표에는 `aspect` 를
/// 곱해 화면 비율을 되돌린다. 웹 `www/src/lib/motion/align.ts` 를 옮긴 것이다.
library;

import 'dart:math' as math;

import 'motion.dart';
import 'pose.dart';

/// 골반 중점을 원점으로, 몸통 길이를 1 로 맞춘 자세.
///
/// 어깨나 골반을 못 잡았으면 `null` — 그 둘이 자와 원점이라 없으면 겹칠 수가 없다.
/// [flip] 이면 **가로만** 뒤집는다.
Pose? normalizePose(Pose pose, double aspect, bool flip) {
  final s = midJoint(pose['left_shoulder'], pose['right_shoulder']);
  final h = midJoint(pose['left_hip'], pose['right_hip']);
  if (s == null || h == null) return null;
  final dx = (s.x - h.x) * aspect;
  final dy = s.y - h.y;
  final torso = math.sqrt(dx * dx + dy * dy);
  if (torso == 0) return null;
  final sign = flip ? -1 : 1;
  return pose.mapPoints(
    (p) => seen(p)
        ? Joint(sign * (p!.x - h.x) * aspect / torso, (p.y - h.y) / torso, p.score)
        : null,
  );
}

/// 🔴 **차는 방향이 다를 때만 뒤집는다.**
///
/// 차는 발만 다를 때 뒤집으면 방향이 오히려 갈린다(오른발잡이와 왼발잡이가 같은
/// 방향으로 차는 일이 흔하다). 판별이 틀릴 수 있어 화면에 되돌리는 토글을 둔다.
bool shouldMirror(Moments player, Moments user) =>
    player.direction != user.direction;
