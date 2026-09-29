/// 세 순간 카드 — **선수와 나의 뼈대를 겹쳐** 그린다.
///
/// 🔴 **겹치는 셈은 여기 없다**(`domain/motion/align.dart`). 이 파일은 이미
/// 골반 원점·몸통 1 로 맞춰진 좌표를 **카드 격자에 앉히기만** 한다.
///
/// 🔴 색은 **선수 마젠타 · 나 초록**(웹과 같다 — 적록색각을 고려한 사용자 결정).
/// ⛔ 둘 다 초록으로 두지 말 것 — 겹친 순간 누가 누군지 알 수 없다.
library;

import 'package:flutter/material.dart';

import '../../domain/motion/compare.dart';
import '../../domain/motion/motion.dart';
import '../../domain/motion/pose.dart';
import 'skeleton_shapes.dart';

/// 선수 — 웹 `--ss-pro`.
const Color kPlayerColor = Color(0xFFE85CC4);

/// 나 — 웹 `--ss-accent`.
const Color kUserColor = Color(0xFF57E389);

/// 🔴 **몸통 1 = 격자/4.2 · 골반은 가운데보다 조금 위(0.48).**
///
/// 웹 `align.ts` 의 `skeletonPath` 와 같은 값이다. 예전 값(3.6 · 0.42)은 얼굴
/// 점까지만 들어가서, 머리를 원으로 바꾸자 **원 윗부분이 격자 위로 나가 잘렸다**
/// (2026-09-15). 선 자세는 몸통 1 기준 머리 끝 ≈ 1.8 위 · 발목 ≈ 1.85 아래다.
const double _kUnitDiv = 4.2;
const double _kPelvisY = 0.48;

class CompareMoments extends StatelessWidget {
  const CompareMoments({
    super.key,
    required this.comparison,
    required this.selected,
    required this.onSelect,
  });

  final Comparison comparison;

  /// 지금 고른 순간 — 두 영상이 이 자리로 되감긴다.
  final MomentKey? selected;
  final ValueChanged<MomentKey> onSelect;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        for (final p in comparison.poses)
          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 3),
              child: _MomentCard(
                poses: p,
                kickingLeg: comparison.userMoments.kickingLeg,
                playerLeg: comparison.playerMoments.kickingLeg,
                selected: selected == p.key,
                onTap: () => onSelect(p.key),
              ),
            ),
          ),
      ],
    );
  }
}

class _MomentCard extends StatelessWidget {
  const _MomentCard({
    required this.poses,
    required this.kickingLeg,
    required this.playerLeg,
    required this.selected,
    required this.onTap,
  });

  final MomentPoses poses;
  final String kickingLeg;
  final String playerLeg;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final empty = poses.player == null && poses.user == null;
    return GestureDetector(
      onTap: empty ? null : onTap,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          AspectRatio(
            aspectRatio: 1,
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: const Color(0xFF16161A),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: selected ? kUserColor : const Color(0x22FFFFFF),
                  width: selected ? 1.6 : 1,
                ),
              ),
              child: empty
                  ? const Center(
                      child: Text(
                        '못 잼',
                        style: TextStyle(color: Color(0x66FFFFFF), fontSize: 11),
                      ),
                    )
                  : CustomPaint(
                      painter: _OverlapPainter(
                        player: poses.player,
                        user: poses.user,
                        playerLeg: playerLeg,
                        userLeg: kickingLeg,
                      ),
                    ),
            ),
          ),
          const SizedBox(height: 5),
          Text(
            poses.key.label,
            style: TextStyle(
              color: selected ? kUserColor : const Color(0xAAFFFFFF),
              fontSize: 11,
              fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

class _OverlapPainter extends CustomPainter {
  const _OverlapPainter({
    required this.player,
    required this.user,
    required this.playerLeg,
    required this.userLeg,
  });

  final Pose? player;
  final Pose? user;
  final String playerLeg;
  final String userLeg;

  @override
  void paint(Canvas canvas, Size size) {
    final unit = size.shortestSide / _kUnitDiv;
    final ox = size.width / 2;
    final oy = size.height * _kPelvisY;

    Offset? resolve(Pose pose, String name) {
      final p = pose[name];
      return p == null ? null : Offset(ox + p.x * unit, oy + p.y * unit);
    }

    /* 🔴 **선수는 굵게 아래, 나는 가늘게 그 위에** (2026-09-25 사용자 지적:
       「3관절 카드에는 선수꺼 관절 자체도 사라졌다」).

       까닭: 이 기능이 잘 될수록 **두 자세가 겹친다.** 그 회차는 무릎이
       116° 대 114° 였고, 같은 굵기로 그리니 나중에 그린 초록이 — 게다가
       어두운 테까지 둘러 — 밑의 마젠타를 **통째로 지웠다.**

       그래서 굵기를 갈라, 겹쳐도 **마젠타가 초록을 감싼 테처럼** 남는다.
       ⛔ 같은 굵기로 되돌리지 말 것 — 자세가 비슷할수록 안 보이게 된다. */
    if (player case final p?) {
      paintSkeleton(
        canvas,
        buildSkeletonShapes((n) => resolve(p, n), swingLeg: playerLeg),
        color: kPlayerColor,
        scale: 0.9,
        // 관절 고리는 **나만** 찍는다 — 둘 다면 점이 스물넷이라 판이 뭉개진다.
        joints: false,
      );
    }
    if (user case final u?) {
      paintSkeleton(
        canvas,
        buildSkeletonShapes((n) => resolve(u, n), swingLeg: userLeg),
        color: kUserColor,
        scale: 0.42,
        // 🔴 **테를 끄지 않으면 밑의 마젠타를 지운다**(위 머리말).
        halo: false,
      );
    }
  }

  @override
  bool shouldRepaint(_OverlapPainter old) =>
      old.player != player ||
      old.user != user ||
      old.playerLeg != playerLeg ||
      old.userLeg != userLeg;
}
