/// 「선수와 비교하기」의 상태 — 고르기 → 읽기 → 겹쳐 보기.
///
/// 🔴 **앱은 관절을 뽑지 않는다.** 웹은 이 자리에서 브라우저 MoveNet 으로 두
/// 영상을 10fps 로 훑느라 **몇 초씩 걸리고 진행률까지 보여 준다**. 앱은 서버가
/// 이미 낸 값을 받으므로 **두 번의 GET 이 전부**다 — 그래서 진행률이 없다.
///
/// ⚠️ 웹의 **가짜 검색 지연**(`COMPARE_MS = 1600`, 「영상을 찾고 있는 중입니다」)도
/// 안 옮겼다. 연출이었고, 여기서는 진짜로 빨라서 기다리게 할 까닭이 없다.
library;

import 'dart:convert';

import 'package:flutter/services.dart' show rootBundle;
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/models/reference_player.dart';
import '../data/models/skeleton.dart';
import '../data/video_providers.dart';
import '../domain/motion/compare.dart';
import '../domain/motion/motion.dart';
import '../domain/motion/pose.dart';

sealed class CompareState {
  const CompareState();
}

/// 아직 안 눌렀다.
class CompareIdle extends CompareState {
  const CompareIdle();
}

/// 선수를 고르는 중.
class ComparePicking extends CompareState {
  const ComparePicking(this.players);
  final List<ReferencePlayer> players;
}

/// 관절을 받아오는 중 — 보통 눈 깜짝할 사이다.
class CompareLoading extends CompareState {
  const CompareLoading(this.player);
  final ReferencePlayer player;
}

class CompareShown extends CompareState {
  const CompareShown({
    required this.player,
    required this.comparison,
    required this.playerSkeleton,
    required this.userSkeleton,
    this.selected,
    this.mirrorOverride,
  });

  final ReferencePlayer player;
  final Comparison comparison;

  /// 🔴 **영상 위에 겹쳐 그리는 데 쓴다** — [comparison] 안의 좌표는 이미
  /// 골반 원점으로 옮겨져 있어 **영상에는 못 얹는다.** 둘은 다른 자리다.
  final Skeleton playerSkeleton;
  final Skeleton userSkeleton;

  /// 지금 고른 순간 — 두 영상이 이 자리에 멈춰 선다. `null` 이면 그냥 돈다.
  final MomentKey? selected;

  /// 사용자가 뒤집기를 직접 정했는가 — `null` 이면 자동 판별([shouldMirror]).
  final bool? mirrorOverride;

  CompareShown copyWith({
    Comparison? comparison,
    MomentKey? selected,
    bool clearSelected = false,
    bool? mirrorOverride,
  }) => CompareShown(
    player: player,
    playerSkeleton: playerSkeleton,
    userSkeleton: userSkeleton,
    comparison: comparison ?? this.comparison,
    selected: clearSelected ? null : (selected ?? this.selected),
    mirrorOverride: mirrorOverride ?? this.mirrorOverride,
  );
}

/// 비교를 못 했다 — 🔴 **까닭을 그대로 보여 준다.**
class CompareFailed extends CompareState {
  const CompareFailed(this.reason);
  final String reason;
}

class CompareController extends Notifier<CompareState> {
  @override
  CompareState build() => const CompareIdle();

  /// 비교하는 쪽 영상 — 🔴 **「분석이 달린 id」다.** 중복 업로드면 원본 id 라서
  /// 저장용 id 와 다르다(어제 여기서 한 번 데였다 — 리포트는 나오는데 관절만
  /// 영영 안 떴다).
  String? _videoId;

  /* 🔴 **비동기 답이 늦게 와서 새 상태를 덮는 것을 막는다.** 선수를 빠르게
     바꾸면 먼저 부른 쪽이 나중에 도착해 **고르지도 않은 선수의 비교**가 뜬다.
     `Notifier` 에는 `mounted` 가 없어 세대 번호로 가른다. */
  int _gen = 0;

  bool _stale(int gen) => gen != _gen;

  /* 🔴 **미리 받아 둔다** (2026-09-25 사용자 지적: 「선수 누르고 비교하는것도
     느려터졋는데?」). 리포트가 뜨자마자 뒤에서 세 가지를 당겨 둔다 — 선수
     목록 · 내 관절 · 선수마다의 관절. 누르는 순간에 받으면 **왕복을 세 번**
     기다린다(목록 0.6초 + 관절 둘 0.9초씩, 실서버 실측).

     ⚠️ 값이 크지 않다 — 관절 한 벌이 **111KB** 다. 미리 받아도 부담이 아니고,
     대신 누르는 순간이 **즉시**가 된다. */
  List<ReferencePlayer>? _players;
  SkeletonResult? _userSkeleton;
  final Map<String, SkeletonResult> _playerSkeletons = {};
  Future<void>? _prefetching;

  /// 리포트가 떴을 때 화면이 한 번 부른다. **여러 번 불러도 한 번만 받는다.**
  Future<void> prefetch(String analysisVideoId) {
    if (_videoId != analysisVideoId) {
      // 다른 영상이다 — 앞서 받아 둔 것은 그 영상 것이라 버린다.
      _videoId = analysisVideoId;
      _players = null;
      _userSkeleton = null;
      _playerSkeletons.clear();
      _prefetching = null;
    }
    return _prefetching ??= _prefetch(analysisVideoId);
  }

  Future<void> _prefetch(String videoId) async {
    final repo = ref.read(videoRepositoryProvider);
    try {
      final players = await repo.referencePlayers();
      _players = players;
      /* 🔴 **들고 다니는 선수는 서버에 안 묻는다** — 같은 값을 물어도
         0.67~11.5초로 들쭉날쭉하다([ReferencePlayer.skeletonAsset] 머리말). */
      final remote = [for (final p in players) if (p.skeletonAsset == null) p];
      final got = await Future.wait([
        repo.skeleton(videoId),
        for (final p in remote) repo.referencePlayerSkeleton(p.id),
      ]);
      _userSkeleton = got.first;
      for (var i = 0; i < remote.length; i += 1) {
        _playerSkeletons[remote[i].id] = got[i + 1];
      }
    } catch (_) {
      /* 🔴 **미리 받기가 실패해도 조용하다** — 누를 때 다시 받는다. 여기서
         화면을 오류로 바꾸면 **누르지도 않았는데** 빨간 글씨가 뜬다. */
      _prefetching = null;
    }
  }

  /// 단추를 눌렀다 — 선수 목록을 받아 고르기로 간다.
  Future<void> open(String analysisVideoId) async {
    _videoId = analysisVideoId;
    final gen = ++_gen;

    // 🔴 미리 받아 뒀으면 **기다리지 않는다** — 누른 순간 고르는 화면이 뜬다.
    final ready = _players;
    if (ready != null && ready.isNotEmpty) {
      state = ComparePicking(ready);
      return;
    }

    state = const CompareLoading(ReferencePlayer(id: '', name: ''));
    try {
      final players = await ref.read(videoRepositoryProvider).referencePlayers();
      _players = players;
      if (_stale(gen)) return;
      if (players.isEmpty) {
        state = const CompareFailed('견줄 선수가 아직 없습니다.');
        return;
      }
      state = ComparePicking(players);
    } catch (_) {
      if (_stale(gen)) return;
      state = const CompareFailed('선수 목록을 받지 못했습니다.');
    }
  }

  /// 선수를 골랐다 — 양쪽 관절을 받아 겹친다.
  Future<void> pick(ReferencePlayer player) async {
    final videoId = _videoId;
    if (videoId == null) return;
    final gen = ++_gen;
    state = CompareLoading(player);

    final repo = ref.read(videoRepositoryProvider);
    try {
      /* 🔴 **미리 받아 둔 것이 있으면 그대로 쓴다** — 없을 때만 부른다.
         둘을 함께 기다리는 것은 줄줄이 부르면 느린 서버에서 두 배로 느껴져서다. */
      // 🔴 **에셋이 있으면 그것이 먼저다** — 읽는 데 왕복이 없다.
      final cachedPlayer =
          _playerSkeletons[player.id] ?? await _bundled(player);
      final cachedUser = _userSkeleton;
      final SkeletonResult playerSkel;
      final SkeletonResult userSkel;
      if (cachedPlayer != null && cachedUser != null) {
        playerSkel = cachedPlayer;
        userSkel = cachedUser;
      } else {
        final got = await Future.wait([
          cachedPlayer != null
              ? Future.value(cachedPlayer)
              : repo.referencePlayerSkeleton(player.id),
          cachedUser != null
              ? Future.value(cachedUser)
              : repo.skeleton(videoId),
        ]);
        if (_stale(gen)) return;
        playerSkel = got[0];
        userSkel = got[1];
        _playerSkeletons[player.id] = playerSkel;
        _userSkeleton = userSkel;
      }
      if (playerSkel is! SkeletonReady) {
        state = CompareFailed(
          playerSkel is SkeletonUnavailable
              ? playerSkel.reason
              : '선수 관절을 아직 읽을 수 없습니다.',
        );
        return;
      }
      if (userSkel is! SkeletonReady) {
        state = CompareFailed(
          userSkel is SkeletonUnavailable
              ? userSkel.reason
              : '이 영상의 관절이 아직 준비되지 않았습니다.',
        );
        return;
      }

      final r = compareSkeletons(
        playerName: player.name,
        player: playerSkel.skeleton,
        user: userSkel.skeleton,
      );
      state = r.ok != null
          ? CompareShown(
              player: player,
              comparison: r.ok!,
              playerSkeleton: playerSkel.skeleton,
              userSkeleton: userSkel.skeleton,
            )
          : CompareFailed(r.failed!.reason);
    } catch (_) {
      if (_stale(gen)) return;
      state = const CompareFailed('관절을 받지 못했습니다.');
    }
  }

  /// 순간을 고른다 — 같은 것을 다시 누르면 **푼다**(영상이 다시 돈다).
  void select(MomentKey key) {
    final s = state;
    if (s is! CompareShown) return;
    state = s.selected == key
        ? s.copyWith(clearSelected: true)
        : s.copyWith(selected: key);
  }

  /// 좌우 뒤집기를 손으로 바꾼다 — 🔴 **자동 판별이 틀릴 수 있어서 둔다.**
  ///
  /// 뒤집으면 겹치는 좌표가 통째로 달라지므로 **다시 계산한다**(각도는 그대로다 —
  /// 각은 뒤집어도 안 바뀐다).
  void toggleMirror() {
    final s = state;
    if (s is! CompareShown) return;
    final next = !s.comparison.mirrored;
    final c = s.comparison;
    final flipped = Comparison(
      playerName: c.playerName,
      mirrored: next,
      // 선수 쪽만 다시 겹친다 — `compare.dart` 와 같은 규칙.
      poses: [
        for (final p in c.poses)
          MomentPoses(
            key: p.key,
            player: p.player == null
                ? null
                : _reflect(p.player!),
            user: p.user,
          ),
      ],
      metrics: c.metrics,
      text: c.text,
      playerMotion: c.playerMotion,
      playerMoments: c.playerMoments,
      userMotion: c.userMotion,
      userMoments: c.userMoments,
    );
    state = s.copyWith(comparison: flipped, mirrorOverride: next);
  }

  /// 앱에 들고 다니는 선수 관절 — 없으면 `null`(서버에 묻는다).
  ///
  /// 🔴 **서버 응답을 그대로 담아 둔 파일이라 파서가 같다.** 모양이 갈릴 여지가
  /// 없다. 못 읽으면 조용히 `null` — 그때는 서버가 답한다.
  Future<SkeletonResult?> _bundled(ReferencePlayer player) async {
    final path = player.skeletonAsset;
    if (path == null) return null;
    try {
      final body = jsonDecode(await rootBundle.loadString(path));
      final skeleton = Skeleton.fromJson(body as Map<String, dynamic>);
      final result = SkeletonReady(skeleton);
      _playerSkeletons[player.id] = result;
      return result;
    } catch (_) {
      return null;
    }
  }

  void close() {
    _gen += 1; // 날아오고 있는 답이 닫힌 화면을 되살리지 않게 한다.
    state = const CompareIdle();
  }

  /// 다른 선수를 고르러 돌아간다.
  Future<void> back() async {
    final videoId = _videoId;
    if (videoId != null) await open(videoId);
  }
}

/// 이미 정규화된 자세를 **가로만** 뒤집는다 — 원점이 골반이라 부호만 바꾸면 된다.
Pose _reflect(Pose pose) =>
    pose.mapPoints((p) => p == null ? null : Joint(-p.x, p.y, p.score));

final compareControllerProvider =
    NotifierProvider<CompareController, CompareState>(CompareController.new);
