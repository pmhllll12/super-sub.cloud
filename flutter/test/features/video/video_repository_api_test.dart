import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:super_sub/core/network/api_client.dart';
import 'package:super_sub/core/network/presigned_upload.dart';
import 'package:super_sub/features/auth/data/token_store.dart';
import 'package:super_sub/features/video/data/clip_file.dart';
import 'package:super_sub/features/video/data/models/video_report.dart';
import 'package:super_sub/features/video/data/video_repository_api.dart';

import '../../contract/video_repository_contract.dart';

/// 🔴 바이트로 준다 — 문자열 생성자는 charset 이 없으면 latin1 로 인코딩해서
/// 한글이 든 본문이 만들 때부터 터진다.
http.Response jsonRes(Object body, int status) =>
    http.Response.bytes(utf8.encode(jsonEncode(body)), status);

http.Response errRes(String code, int status, [String message = '없습니다']) =>
    jsonRes({
      'error': {'code': code, 'message': message},
    }, status);

Map<String, dynamic> videoRow(
  String id, {
  bool passed = true,
  String? rejectReason,
  String? jobId,
  String? status,
  bool isPublic = false,
  bool isFeatured = false,
  String? title,
  String? description,
  String createdAt = '2026-09-20T14:30:00Z',
}) =>
    {
      'id': id,
      'sport_code': 'football',
      'storage_key': 'videos/u-1/$id.mp4',
      'duration_ms': 10200,
      'created_at': createdAt,
      'passed': passed,
      'reject_reason': rejectReason,
      'analysis_job_id': jobId,
      'analysis_status': status,
      'is_public': isPublic,
      'is_featured': isFeatured,
      'title': title,
      'description': description,
      'kept': true,
    };

Map<String, dynamic> reportBody() => {
      'video_id': 'v-analyzed',
      'analyzed_at': '2026-09-20T12:00:00Z',
      'summary': '디딤발 무릎 굽히기가 강점입니다.',
      'provisional': false,
      'total_score': 71,
      'overall_grade': 'B',
      'breakdown': [
        {
          'criterion_id': 'plant_knee_flexion',
          'name': '디딤발 무릎 굽히기',
          'grade': 2,
          'title': '흔들리지 않는 축',
          'title_earned': true,
          'evidence': '안정적으로 놓였습니다.',
          'stat': 88.5,
          'skipped': false,
        },
        {
          'criterion_id': 'follow_through',
          'name': '팔로스루',
          'grade': 0,
          // 🔴 **0등급도 문구를 받는다** — `title_earned` 가 거짓이면 호칭이
          //    아니다. 이 줄이 「유무로 가르면 안 된다」를 실제로 밟게 한다.
          'title': '무너지는 축',
          'title_earned': false,
          'evidence': '팔로스루가 중간에 멈춥니다.',
          'stat': 41.0,
          'skipped': false,
        },
        {
          'criterion_id': 'plant_foot_position',
          'name': '디딤발 위치',
          'grade': null,
          'title': null,
          'title_earned': null,
          'evidence': null,
          'stat': null,
          'skipped': true,
        },
      ],
      'scenes': [
        {'metric_code': 'impact_frame', 'label': '임팩트 프레임', 'at_seconds': 2.07},
      ],
    };

/// 계약을 물릴 가짜 서버. 상태를 들고 있어 등재·수정·삭제가 실제로 반영된다.
ApiVideoRepository buildRepo() {
  final rows = <String, Map<String, dynamic>>{
    'v-analyzed': videoRow('v-analyzed',
        jobId: 'job-1',
        status: 'succeeded',
        createdAt: '2026-09-20T14:30:00Z'),
    'v-raw': videoRow('v-raw', createdAt: '2026-09-18T19:40:00Z'),
    'v-rejected': videoRow('v-rejected',
        passed: false,
        rejectReason: '길이가 상한을 넘습니다: 92초 (상한 60초)',
        createdAt: '2026-09-17T11:00:00Z'),
  };

  final client = MockClient((req) async {
    final path = req.url.path;
    final body = req.body.isEmpty
        ? <String, dynamic>{}
        : jsonDecode(req.body) as Map<String, dynamic>;

    if (path.endsWith('/videos/upload-url')) {
      return jsonRes({
        'storage_key': 'videos/u-1/new.mp4',
        'upload_url': 'https://storage.test/put',
        'expires_in': 900,
      }, 200);
    }
    /* 🔴 **`/videos` 검사보다 먼저 온다.** `/videos/public` 은 `/videos` 로
       끝나지 않아 아래 GET 분기에는 안 걸리지만, 더 아래의
       `path.contains('/videos/')`(재생·리포트 공용)에 걸려 엉뚱한 답을 준다. */
    if (path.endsWith('/videos/public')) {
      /* 🔴 **`rows`(내 목록)와 겹치지 않는 id 를 섞는다** — 계약이 「내 것이
         아닌 것도 온다」를 보므로, 내 것만 되돌리면 그 시험이 통과해선 안 된다.
         🔴 **`width`·`height` 를 안 준 줄도 하나 둔다** — 이 칸이 생기기 전
         등록분이고, 계약이 「그때는 16:9」로 정했다. */
      return jsonRes([
        {
          'id': 'v-other-1',
          'sport_code': 'football',
          'duration_ms': 12000,
          'created_at': '2026-09-21T08:00:00Z',
          'title': '코너킥 훈련',
          'description': null,
          'uploader_nickname': '이감독',
          'uploader_card_slug': 'coach-lee-1a2b',
          'width': 1920,
          'height': 1080,
        },
        {
          'id': 'v-other-2',
          'sport_code': 'football',
          'duration_ms': 9000,
          'created_at': '2026-09-16T17:20:00Z',
          'title': null,
          'description': null,
          'uploader_nickname': '박신입',
          'uploader_card_slug': null,
        },
      ], 200);
    }
    if (path.endsWith('/videos') && req.method == 'POST') {
      final id = 'v-new-${rows.length}';
      // 🔴 `analyze: false` 면 작업을 안 만든다(계약 3-6절).
      final analyze = body['analyze'] != false;
      rows[id] = videoRow(id,
          jobId: analyze ? 'job-new' : null,
          status: analyze ? 'queued' : null,
          createdAt: '2026-09-22T10:00:00Z');
      return jsonRes(rows[id]!, 201);
    }
    if (path.endsWith('/videos') && req.method == 'GET') {
      final list = rows.values.toList()
        ..sort((a, b) => (b['created_at'] as String)
            .compareTo(a['created_at'] as String));
      return jsonRes(list, 200);
    }
    if (path.endsWith('/playback-url')) {
      final id = path.split('/videos/').last.split('/').first;
      if (!rows.containsKey(Uri.decodeComponent(id))) {
        return errRes('VIDEO_NOT_FOUND', 404);
      }
      return jsonRes({'url': 'https://storage.test/get', 'expires_in': 900}, 200);
    }
    if (path.endsWith('/report')) {
      final id = Uri.decodeComponent(path.split('/videos/').last.split('/').first);
      final row = rows[id];
      if (row == null) return errRes('VIDEO_NOT_FOUND', 404);
      if (row['passed'] == false || row['analysis_job_id'] == null) {
        return errRes('VIDEO_NOT_FOUND', 404);
      }
      if (row['analysis_status'] != 'succeeded') {
        return errRes('REPORT_NOT_READY', 404);
      }
      return jsonRes(reportBody(), 200);
    }
    if (path.contains('/videos/')) {
      final id = Uri.decodeComponent(path.split('/videos/').last);
      final row = rows[id];
      if (row == null) return errRes('VIDEO_NOT_FOUND', 404);

      if (req.method == 'DELETE') {
        rows.remove(id);
        return http.Response('', 204);
      }
      if (req.method == 'PATCH') {
        // 🔴 반려된 클립은 대표가 될 수 없다.
        if (body['is_featured'] == true && row['passed'] == false) {
          return errRes('CANNOT_FEATURE', 422, '반려된 클립은 대표로 세울 수 없습니다');
        }
        // 🔴 **사람당 하나** — 세우면 다른 대표가 내려간다(서버가 지킨다).
        if (body['is_featured'] == true) {
          for (final r in rows.values) {
            r['is_featured'] = false;
          }
        }
        // 보낸 것만 바뀐다.
        for (final entry in body.entries) {
          row[entry.key] = entry.value;
        }
        return jsonRes(row, 200);
      }
    }
    return errRes('NOT_FOUND', 404);
  });

  return ApiVideoRepository(
    ApiClient(tokens: InMemoryTokenStore(), client: client),
    upload: PresignedUpload(
      client: MockClient((_) async => http.Response('', 200)),
    ),
  );
}

ClipFile clip({String name = '첫 골.mp4'}) => ClipFile(
      name: name,
      contentType: 'video/mp4',
      sizeBytes: 5,
      openRead: () => Stream.value(utf8.encode('bytes')),
    );

const meta = ClipMeta(durationMs: 10200, width: 1920, height: 1080);

void main() {
  runVideoRepositoryContract(
    'ApiVideoRepository',
    buildRepo,
    analyzedVideoId: 'v-analyzed',
    rejectedVideoId: 'v-rejected',
  );

  group('ApiVideoRepository 고유 규칙', () {
    /// 🔴 **세 단계의 순서가 이 경로의 전부다.** 자리를 받기 전에 올리거나,
    /// 올리기 전에 등록하면 서버는 `FILE_NOT_UPLOADED` 로 튕긴다.
    test('업로드는 자리받기 → S3 → 등록 순서로 간다', () async {
      final calls = <String>[];
      final api = ApiClient(
        tokens: InMemoryTokenStore(),
        client: MockClient((req) async {
          if (req.url.path.endsWith('/videos/upload-url')) {
            calls.add('spot');
            return jsonRes({
              'storage_key': 'videos/u-1/new.mp4',
              'upload_url': 'https://storage.test/put',
              'expires_in': 900,
            }, 200);
          }
          calls.add('register');
          return jsonRes(videoRow('v-new'), 201);
        }),
      );
      final repo = ApiVideoRepository(
        api,
        upload: PresignedUpload(
          client: MockClient((_) async {
            calls.add('s3');
            return http.Response('', 200);
          }),
        ),
      );

      await repo.uploadClip(file: clip(), meta: meta, sportCode: 'football');

      expect(calls, equals(['spot', 's3', 'register']));
    });

    /// 🔴 **저장 키를 뜯어보지 않고 그대로 넘긴다**(계약).
    test('받은 저장 키를 그대로 등록에 싣는다', () async {
      Map<String, dynamic>? registered;
      final api = ApiClient(
        tokens: InMemoryTokenStore(),
        client: MockClient((req) async {
          if (req.url.path.endsWith('/videos/upload-url')) {
            return jsonRes({
              'storage_key': 'videos/u-1/백성검-첫-골-20260922-1000-9a2e0c11.mp4',
              'upload_url': 'https://storage.test/put',
              'expires_in': 900,
            }, 200);
          }
          registered = jsonDecode(req.body) as Map<String, dynamic>;
          return jsonRes(videoRow('v-new'), 201);
        }),
      );
      final repo = ApiVideoRepository(
        api,
        upload: PresignedUpload(
          client: MockClient((_) async => http.Response('', 200)),
        ),
      );

      await repo.uploadClip(file: clip(), meta: meta, sportCode: 'football');

      expect(
        registered!['storage_key'],
        equals('videos/u-1/백성검-첫-골-20260922-1000-9a2e0c11.mp4'),
      );
    });

    /// 🔴 **생략하면 참이다** — 기록용 업로드일 때만 실어 보낸다.
    test('analyze 는 거짓일 때만 싣는다', () async {
      final bodies = <Map<String, dynamic>>[];
      ApiVideoRepository make() {
        final api = ApiClient(
          tokens: InMemoryTokenStore(),
          client: MockClient((req) async {
            if (req.url.path.endsWith('/videos/upload-url')) {
              return jsonRes({
                'storage_key': 'k',
                'upload_url': 'https://storage.test/put',
                'expires_in': 900,
              }, 200);
            }
            bodies.add(jsonDecode(req.body) as Map<String, dynamic>);
            return jsonRes(videoRow('v-new'), 201);
          }),
        );
        return ApiVideoRepository(
          api,
          upload: PresignedUpload(
            client: MockClient((_) async => http.Response('', 200)),
          ),
        );
      }

      await make().uploadClip(file: clip(), meta: meta, sportCode: 'football');
      await make().uploadClip(
          file: clip(), meta: meta, sportCode: 'football', analyze: true);

      expect(bodies[0]['analyze'], isFalse);
      expect(bodies[1].containsKey('analyze'), isFalse);
    });

    /// 🔴 **반려는 예외가 아니라 `201` 이다** — 상태 코드로 분기하면 사유가
    /// 화면까지 못 온다(계약 3-6절).
    test('반려(201 + passed:false)를 예외로 만들지 않는다', () async {
      final api = ApiClient(
        tokens: InMemoryTokenStore(),
        client: MockClient((req) async {
          if (req.url.path.endsWith('/videos/upload-url')) {
            return jsonRes({
              'storage_key': 'k',
              'upload_url': 'https://storage.test/put',
              'expires_in': 900,
            }, 200);
          }
          return jsonRes(
            videoRow('v-bad',
                passed: false, rejectReason: '해상도가 상한을 넘습니다'),
            201,
          );
        }),
      );
      final repo = ApiVideoRepository(
        api,
        upload: PresignedUpload(
          client: MockClient((_) async => http.Response('', 200)),
        ),
      );

      final saved =
          await repo.uploadClip(file: clip(), meta: meta, sportCode: 'football');

      expect(saved.passed, isFalse);
      expect(saved.rejectReason, equals('해상도가 상한을 넘습니다'));
    });

    /// 🔴 **404 를 세 뜻으로 가른다.** 이걸 뭉치면 화면이 「다시 확인」을
    /// 무한 반복시킨다(웹에서 사용자가 실제로 겪었다).
    test('REPORT_NOT_READY 는 「아직」이다', () async {
      final repo = ApiVideoRepository(
        ApiClient(
          tokens: InMemoryTokenStore(),
          client: MockClient((_) async => errRes('REPORT_NOT_READY', 404)),
        ),
      );

      expect(await repo.report('v-1'), isA<ReportNotReady>());
    });

    test('ANALYSIS_FAILED 는 「실패」이고 사유를 그대로 싣는다', () async {
      final repo = ApiVideoRepository(
        ApiClient(
          tokens: InMemoryTokenStore(),
          client: MockClient((_) async => errRes(
              'ANALYSIS_FAILED', 404, '품질 게이트 미달: 사람이 너무 작습니다. 재촬영이 필요합니다.')),
        ),
      );

      final got = await repo.report('v-1');

      expect(got, isA<ReportFailed>());
      expect((got as ReportFailed).reason, contains('재촬영'));
    });

    /// 🔴 로그인이 풀린 것이 「리포트가 없다」로 보이면 화면이 조용히 잘못된
    /// 상태에 머문다.
    test('401 은 리포트 없음으로 삼키지 않는다', () async {
      final repo = ApiVideoRepository(
        ApiClient(
          tokens: InMemoryTokenStore(),
          client: MockClient((_) async => errRes('UNAUTHORIZED', 401)),
        ),
      );

      await expectLater(repo.report('v-1'), throwsA(isA<ApiException>()));
    });

    test('401 은 재생 주소에서도 삼키지 않는다', () async {
      final repo = ApiVideoRepository(
        ApiClient(
          tokens: InMemoryTokenStore(),
          client: MockClient((_) async => errRes('UNAUTHORIZED', 401)),
        ),
      );

      await expectLater(repo.playbackUrl('v-1'), throwsA(isA<ApiException>()));
    });

    /// 저장소가 안 붙은 배포에서 목록 전체가 죽는 것보다 플레이어 자리만
    /// 비는 편이 맞다(웹과 같은 판단).
    test('STORAGE_NOT_CONFIGURED 면 주소가 null 이다', () async {
      final repo = ApiVideoRepository(
        ApiClient(
          tokens: InMemoryTokenStore(),
          client: MockClient(
              (_) async => errRes('STORAGE_NOT_CONFIGURED', 503)),
        ),
      );

      expect(await repo.playbackUrl('v-1'), isNull);
    });

    /// 🔴 `title` 은 **모든 등급에 있다** — `title_earned` 로 가른다(CCC 47).
    /// 유무로 선을 그으면 못한 항목에 호칭을 단다.
    test('호칭은 title_earned 가 참인 것만 그린다', () async {
      final got = await buildRepo().report('v-analyzed') as ReportReady;

      final earned = got.report.points.where((p) => p.title != null).toList();
      expect(earned, hasLength(1));
      expect(earned.first.title, equals('흔들리지 않는 축'));
      // 🔴 호칭을 못 받아도 **문장은 남는다.**
      expect(
        got.report.points.map((p) => p.evidence),
        contains('팔로스루가 중간에 멈춥니다.'),
      );
    });

    /// 🔴 `skipped` 항목을 0 으로 그리면 「그 항목을 못했다」로 잘못 읽힌다.
    test('skipped 항목은 축에서도 문장에서도 빠진다', () async {
      final got = await buildRepo().report('v-analyzed') as ReportReady;

      expect(got.report.radar.map((a) => a.name), isNot(contains('디딤발 위치')));
      expect(got.report.radar, hasLength(2));
    });

    test('영상 id 를 URL 에 안전하게 싣는다', () async {
      String? seen;
      final repo = ApiVideoRepository(
        ApiClient(
          tokens: InMemoryTokenStore(),
          client: MockClient((req) async {
            seen = req.url.path;
            return errRes('VIDEO_NOT_FOUND', 404);
          }),
        ),
      );

      await repo.playbackUrl('a/b');

      expect(seen, contains('a%2Fb'));
    });
  });
}
