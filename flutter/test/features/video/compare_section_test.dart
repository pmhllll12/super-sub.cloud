/// 「선수와 비교하기」 절의 화면 시험.
///
/// 🔴 **영상은 안 띄운다.** `video_player` 는 위젯 시험에서 플랫폼 채널이 없어
/// 초기화가 영영 안 끝난다 — 여기서는 **흰 판 쪽**(단추 · 고르기 · 문장 · 실패
/// 문구)만 본다. 좌우로 갈린 영상 칸은 실기기에서 눈으로 확인한다.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/video/data/models/reference_player.dart';
import 'package:super_sub/features/video/data/models/skeleton.dart';
import 'package:super_sub/features/video/data/video_providers.dart';
import 'package:super_sub/features/video/data/video_repository.dart';
import 'package:super_sub/features/video/domain/motion/compare.dart';
import 'package:super_sub/features/video/domain/motion/motion.dart';
import 'package:super_sub/features/video/presentation/compare_controller.dart';
import 'package:super_sub/features/video/presentation/widgets/compare_moments.dart';

import 'motion_test.dart' show kNames, kickMotion;

Skeleton skeletonOf({int direction = 1, double lean = 0}) {
  final m = kickMotion(lean: lean);
  return Skeleton(
    known: true,
    fps: 15,
    frameWidth: 1280,
    frameHeight: 720,
    swingLeg: 'right',
    direction: direction,
    keypointNames: kNames,
    joints: [
      for (final f in m.frames)
        f == null ? null : [for (final p in f.points) [p!.x, p.y, p.score]],
    ],
    moments: const {'before': 14, 'impact': 15, 'after': 30},
  );
}

Comparison buildComparison() => compareSkeletons(
  playerName: '에스테반 로벨리',
  player: skeletonOf(),
  user: skeletonOf(lean: 0.05),
).ok!;

void main() {
  group('세 순간 카드', () {
    testWidgets('순간 이름 셋을 그리고, 누르면 그 순간을 고른다', (tester) async {
      final cmp = buildComparison();
      MomentKey? picked;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: CompareMoments(
              comparison: cmp,
              selected: null,
              onSelect: (k) => picked = k,
            ),
          ),
        ),
      );

      expect(find.text('백스윙'), findsOneWidget);
      expect(find.text('접촉'), findsOneWidget);
      expect(find.text('접촉 후'), findsOneWidget);

      await tester.tap(find.text('접촉'));
      expect(picked, MomentKey.impact);
    });

    /// 🔴 **못 잰 순간은 누를 수 없어야 한다** — 누르면 두 영상이 엉뚱한 자리로
    /// 간다(그 순간의 자세가 없는데 위치만 옮겨진다).
    testWidgets('두 쪽 다 없는 순간은 「못 잼」으로 두고 안 고른다', (tester) async {
      final cmp = buildComparison();
      var tapped = 0;
      final holed = Comparison(
        playerName: cmp.playerName,
        mirrored: cmp.mirrored,
        poses: [
          for (final p in cmp.poses)
            p.key == MomentKey.after ? MomentPoses(key: p.key) : p,
        ],
        metrics: cmp.metrics,
        text: cmp.text,
        playerMotion: cmp.playerMotion,
        playerMoments: cmp.playerMoments,
        userMotion: cmp.userMotion,
        userMoments: cmp.userMoments,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: CompareMoments(
              comparison: holed,
              selected: null,
              onSelect: (_) => tapped += 1,
            ),
          ),
        ),
      );

      expect(find.text('못 잼'), findsOneWidget);
      await tester.tap(find.text('접촉 후'));
      expect(tapped, 0);
    });
  });

  group('비교 컨트롤러', () {
    /// 선수 관절만 주는 아주 작은 대역 — 계약 시험이 아니라 **흐름**을 본다.
    ProviderContainer containerWith(_FakeRepo repo) => ProviderContainer(
      overrides: [videoRepositoryProvider.overrideWithValue(repo)],
    );

    test('선수를 고르면 겹친 결과가 나온다', () async {
      final c = containerWith(_FakeRepo());
      addTearDown(c.dispose);
      final n = c.read(compareControllerProvider.notifier);

      await n.open('v-1');
      expect(c.read(compareControllerProvider), isA<ComparePicking>());

      await n.pick(const ReferencePlayer(id: 'rovelli', name: '에스테반 로벨리'));
      final shown = c.read(compareControllerProvider);
      expect(shown, isA<CompareShown>());
      expect((shown as CompareShown).comparison.text.summary, isNotEmpty);
    });

    /// 🔴 **같은 것을 다시 누르면 푼다** — 안 풀면 영상이 멈춘 채로 남아
    /// 「고장난 것」처럼 보인다.
    test('고른 순간을 다시 누르면 선택이 풀린다', () async {
      final c = containerWith(_FakeRepo());
      addTearDown(c.dispose);
      final n = c.read(compareControllerProvider.notifier);
      await n.open('v-1');
      await n.pick(const ReferencePlayer(id: 'rovelli', name: 'p'));

      n.select(MomentKey.impact);
      expect(
        (c.read(compareControllerProvider) as CompareShown).selected,
        MomentKey.impact,
      );

      n.select(MomentKey.impact);
      expect(
        (c.read(compareControllerProvider) as CompareShown).selected,
        isNull,
      );
    });

    /// 🔴 **관절이 없는 영상은 까닭을 말한다** — 분석을 안 건 영상이 대부분이라,
    /// 그냥 「실패」라고만 하면 같은 영상으로 계속 눌러 본다.
    test('내 영상에 관절이 없으면 까닭이 뜬다', () async {
      final c = containerWith(_FakeRepo(userKnown: false));
      addTearDown(c.dispose);
      final n = c.read(compareControllerProvider.notifier);
      await n.open('v-1');
      await n.pick(const ReferencePlayer(id: 'rovelli', name: 'p'));

      final s = c.read(compareControllerProvider);
      expect(s, isA<CompareFailed>());
      expect((s as CompareFailed).reason, contains('분석이 끝난 영상'));
    });

    test('뒤집기는 선수 쪽 가로만 바꾼다', () async {
      final c = containerWith(_FakeRepo());
      addTearDown(c.dispose);
      final n = c.read(compareControllerProvider.notifier);
      await n.open('v-1');
      await n.pick(const ReferencePlayer(id: 'rovelli', name: 'p'));

      final before = c.read(compareControllerProvider) as CompareShown;
      final ankleBefore =
          before.comparison.poses[1].player!['right_ankle']!.x;
      final userBefore = before.comparison.poses[1].user!['right_ankle']!.x;

      n.toggleMirror();
      final after = c.read(compareControllerProvider) as CompareShown;

      expect(after.comparison.mirrored, !before.comparison.mirrored);
      expect(
        after.comparison.poses[1].player!['right_ankle']!.x,
        closeTo(-ankleBefore, 1e-9),
      );
      // 🔴 **내 쪽은 그대로다** — 둘 다 뒤집으면 아무것도 안 뒤집은 것과 같다.
      expect(
        after.comparison.poses[1].user!['right_ankle']!.x,
        closeTo(userBefore, 1e-9),
      );
    });
  });
}

/// 비교 흐름에 필요한 두 메서드만 답하는 대역.
class _FakeRepo implements VideoRepository {
  _FakeRepo({this.userKnown = true});

  final bool userKnown;

  @override
  Future<List<ReferencePlayer>> referencePlayers() async => const [
    ReferencePlayer(id: 'rovelli', name: '에스테반 로벨리'),
    ReferencePlayer(id: 'castanheira', name: '티아구 카스탄헤이라'),
  ];

  @override
  Future<SkeletonResult> referencePlayerSkeleton(String playerId) async =>
      SkeletonReady(skeletonOf());

  @override
  Future<SkeletonResult> skeleton(String videoId) async => userKnown
      ? SkeletonReady(skeletonOf(lean: 0.05))
      : const SkeletonReady(Skeleton(known: false, why: '옛 리포트입니다.'));

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('비교 시험이 안 쓰는 자리: ${invocation.memberName}');
}
