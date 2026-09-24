import 'dart:typed_data';

import '../../../core/mock/mock_db.dart';
import '../../../core/network/api_client.dart';
import 'clip_file.dart';
import 'models/my_video.dart';
import 'models/public_video.dart';
import 'models/video_report.dart';
import 'video_repository.dart';

/// 백엔드 없이 도는 영상 저장소.
///
/// 🔴 **일부러 느리고 일부러 실패한다**(`flutter/CLAUDE.md`). 즉시 성공하게
/// 고치면 로딩 화면과 오류 화면을 아예 안 만들게 되고, 진짜 서버에 붙는 날
/// 그 두 화면이 없다는 것을 알게 된다.
class MockVideoRepository implements VideoRepository {
  MockVideoRepository(this._db, {required this.userId});

  final MockDb _db;

  /// 지금 로그인한 사람 — 「내 영상」이 누구 것인지 가른다.
  final String userId;

  static const _delay = Duration(milliseconds: 300);

  /// 계약 테스트가 「분석이 끝난 영상」으로 쓰는 id(시드).
  static const analyzedId = 'v-analyzed';

  /// 계약 테스트가 「규격 반려」로 쓰는 id(시드).
  static const rejectedId = 'v-rejected';

  List<MyVideo> get _mine => _db.videosOf(userId);

  @override
  Future<List<MyVideo>> myVideos() async {
    await Future<void>.delayed(_delay);
    // 서버가 최근 것을 앞에 준다 — 그 성질을 여기서도 지킨다.
    final list = [..._mine]
      ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return list;
  }

  /* 🔴 **`_mine` 이 아니라 `_db.videos` 전체를 훑는다** — 공개 목록은 남의
     것까지다. 서버 질의(`is_public && kept`)를 그대로 흉내 낸다. */
  @override
  Future<List<PublicVideo>> publicVideos() async {
    await Future<void>.delayed(_delay);
    final rows = [
      for (final row in _db.videos)
        if (row.video.isPublic && row.video.kept) row,
    ]..sort((a, b) => b.video.createdAt.compareTo(a.video.createdAt));
    return [
      for (final row in rows)
        PublicVideo(
          id: row.video.id,
          sportCode: row.video.sportCode,
          durationMs: row.video.durationMs,
          createdAt: row.video.createdAt,
          title: row.video.title,
          description: row.video.description,
          uploaderNickname: _db.findUserById(row.userId)?.nickname,
          /* ⚠️ **크기는 안 준다** — [MyVideo] 가 안 들고 있다. 계약이
             「없으면 16:9」로 정했으므로 이것도 **있을 수 있는 상태**다. */
        ),
    ];
  }

  /* 🔴 **진짜 그림을 지어내지 않는다** — `playbackUrl` 과 같은 까닭이다.
     Mock 에 없는 자산을 가리키면 화면이 「깨진 그림」을 그리게 되고, 그건
     「아직 없음」과 다른 그림이라 목업으로 볼 값이 없다. */
  @override
  Future<Uint8List?> poster(String videoId) async {
    await Future<void>.delayed(_delay);
    return null;
  }

  @override
  Future<String?> playbackUrl(String videoId) async {
    await Future<void>.delayed(_delay);
    final v = _find(videoId);
    if (v == null) return null;
    /* 🔴 **진짜 주소를 지어내지 않는다.** Mock 에 없는 자산을 가리키면 화면이
       「받는 중」에서 영영 안 나오고, 그것이 코드 문제인지 목업 문제인지
       못 가른다. 에셋 경로 하나를 그대로 준다 — 없으면 플레이어가 빈 자리로
       남고 나머지는 정상으로 그려진다. */
    return 'asset:///assets/mock/clip.mp4';
  }

  @override
  Future<MyVideo> uploadClip({
    required ClipFile file,
    required ClipMeta meta,
    required String sportCode,
    bool analyze = false,
  }) async {
    // 세 단계(자리 받기 · S3 · 등록)를 흉내 내느라 한 박자 더 쉰다.
    await Future<void>.delayed(_delay * 2);

    /* 🔴 **형식·용량은 여기서도 막는다** — 계약이 `upload-url` 에서 422 로
       튕기는 자리다. Mock 이 받아 주면 그 오류 화면을 안 만들게 되고, 진짜
       서버에서 처음으로 막힌다. */
    final bad = checkClip(file);
    if (bad != null) {
      throw ApiException(bad, code: 'UNSUPPORTED_FORMAT', status: 422);
    }

    /* 🔴 **반려는 예외가 아니라 `201` 이다.** 세로가 너무 긴 클립 하나를
       반려로 흉내 내서, 화면이 「passed 로 분기한다」를 실제로 밟게 한다. */
    final tooLong = meta.durationMs > 60000;
    final saved = MyVideo(
      id: 'v-${DateTime.now().microsecondsSinceEpoch}',
      sportCode: sportCode,
      storageKey: 'videos/$userId/${file.name}',
      durationMs: meta.durationMs,
      createdAt: DateTime.now(),
      passed: !tooLong,
      rejectReason: tooLong ? '길이가 상한을 넘습니다 (상한 60초).' : null,
      // 반려된 클립은 `analyze` 와 무관하게 작업이 없다(계약 3-6절).
      analysisJobId: (!tooLong && analyze) ? 'job-${file.name.hashCode}' : null,
      analysisStatus: (!tooLong && analyze) ? 'queued' : null,
    );
    _db.videos.add((userId: userId, video: saved));
    return saved;
  }

  @override
  Future<MyVideo> patchVideo(
    String videoId, {
    bool? isPublic,
    String? title,
    String? description,
    bool? isFeatured,
  }) async {
    await Future<void>.delayed(_delay);
    final v = _find(videoId);
    if (v == null) {
      throw const ApiException('없는 클립입니다',
          code: 'VIDEO_NOT_FOUND', status: 404);
    }
    /* 🔴 **반려된 클립은 대표가 될 수 없다** — 서버가 422 `CANNOT_FEATURE` 로
       막는 자리다(계약). Mock 이 받아 주면 그 오류 문구를 안 만들게 된다. */
    if (isFeatured == true && !v.passed) {
      throw const ApiException('반려된 클립은 대표로 세울 수 없습니다',
          code: 'CANNOT_FEATURE', status: 422);
    }

    /* 🔴 **사람당 하나는 서버가 지킨다** — 여기서도 지켜야 화면이 옛 대표를
       따로 내리는 코드를 안 갖게 된다. 그 코드가 생기면 서버 규칙과 두 벌이
       되고, 어긋나면 대표가 둘로 보인다. */
    if (isFeatured == true) {
      for (var i = 0; i < _db.videos.length; i += 1) {
        final row = _db.videos[i];
        if (row.userId != userId || !row.video.isFeatured) continue;
        _db.videos[i] =
            (userId: row.userId, video: row.video.copyWith(isFeatured: false));
      }
    }

    final next = v.copyWith(
      isPublic: isPublic,
      isFeatured: isFeatured,
      // 🔴 공백만 보내면 지운다(계약: `PATCH /me/card` 의 `tagline` 과 같은 규칙).
      title: title,
      clearTitle: title != null && title.trim().isEmpty,
      description: description,
      clearDescription: description != null && description.trim().isEmpty,
    );
    _db.videos[_indexOf(videoId)] = (userId: userId, video: next);
    return next;
  }

  @override
  Future<void> deleteVideo(String videoId) async {
    await Future<void>.delayed(_delay);
    final at = _indexOf(videoId);
    if (at < 0) {
      throw const ApiException('없는 클립입니다',
          code: 'VIDEO_NOT_FOUND', status: 404);
    }
    _db.videos.removeAt(at);
  }

  @override
  Future<ReportResult> report(String videoId) async {
    await Future<void>.delayed(_delay);
    final v = _find(videoId);
    if (v == null) return const ReportMissing();
    // 반려된 클립·분석 안 한 클립은 **작업 자체가 없다** — 「아직」이 아니다.
    if (!v.analyzed) return const ReportMissing();
    switch (v.analysisStatus) {
      case 'failed':
        return const ReportFailed('품질 게이트 미달: 사람이 화면에서 너무 작습니다. 재촬영이 필요합니다.');
      case 'queued':
      case 'running':
        return const ReportNotReady();
    }
    return ReportReady(_db.reportFor(videoId));
  }

  MyVideo? _find(String videoId) {
    for (final v in _mine) {
      if (v.id == videoId) return v;
    }
    return null;
  }

  int _indexOf(String videoId) {
    for (var i = 0; i < _db.videos.length; i += 1) {
      final row = _db.videos[i];
      if (row.userId == userId && row.video.id == videoId) return i;
    }
    return -1;
  }
}
