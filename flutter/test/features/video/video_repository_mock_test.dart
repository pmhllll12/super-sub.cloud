import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/video/data/clip_file.dart';
import 'package:super_sub/features/video/data/models/video_report.dart';
import 'package:super_sub/features/video/data/video_repository_mock.dart';

import '../../contract/video_repository_contract.dart';

MockVideoRepository buildRepo() =>
    MockVideoRepository(MockDb(), userId: MockDb.playerId);

ClipFile clip({
  String name = '첫 골.mp4',
  String contentType = 'video/mp4',
  int sizeBytes = 1024,
}) =>
    ClipFile(
      name: name,
      contentType: contentType,
      sizeBytes: sizeBytes,
      openRead: () => Stream.value(List<int>.filled(1, 7)),
    );

void main() {
  runVideoRepositoryContract(
    'MockVideoRepository',
    buildRepo,
    analyzedVideoId: MockVideoRepository.analyzedId,
    rejectedVideoId: MockVideoRepository.rejectedId,
  );

  group('MockVideoRepository 고유 규칙', () {
    /// 🔴 **Mock 은 일부러 느리다**(`flutter/CLAUDE.md`). 즉시 성공하게 고치면
    /// 로딩 화면을 안 만들게 되고, API 를 붙이는 날 화면을 다시 짠다.
    /// 계약이 아니라 여기 두는 이유 — API 구현체는 이 조건을 못 지킨다.
    test('일부러 느리다', () async {
      final started = DateTime.now();

      await buildRepo().myVideos();

      expect(
        DateTime.now().difference(started).inMilliseconds,
        greaterThanOrEqualTo(200),
      );
    });

    test('신규 가입자는 영상이 하나도 없다 — 빈 상태를 반드시 밟게 한다', () async {
      final repo = MockVideoRepository(MockDb(), userId: MockDb.newbieId);

      expect(await repo.myVideos(), isEmpty);
    });

    /// 🔴 Mock 이 받아 주면 그 오류 화면을 안 만들게 되고, 진짜 서버에서
    /// 처음으로 막힌다.
    test('받지 않는 형식은 올리기 전에 막는다', () async {
      await expectLater(
        buildRepo().uploadClip(
          file: clip(contentType: 'video/x-msvideo'),
          meta: const ClipMeta(durationMs: 5000, width: 1920, height: 1080),
          sportCode: 'football',
        ),
        throwsA(anything),
      );
    });

    test('용량 상한을 넘으면 올리기 전에 막는다', () async {
      await expectLater(
        buildRepo().uploadClip(
          file: clip(sizeBytes: kClipMaxBytes + 1),
          meta: const ClipMeta(durationMs: 5000, width: 1920, height: 1080),
          sportCode: 'football',
        ),
        throwsA(anything),
      );
    });

    /// 🔴 **반려는 예외가 아니라 정상 응답이다** — 상태 코드가 아니라
    /// `passed` 로 분기한다(계약 3-6절). 예외로 만들면 사유가 화면까지 못 온다.
    test('길이가 넘치면 예외가 아니라 passed: false 로 온다', () async {
      final saved = await buildRepo().uploadClip(
        file: clip(),
        meta: const ClipMeta(durationMs: 92000, width: 1920, height: 1080),
        sportCode: 'football',
      );

      expect(saved.passed, isFalse);
      expect(saved.rejectReason, isNotNull);
      expect(saved.analysisJobId, isNull);
    });

    test('analyze: true 면 작업이 생긴다', () async {
      final saved = await buildRepo().uploadClip(
        file: clip(),
        meta: const ClipMeta(durationMs: 10000, width: 1920, height: 1080),
        sportCode: 'football',
        analyze: true,
      );

      expect(saved.analyzed, isTrue);
      expect(saved.analysisStatus, equals('queued'));
    });

    /// 🔴 분석 중인 클립에 「없다」를 보이면 결과가 없는 것처럼 읽힌다.
    test('분석 중인 클립의 리포트는 not-ready 다', () async {
      expect(await buildRepo().report('v-running'), isA<ReportNotReady>());
    });

    /// 🔴 반려·분석 안 함은 **작업 자체가 없다** — 「아직」으로 답하면 화면이
    /// 영영 오지 않을 결과를 기다리게 한다.
    test('분석을 안 건 클립의 리포트는 「아직」이 아니라 「없다」다', () async {
      expect(await buildRepo().report('v-raw'), isA<ReportMissing>());
    });
  });
}
