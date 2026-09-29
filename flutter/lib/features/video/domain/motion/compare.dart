/// 선수와 나를 **한 덩어리로** 비교한다 — 화면이 부르는 유일한 입구.
///
/// 🔴 **화면은 관절도 각도도 모른다.** 서버가 준 [Skeleton] 둘을 넣으면
/// 겹칠 좌표 · 각도 행 · 문장이 한 번에 나온다. 그래야 웹과 값이 안 갈린다.
library;

import '../../data/models/skeleton.dart';
import 'align.dart';
import 'angles.dart';
import 'describe.dart';
import 'motion.dart';
import 'pose.dart';

/// 한 순간에 겹쳐 그릴 두 자세 — 이미 **골반 원점 · 몸통 1** 로 맞춰져 있다.
class MomentPoses {
  const MomentPoses({required this.key, this.player, this.user});
  final MomentKey key;

  /// 🔴 **`null` 이면 그 순간은 못 그린다** — 억지로 그리지 말 것.
  final Pose? player;
  final Pose? user;
}

class Comparison {
  const Comparison({
    required this.playerName,
    required this.mirrored,
    required this.poses,
    required this.metrics,
    required this.text,
    required this.playerMotion,
    required this.playerMoments,
    required this.userMotion,
    required this.userMoments,
  });

  final String playerName;

  /// 선수 쪽을 가로로 뒤집었는가 — 🔴 **선수만 뒤집는다**(내 영상은 그대로).
  final bool mirrored;

  final List<MomentPoses> poses;
  final List<MomentMetrics> metrics;
  final ComparisonText text;

  /// 영상 위에 뼈대를 겹칠 때 쓰는 원본 — 세 순간의 **초**를 찾는 데도 쓴다.
  final Motion playerMotion;
  final Moments playerMoments;
  final Motion userMotion;
  final Moments userMoments;

  /// 그 순간의 **재생 위치**. 되감을 자리를 화면이 여기서 얻는다.
  Duration playerAt(MomentKey key) => _positionOf(playerMotion, playerMoments, key);
  Duration userAt(MomentKey key) => _positionOf(userMotion, userMoments, key);
}

Duration _positionOf(Motion m, Moments moments, MomentKey key) {
  if (m.fps <= 0) return Duration.zero;
  return Duration(milliseconds: (moments[key] / m.fps * 1000).round());
}

/// 왜 비교를 못 했는가 — 화면이 그대로 보여 주는 문구.
class CompareFailure {
  const CompareFailure(this.reason);
  final String reason;
}

/// 선수와 내 영상을 비교한다.
///
/// [mirrorOverride] 가 있으면 자동 판별 대신 그 값을 쓴다(화면의 뒤집기 토글).
///
/// 🔴 **못 하면 지어내지 않고 [CompareFailure] 로 돌려준다.** 관절이 없는 옛
/// 리포트(`known: false`)와 세 순간이 없는 분석이 실제로 있다.
({Comparison? ok, CompareFailure? failed}) compareSkeletons({
  required String playerName,
  required Skeleton player,
  required Skeleton user,
  bool? mirrorOverride,
}) {
  final p = motionOf(player);
  if (p == null) {
    return (ok: null, failed: const CompareFailure('선수 영상의 관절을 읽지 못했습니다.'));
  }
  final u = motionOf(user);
  if (u == null) {
    return (
      ok: null,
      failed: const CompareFailure(
        // 🔴 「없다」가 아니라 **왜 없는지**를 적는다 — 분석을 안 건 영상이
        //    대부분이라, 그걸 모르면 사용자가 같은 영상으로 계속 눌러 본다.
        '이 영상은 아직 관절을 잴 수 없습니다. 분석이 끝난 영상만 비교할 수 있습니다.',
      ),
    );
  }

  final mirrored = mirrorOverride ?? shouldMirror(p.moments, u.moments);

  final poses = <MomentPoses>[];
  final metrics = <MomentMetrics>[];
  for (final key in MomentKey.values) {
    final ps = sideAt(p.motion, p.moments, key);
    final us = sideAt(u.motion, u.moments, key);
    poses.add(
      MomentPoses(
        key: key,
        player: ps == null
            ? null
            : normalizePose(ps.pose, ps.aspect, mirrored),
        user: us == null ? null : normalizePose(us.pose, us.aspect, false),
      ),
    );
    metrics.add(
      MomentMetrics(
        key: key,
        // 한쪽 순간을 못 잡았으면 그 순간은 **빈 행**이다 — 문장이 그렇게 적는다.
        metrics: (ps == null || us == null)
            ? const []
            : metricsAt(key, ps, us),
      ),
    );
  }

  return (
    ok: Comparison(
      playerName: playerName,
      mirrored: mirrored,
      poses: poses,
      metrics: metrics,
      text: describeComparison(metrics),
      playerMotion: p.motion,
      playerMoments: p.moments,
      userMotion: u.motion,
      userMoments: u.moments,
    ),
    failed: null,
  );
}
