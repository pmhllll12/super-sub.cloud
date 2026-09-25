/// 한 순간의 자세와, 그것을 **이름으로** 읽는 길.
///
/// 🔴 **자리 번호를 상수로 박지 않는다.** 웹의 같은 코드(`www/src/lib/motion/angles.ts`)는
/// `lShoulder: 5` 처럼 COCO-17 순서를 하드코딩해 두었는데, 서버가 순서를 바꾸면
/// **아무 데서도 안 터지고 그림과 각도만 조용히 틀어진다.** `skeleton.dart` 머리말이
/// 이미 그걸 「하지 말 것」으로 적어 두었고, 여기서 그 규칙을 지킨다 —
/// 뜻은 서버가 준 `keypoint_names` 가 정한다.
library;

import 'dart:math' as math;

/// 관절 하나. 좌표는 **0~1 로 눌린 화면 비율**이고, [score] 는 확신이다.
///
/// 🔴 **0~1 을 벗어날 수 있다 — 자르지 말 것**(계약 3-14절). 화면 밖으로 나간
/// 관절이 실제로 있고, 자르면 발이 가장자리에 붙은 것처럼 그려진다.
class Joint {
  const Joint(this.x, this.y, [this.score = 1]);
  final double x;
  final double y;
  final double score;

  Joint copyWith({double? x, double? y, double? score}) =>
      Joint(x ?? this.x, y ?? this.y, score ?? this.score);
}

/// 이 값보다 확신이 낮은 관절은 **없는 것으로 친다** (웹 `MIN_KP`).
const double kMinConfidence = 0.3;

/// 볼 만한 관절인가 — `null` 이거나 확신이 낮으면 거짓.
bool seen(Joint? p) => p != null && p.score >= kMinConfidence;

/// 두 점의 가운데. 한쪽이라도 안 보이면 `null`.
Joint? midJoint(Joint? a, Joint? b) {
  if (!seen(a) || !seen(b)) return null;
  return Joint(
    (a!.x + b!.x) / 2,
    (a.y + b.y) / 2,
    math.min(a.score, b.score),
  );
}

/// 한 프레임의 관절 전부 — **이름표를 달고 다닌다.**
class Pose {
  const Pose({required this.names, required this.points});

  /// 자리마다의 뜻 (`nose` · `left_shoulder` …). [points] 와 길이가 같다.
  final List<String> names;
  final List<Joint?> points;

  /// 이름으로 읽는다. 없거나 확신이 낮으면 `null`.
  ///
  /// 🔴 **이것이 유일한 읽는 길이다** — 번호로 직접 꺼내지 말 것(위 머리말).
  Joint? operator [](String name) {
    final i = names.indexOf(name);
    if (i < 0 || i >= points.length) return null;
    final p = points[i];
    return seen(p) ? p : null;
  }

  /// 자리를 지킨 채 점을 갈아 끼운다 — 정규화가 쓴다.
  Pose mapPoints(Joint? Function(Joint? p) f) =>
      Pose(names: names, points: [for (final p in points) f(p)]);
}

/// 차는 다리의 세 마디 이름.
({String hip, String knee, String ankle}) legOf(String leg) => (
  hip: '${leg}_hip',
  knee: '${leg}_knee',
  ankle: '${leg}_ankle',
);

String otherLeg(String leg) => leg == 'left' ? 'right' : 'left';
