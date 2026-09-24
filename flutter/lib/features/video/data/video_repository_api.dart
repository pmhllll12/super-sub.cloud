import 'dart:typed_data';

import '../../../core/network/api_client.dart';
import '../../../core/network/presigned_upload.dart';
import 'clip_file.dart';
import 'models/my_video.dart';
import 'models/public_video.dart';
import 'models/skeleton.dart';
import 'models/video_report.dart';
import 'video_repository.dart';

/// `fastapi/` 백엔드에 붙는 실제 구현. 계약은 `fastapi/docs/api-contract.md`
/// 의 3-6절(클립 업로드)과 3-1절(리포트 읽기).
class ApiVideoRepository implements VideoRepository {
  ApiVideoRepository(this._api, {PresignedUpload? upload})
      : _upload = upload ?? PresignedUpload();

  final ApiClient _api;

  /// 🔴 **저장소 PUT 은 `ApiClient` 를 안 지난다** — 토큰을 실으면 서명이
  /// 깨지고 응답이 JSON 이 아니다(`presigned_upload.dart` 머리말).
  final PresignedUpload _upload;

  @override
  Future<List<MyVideo>> myVideos() async {
    final rows = await _api.getList('/videos');
    return [for (final r in rows) MyVideo.fromJson(r)];
  }

  @override
  Future<List<PublicVideo>> publicVideos() async {
    final rows = await _api.getList('/videos/public');
    return [for (final r in rows) PublicVideo.fromJson(r)];
  }

  @override
  Future<Uint8List?> poster(String videoId) async {
    try {
      return await _api.getBytes(
        '/videos/${Uri.encodeComponent(videoId)}/poster',
      );
    } on ApiException catch (e) {
      /* 🔴 **404 둘을 같게 삼킨다** — `VIDEO_NOT_FOUND`(없거나 비공개 남의 것)와
         `POSTER_NOT_AVAILABLE`(장면을 못 떴다). 화면이 할 일이 같다: 자리표시.
         🔴 **503 도 삼킨다** — 저장소가 안 붙은 배포다(`playbackUrl` 과 같은
         판단). 401·500 은 그대로 올린다. */
      if (e.status == 404 || e.code == 'STORAGE_NOT_CONFIGURED') return null;
      rethrow;
    }
  }

  @override
  Future<String?> playbackUrl(String videoId) async {
    try {
      final body = await _api.get('/videos/${Uri.encodeComponent(videoId)}/playback-url');
      return body['url'] as String?;
    } on ApiException catch (e) {
      /* 🔴 **404 만** null 이다 — 계약이 「없는 클립」과 「비공개 남의 클립」을
         같게 답한다. 🔴 **503 `STORAGE_NOT_CONFIGURED` 도 null 로 삼킨다**:
         저장소가 안 붙은 배포에서 목록 전체가 오류로 죽는 것보다, 플레이어
         자리만 비고 나머지가 그려지는 편이 맞다(웹이 미결 paik 12번에서
         내린 판단과 같다). 401·500 은 그대로 올린다. */
      if (e.status == 404 || e.code == 'STORAGE_NOT_CONFIGURED') return null;
      rethrow;
    }
  }

  @override
  Future<MyVideo> uploadClip({
    required ClipFile file,
    required ClipMeta meta,
    required String sportCode,
    bool analyze = false,
  }) async {
    // (1) 올릴 자리를 받는다.
    final spot = await _api.post('/videos/upload-url', {
      'content_type': file.contentType,
      'size_bytes': file.sizeBytes,
      // 저장 키를 사람이 알아보게 짓는 데 쓴다 — 서버가 슬러그화한다.
      'filename': file.name,
    });
    final storageKey = spot['storage_key'] as String;

    // (2) S3 에 직접. 원본이 앱 서버를 안 지난다(PER-002).
    await _upload.put(
      url: Uri.parse(spot['upload_url'] as String),
      openRead: file.openRead,
      contentLength: file.sizeBytes,
      contentType: file.contentType,
    );

    // (3) 등록하고 서버가 규격을 검사한다.
    /* 🔴 **반려는 `201` 이라 예외가 아니다** — `_api.post` 는 2xx 를 그대로
       돌려주므로 여기서 할 일이 없다. 부르는 쪽이 `passed` 로 분기한다. */
    final saved = await _api.post('/videos', {
      'sport_code': sportCode,
      // 🔴 **뜯어보지 않고 그대로 넘긴다**(계약).
      'storage_key': storageKey,
      'filename': file.name,
      'duration_ms': meta.durationMs,
      'width': meta.width,
      'height': meta.height,
      // 🔴 **생략하면 참이다.** 기록용 업로드일 때만 실어 보낸다.
      if (!analyze) 'analyze': false,
    });
    return MyVideo.fromJson(saved);
  }

  @override
  Future<MyVideo> patchVideo(
    String videoId, {
    bool? isPublic,
    String? title,
    String? description,
    bool? isFeatured,
  }) async {
    /* 🔴 **보낸 것만 바뀐다** — 안 보낸 것은 그대로다. `null` 을 보내는 것과
       안 보내는 것이 다른 뜻인 곳은 `title`·`description` 뿐인데(공백이면
       지운다), 그 판단은 부르는 쪽이 하고 여기서는 받은 것을 그대로 싣는다. */
    final body = <String, dynamic>{
      'is_public': ?isPublic,
      'is_featured': ?isFeatured,
      'title': ?title,
      'description': ?description,
    };
    final row = await _api.patch(
      '/videos/${Uri.encodeComponent(videoId)}',
      body,
    );
    return MyVideo.fromJson(row);
  }

  @override
  Future<void> deleteVideo(String videoId) =>
      _api.delete('/videos/${Uri.encodeComponent(videoId)}');

  @override
  Future<MyVideo> keepVideo(String videoId) async {
    /* 🔴 **본문이 없다** — 계약이 경로만 받는다. 응답은 `GET /videos` 한 줄과
       같은 모양이고, `storage_key` 가 **새 자리로 바뀌어** 온다. */
    final saved = await _api.post(
      '/videos/${Uri.encodeComponent(videoId)}/keep',
      const {},
    );
    return MyVideo.fromJson(saved);
  }

  @override
  Future<SkeletonResult> skeleton(String videoId) async {
    try {
      final body =
          await _api.get('/videos/${Uri.encodeComponent(videoId)}/skeleton');
      return SkeletonReady(Skeleton.fromJson(body));
    } on ApiException catch (e) {
      // 🔴 리포트와 같은 셋이다(계약 3-14절).
      switch (e.code) {
        case 'REPORT_NOT_READY':
          return const SkeletonNotReady();
        case 'ANALYSIS_FAILED':
          return SkeletonUnavailable(e.message);
        case 'VIDEO_NOT_FOUND':
          return const SkeletonUnavailable('그 영상을 찾을 수 없습니다.');
      }
      // 🔴 401 을 「관절 없음」으로 만들지 않는다 — `report` 와 같은 까닭.
      if (e.status == 401 || e.status == 403) rethrow;
      return SkeletonUnavailable(e.message);
    }
  }

  @override
  Future<ReportResult> report(String videoId) async {
    try {
      final body = await _api.get('/videos/${Uri.encodeComponent(videoId)}/report');
      return ReportReady(VideoReport.fromJson(body));
    } on ApiException catch (e) {
      /* 🔴 **404 를 세 뜻으로 가른다.** 뭉치면 분석 중인 클립이 결과 없는
         클립처럼, 또는 영영 안 될 실패가 곧 될 것처럼 보인다 — 웹에서
         사용자가 「다시 확인」을 무한 반복하는 것을 실제로 겪었다. */
      switch (e.code) {
        case 'REPORT_NOT_READY':
          return const ReportNotReady();
        case 'ANALYSIS_FAILED':
          // 🔴 `message` 가 곧 실패 사유다 — 기본 문구로 덮지 않는다.
          return ReportFailed(e.message);
        case 'VIDEO_NOT_FOUND':
          return const ReportMissing();
      }
      /* 🔴 **401 을 「리포트가 없다」로 만들지 않는다.** 로그인이 풀린 것이
         결과 없음으로 보이면 화면이 조용히 잘못된 상태에 머문다. */
      if (e.status == 401 || e.status == 403) rethrow;
      return ReportError(e.message);
    }
  }
}
