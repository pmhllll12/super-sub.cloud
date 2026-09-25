/// 웹 `www/src/lib/motion/{angles,align,describe}.test.ts` 를 그대로 옮긴 것.
///
/// 🔴 **옮긴 시험이 곧 규격이다.** 같은 영상에 웹과 앱이 다른 각도·다른 문장을
/// 내면 그게 버그라서, 웹이 지키던 단언을 그대로 지킨다. 숫자를 느슨하게
/// 고치지 말 것 — 느슨해지는 순간 이 시험은 아무것도 안 잡는다.
library;

import 'dart:math' as math;

import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/video/data/models/skeleton.dart';
import 'package:super_sub/features/video/domain/motion/align.dart';
import 'package:super_sub/features/video/domain/motion/angles.dart';
import 'package:super_sub/features/video/domain/motion/compare.dart';
import 'package:super_sub/features/video/domain/motion/describe.dart';
import 'package:super_sub/features/video/domain/motion/motion.dart';
import 'package:super_sub/features/video/domain/motion/pose.dart';

/// COCO-17 이름 — 서버가 주는 `keypoint_names` 와 같은 차례.
const kNames = [
  'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
  'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
  'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
  'left_knee', 'right_knee', 'left_ankle', 'right_ankle',
];

/// 웹 `kickFixture.ts` 의 `posture` — 오른발로 차는 사람을 옆에서 본 관절.
Pose posture({
  required double rightKnee,
  double leftKnee = 160,
  int dir = 1,
  double lean = 0,
  double hipX = 0.5,
}) {
  final pts = List<Joint?>.filled(17, const Joint(0, 0, 0));
  const hipY = 0.5;
  const l = 0.1;
  final lx = hipX - 0.01;
  final rx = hipX + 0.01;
  pts[0] = const Joint(0, 0, 0.9).copyWith(x: hipX, y: hipY - 0.4);
  pts[5] = Joint(lx + lean, hipY - 0.3, 0.9);
  pts[6] = Joint(rx + lean, hipY - 0.3, 0.9);
  pts[11] = Joint(lx, hipY, 0.9);
  pts[12] = Joint(rx, hipY, 0.9);
  // 허벅지는 곧게 아래로, 정강이는 무릎각만큼 뒤로 접힌다.
  (Joint, Joint) leg(double hx, double knee) {
    final bend = (180 - knee) * math.pi / 180;
    return (
      Joint(hx, hipY + l, 0.9),
      Joint(hx - dir * math.sin(bend) * l, hipY + l + math.cos(bend) * l, 0.9),
    );
  }

  final (lk, la) = leg(lx, leftKnee);
  final (rk, ra) = leg(rx, rightKnee);
  pts[13] = lk;
  pts[15] = la;
  pts[14] = rk;
  pts[16] = ra;
  return Pose(names: kNames, points: pts);
}

/// 웹 `kickMotion` — 무릎각만 바꿔 만든 동작. 15번이 각속도 최대(= 접촉).
const _kRightKnee = <double>[
  170, 170, 170, 170, 170, 170, 170, 170, 170, 170,
  150, 130, 110, 95, 90, // 10~14 뒤로 접는다
  120, 165, 175, // 15~17 편다
];

Motion kickMotion({int dir = 1, double fps = 15, int frames = 46, double lean = 0}) =>
    Motion(
      fps: fps,
      aspect: 1,
      frames: [
        for (var i = 0; i < frames; i += 1)
          posture(
            rightKnee: _kRightKnee[math.min(_kRightKnee.length - 1, i)],
            dir: dir,
            lean: lean,
          ),
      ],
    );

const _base = Moments(
  kickingLeg: 'right',
  direction: 1,
  before: 14,
  impact: 15,
  after: 30,
);

void main() {
  group('각도', () {
    test('무릎각은 엉덩이–무릎–발목 사이 각이다', () {
      final pose = posture(rightKnee: 120);
      expect(kneeAngle(pose, 'right', 1), closeTo(120, 1e-5));
      expect(kneeAngle(pose, 'left', 1), closeTo(160, 1e-5));
    });

    // 🔴 좌표가 가로·세로 따로 0~1 이라, 16:9 에서 비율을 안 되돌리면 각이 비뚤어진다.
    test('가로 좌표에 화면 비율을 곱해 잰다', () {
      const a = Joint(0, 0);
      const b = Joint(0, 0.1);
      const c = Joint(0.1, 0.1);
      expect(jointAngle(a, b, c, 1), closeTo(90, 1e-5));
      expect(jointAngle(a, b, c, 16 / 9), closeTo(90, 1e-5));
      const d = Joint(0.1, 0.2);
      expect(jointAngle(a, b, d, 1), closeTo(135, 1e-5));
      expect((jointAngle(a, b, d, 16 / 9)! - 135).abs(), greaterThan(1));
    });

    test('점수가 낮은 관절이 끼면 재지 않는다', () {
      final pose = posture(rightKnee: 120);
      final pts = [...pose.points];
      pts[16] = pts[16]!.copyWith(score: 0.1);
      expect(kneeAngle(Pose(names: kNames, points: pts), 'right', 1), isNull);
    });

    test('상체 기울기는 차는 방향으로 넘어가면 양수, 뒤로면 음수다', () {
      final forward = posture(rightKnee: 170, lean: 0.1);
      final want = math.atan2(0.1, 0.3) * 180 / math.pi;
      expect(trunkLean(forward, 1, 1), closeTo(want, 1e-5));
      expect(trunkLean(forward, -1, 1), closeTo(-want, 1e-5));
      expect(trunkLean(posture(rightKnee: 170), 1, 1), closeTo(0, 1e-5));
    });

    // 가짜 자세는 어깨 중점과 오른쪽 엉덩이가 가로로 0.01 벌어져 정확히 0 은 아니다.
    test('엉덩이 굴곡은 몸통과 허벅지가 곧으면 0 가깝고, 앞으로 들면 커진다', () {
      expect(hipFlexion(posture(rightKnee: 170), 'right', 1)!.abs(), lessThan(3));
      final lifted = posture(rightKnee: 170);
      final pts = [...lifted.points];
      pts[14] = Joint(pts[12]!.x + 0.1, pts[12]!.y, 0.9); // 허벅지를 앞으로 수평
      expect(
        hipFlexion(Pose(names: kNames, points: pts), 'right', 1),
        greaterThan(80),
      );
    });

    test('순간마다 정해진 항목만, 반올림해서 낸다', () {
      final player = sideAt(kickMotion(), _base, MomentKey.impact)!;
      final user = sideAt(kickMotion(lean: 0.05), _base, MomentKey.impact)!;
      final rows = metricsAt(MomentKey.impact, player, user);
      expect(
        rows.map((r) => r.metric).toList(),
        [Metric.plantKneeFlexion, Metric.swingKneeExtension, Metric.trunkLean],
      );
      expect(rows[0].label, '디딤발 무릎 굽히기');
      expect(rows[0].player, 160);
      expect(rows[0].user, 160);
      expect(rows[1].player, 120);
      expect(rows[1].user, 120);
      expect(rows[2].player, 0);
      expect(rows[2].user, (math.atan2(0.05, 0.3) * 180 / math.pi).round());
      expect(
        metricsAt(MomentKey.after, player, user).map((r) => r.metric).toList(),
        [Metric.trunkLean, Metric.followThrough],
      );
    });

    test('그 순간 프레임을 못 잡았으면 sideAt 은 null 이다', () {
      final m = kickMotion();
      final frames = [...m.frames]..[15] = null;
      final holed = Motion(fps: m.fps, aspect: m.aspect, frames: frames);
      expect(sideAt(holed, _base, MomentKey.impact), isNull);
    });
  });

  group('겹치기', () {
    test('골반 중점이 원점, 몸통 길이가 1 이 된다', () {
      final n = normalizePose(posture(rightKnee: 170), 1, false)!;
      final hip = midJoint(n['left_hip'], n['right_hip'])!;
      final sh = midJoint(n['left_shoulder'], n['right_shoulder'])!;
      expect(hip.x, closeTo(0, 1e-6));
      expect(hip.y, closeTo(0, 1e-6));
      final dx = sh.x - hip.x;
      final dy = sh.y - hip.y;
      expect(math.sqrt(dx * dx + dy * dy), closeTo(1, 1e-6));
    });

    // 🔴 서 있는 자리가 달라도 같은 자세면 같은 좌표가 되어야 겹쳐 비교된다.
    test('위치가 달라도 같은 자세면 같은 좌표다', () {
      final a = normalizePose(posture(rightKnee: 120, hipX: 0.3), 1, false)!;
      final b = normalizePose(posture(rightKnee: 120, hipX: 0.7), 1, false)!;
      for (var i = 0; i < a.points.length; i += 1) {
        final p = a.points[i];
        if (p == null) continue;
        expect(b.points[i]!.x, closeTo(p.x, 1e-6));
        expect(b.points[i]!.y, closeTo(p.y, 1e-6));
      }
    });

    test('flip 이면 가로만 뒤집는다', () {
      final a = normalizePose(posture(rightKnee: 120), 1, false)!;
      final b = normalizePose(posture(rightKnee: 120), 1, true)!;
      expect(b['right_ankle']!.x, closeTo(-a['right_ankle']!.x, 1e-6));
      expect(b['right_ankle']!.y, closeTo(a['right_ankle']!.y, 1e-6));
    });

    test('어깨나 골반을 못 잡았으면 null 이다', () {
      final pose = posture(rightKnee: 120);
      final pts = [...pose.points];
      pts[5] = pts[5]!.copyWith(score: 0);
      expect(normalizePose(Pose(names: kNames, points: pts), 1, false), isNull);
    });

    test('차는 방향이 다를 때만 뒤집는다 — 차는 발만 다르면 안 뒤집는다', () {
      const flipped = Moments(
        kickingLeg: 'right', direction: -1, before: 14, impact: 15, after: 30,
      );
      const leftFoot = Moments(
        kickingLeg: 'left', direction: 1, before: 14, impact: 15, after: 30,
      );
      expect(shouldMirror(_base, flipped), isTrue);
      expect(shouldMirror(_base, leftFoot), isFalse);
      expect(shouldMirror(_base, _base), isFalse);
    });
  });

  group('규칙 문장', () {
    MetricRow row(Metric m, int player, int user) =>
        MetricRow(metric: m, player: player, user: user);

    test('차이가 5° 미만이면 비슷하다고 적는다', () {
      expect(
        describeLine(row(Metric.trunkLean, 10, 13)),
        '상체 기울기 선수 10° · 나 13° — 비슷합니다',
      );
    });

    // 🔴 값이 크다는 뜻이 항목마다 다르다 — 무릎각이 크면 「덜 굽힘」.
    test('항목마다 방향에 맞는 말로 차이를 적는다', () {
      expect(
        describeLine(row(Metric.plantKneeFlexion, 142, 158)),
        '디딤발 무릎 굽히기 선수 142° · 나 158° — 디딤발 무릎을 16° 덜 굽혔습니다',
      );
      expect(
        describeLine(row(Metric.swingKneeExtension, 171, 149)),
        '차는 다리 뻗기 선수 171° · 나 149° — 차는 다리를 22° 덜 폈습니다',
      );
      expect(
        describeLine(row(Metric.trunkLean, 12, -5)),
        '상체 기울기 선수 12° · 나 -5° — 상체가 차는 방향으로 17° 덜 기울었습니다',
      );
      expect(
        describeLine(row(Metric.followThrough, 40, 60)),
        '차고 난 뒤 마무리 선수 40° · 나 60° — 차는 다리를 20° 더 높이 들었습니다',
      );
    });

    test('순간마다 줄을 모으고, 잰 항목이 없으면 그렇다고 적는다', () {
      final text = describeComparison([
        MomentMetrics(key: MomentKey.before, metrics: [row(Metric.trunkLean, 10, 13)]),
        const MomentMetrics(key: MomentKey.impact, metrics: []),
        const MomentMetrics(key: MomentKey.after, metrics: []),
      ]);
      expect(
        text.moments.map((m) => m.key).toList(),
        [MomentKey.before, MomentKey.impact, MomentKey.after],
      );
      expect(text.moments[1].lines, ['이 순간은 잴 수 없었습니다']);
    });

    test('총평은 가장 큰 차이를 짚는다', () {
      final text = describeComparison([
        MomentMetrics(
          key: MomentKey.before,
          metrics: [row(Metric.plantKneeFlexion, 142, 158)],
        ),
        MomentMetrics(
          key: MomentKey.impact,
          metrics: [row(Metric.swingKneeExtension, 171, 149)],
        ),
        const MomentMetrics(key: MomentKey.after, metrics: []),
      ]);
      expect(
        text.summary,
        '가장 큰 차이는 접촉의 차는 다리 뻗기입니다 — 선수 171° · 나 149°(22° 차이).',
      );
    });

    test('모두 5° 미만이면 비슷하다고, 잰 것이 없으면 비교 못 했다고 적는다', () {
      final similar = describeComparison([
        MomentMetrics(key: MomentKey.before, metrics: [row(Metric.trunkLean, 10, 13)]),
        const MomentMetrics(key: MomentKey.impact, metrics: []),
        const MomentMetrics(key: MomentKey.after, metrics: []),
      ]);
      expect(similar.summary, '세 순간 모두 선수와 비슷합니다.');
      final none = describeComparison(const [
        MomentMetrics(key: MomentKey.before, metrics: []),
        MomentMetrics(key: MomentKey.impact, metrics: []),
        MomentMetrics(key: MomentKey.after, metrics: []),
      ]);
      expect(none.summary, '잴 수 있는 순간이 없어 비교하지 못했습니다.');
    });
  });

  group('서버 값을 비교로', () {
    /// 서버가 주는 모양 그대로 — 계약 3-14절.
    Skeleton skeletonOf({
      String swingLeg = 'right',
      int direction = 1,
      double lean = 0,
      Map<String, int>? moments,
      bool known = true,
    }) {
      final m = kickMotion(lean: lean);
      return Skeleton(
        known: known,
        fps: 15,
        frameWidth: 1280,
        frameHeight: 720,
        swingLeg: swingLeg,
        direction: direction,
        keypointNames: kNames,
        joints: [
          for (final f in m.frames)
            f == null
                ? null
                : [for (final p in f.points) [p!.x, p.y, p.score]],
        ],
        moments: moments ?? const {'before': 14, 'impact': 15, 'after': 30},
      );
    }

    test('선수와 내 영상을 겹쳐 세 순간을 낸다', () {
      final r = compareSkeletons(
        playerName: '에스테반 로벨리',
        player: skeletonOf(),
        user: skeletonOf(lean: 0.05),
      );
      expect(r.failed, isNull);
      final c = r.ok!;
      expect(c.poses.map((p) => p.key).toList(), MomentKey.values);
      // 🔴 골반 원점 · 몸통 1 로 맞춰져 있어야 겹쳐 그릴 수 있다.
      final hip = midJoint(c.poses[1].player!['left_hip'], c.poses[1].player!['right_hip'])!;
      expect(hip.x, closeTo(0, 1e-6));
      expect(c.text.summary, contains('상체 기울기'));
    });

    test('차는 방향이 같으면 안 뒤집는다', () {
      final same = compareSkeletons(
        playerName: 'p', player: skeletonOf(), user: skeletonOf(),
      ).ok!;
      expect(same.mirrored, isFalse);
      final opposite = compareSkeletons(
        playerName: 'p', player: skeletonOf(), user: skeletonOf(direction: -1),
      ).ok!;
      expect(opposite.mirrored, isTrue);
    });

    // 🔴 관절이 없는 옛 리포트는 **200 으로** `known: false` 가 온다 — 오류가 아니다.
    test('관절이 없는 영상은 까닭을 말하고 물러난다', () {
      final r = compareSkeletons(
        playerName: 'p', player: skeletonOf(), user: skeletonOf(known: false),
      );
      expect(r.ok, isNull);
      expect(r.failed!.reason, contains('분석이 끝난 영상'));
    });

    test('세 순간이 없으면 비교하지 않는다', () {
      final r = compareSkeletons(
        playerName: 'p',
        player: skeletonOf(),
        user: skeletonOf(moments: const {'before': 1}),
      );
      expect(r.ok, isNull);
    });

    test('그 순간의 재생 위치를 프레임에서 환산한다', () {
      final c = compareSkeletons(
        playerName: 'p', player: skeletonOf(), user: skeletonOf(),
      ).ok!;
      // 15fps 의 15번째 프레임 = 1.0초
      expect(c.userAt(MomentKey.impact), const Duration(seconds: 1));
    });
  });
}
