/// 비교가 다루는 모양 — **어디서 왔는지 모르는 자세 시계열**과 세 순간.
///
/// 🔴 **앱은 관절을 뽑지 않는다.** 웹은 브라우저에서 MoveNet 을 돌려 이 모양을
/// 만들지만(`www/src/lib/motion/extract.ts`), 앱은 **서버가 이미 낸 것**을 그대로
/// 받는다(계약 3-14절). 그래서 웹에 있는 것 중 **두 가지가 앱엔 아예 없다**:
///
/// - `moments.ts` (세 순간을 무릎 각속도 피크로 **찾는** 코드) — 서버가 골라 준다
/// - `extract.ts` · `personDetector.ts` (tfjs·canvas) — 옮길 것도 없다
///
/// 덤으로 **더 촘촘하다** — 브라우저는 10fps 로 훑는데 서버 값은 30fps 다.
library;

import '../../data/models/skeleton.dart';
import 'pose.dart';

/// 자세 시계열.
class Motion {
  const Motion({required this.fps, required this.aspect, required this.frames});

  final double fps;

  /// 영상 가로/세로. 🔴 좌표가 가로·세로 **따로** 0~1 로 눌려 있어, 각도를 잴 때
  /// 가로에 이 값을 곱해 비율을 되돌린다.
  final double aspect;

  /// 프레임마다의 자세. 🔴 **못 잡은 프레임은 `null` 로 자리를 지킨다** —
  /// 빼고 압축하면 인덱스가 밀려 세 순간이 엉뚱한 자세를 가리키는데,
  /// 뼈대는 어느 쪽이든 그럴듯해 보여 **눈으로도 안 잡힌다**(계약).
  final List<Pose?> frames;

  Pose? at(int frame) =>
      (frame < 0 || frame >= frames.length) ? null : frames[frame];
}

/// 세 순간 — 서버가 고른 **프레임 번호**와, 차는 다리·방향.
class Moments {
  const Moments({
    required this.kickingLeg,
    required this.direction,
    required this.before,
    required this.impact,
    required this.after,
    this.afterClipped = false,
  });

  /// `left` · `right`.
  final String kickingLeg;

  /// 차는 방향 — 화면 오른쪽이 `1`.
  final int direction;

  final int before;
  final int impact;
  final int after;

  /// `after` 가 영상 끝에 걸려 마지막 프레임으로 대신했는가.
  final bool afterClipped;

  int operator [](MomentKey key) => switch (key) {
    MomentKey.before => before,
    MomentKey.impact => impact,
    MomentKey.after => after,
  };
}

enum MomentKey { before, impact, after }

/// 계약에 실리는 키 — 🔴 **서버 `moments` 맵의 열쇠와 같아야 한다.**
extension MomentKeyWire on MomentKey {
  String get wire => switch (this) {
    MomentKey.before => 'before',
    MomentKey.impact => 'impact',
    MomentKey.after => 'after',
  };

  /// 화면에 적는 이름 — 🔴 **이름만 바꾼 것이다**(2026-09-15 사용자 요청:
  /// 직전 → 백스윙 · 임팩트 → 접촉 · +1초 → 접촉 후). 위 [wire] 는 안 바뀐다.
  String get label => switch (this) {
    MomentKey.before => '백스윙',
    MomentKey.impact => '접촉',
    MomentKey.after => '접촉 후',
  };
}

/// 서버가 준 [Skeleton] 을 비교가 쓰는 모양으로 옮긴다.
///
/// 🔴 **셋 중 하나라도 없으면 `null` 이다** — 관절(`known`) · 세 순간 · 차는 다리.
/// 하나라도 지어내면 비교가 **조용히 틀린 값**을 낸다. 화면은 그때 「비교할 수
/// 없습니다」로 물러난다.
({Motion motion, Moments moments})? motionOf(Skeleton s) {
  if (!s.known || s.joints.isEmpty || s.frameHeight <= 0) return null;

  final leg = s.swingLeg;
  if (leg != 'left' && leg != 'right') return null;

  final before = s.moments[MomentKey.before.wire];
  final impact = s.moments[MomentKey.impact.wire];
  final after = s.moments[MomentKey.after.wire];
  if (before == null || impact == null || after == null) return null;

  return (
    motion: Motion(
      fps: s.fps,
      aspect: s.frameWidth / s.frameHeight,
      frames: [
        for (final frame in s.joints)
          if (frame == null)
            null
          else
            Pose(
              names: s.keypointNames,
              points: [
                for (final kp in frame)
                  kp.length < 3 ? null : Joint(kp[0], kp[1], kp[2]),
              ],
            ),
      ],
    ),
    moments: Moments(
      kickingLeg: leg!,
      // 🔴 방향은 **오른쪽이 1** — 서버가 안 주면 오른쪽으로 본다(웹과 같다).
      direction: s.direction == -1 ? -1 : 1,
      before: before,
      impact: impact,
      after: after,
      afterClipped: s.afterClipped,
    ),
  );
}
