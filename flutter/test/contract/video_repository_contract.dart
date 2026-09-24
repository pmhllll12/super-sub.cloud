import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/video/data/clip_file.dart';
import 'package:super_sub/features/video/data/video_repository.dart';
import 'package:super_sub/features/video/data/models/video_report.dart';

/// VideoRepository 의 모든 구현체가 지켜야 하는 계약.
///
/// 🔴 **여기에는 프로토콜의 성질만 둔다.** Mock 에만 있는 의무(지연 하한)는
/// 구현체별 테스트 파일로 내린다 — 계약에 섞으면 API 구현체가 통과할 수 없는
/// 조건이 된다(`flutter/CLAUDE.md`).
///
/// 같은 파일을 Mock 과 API 에 **둘 다** 물려 돌린다.
///
/// [build] 는 매 테스트마다 깨끗한 구현체를 만든다.
/// [analyzedVideoId] 는 분석이 끝나 **리포트가 있는** 영상.
/// [rejectedVideoId] 는 **규격에 반려된** 영상(대표로 못 세운다).
void runVideoRepositoryContract(
  String name,
  VideoRepository Function() build, {
  required String analyzedVideoId,
  required String rejectedVideoId,
}) {
  group('$name — VideoRepository 계약', () {
    late VideoRepository repo;

    setUp(() => repo = build());

    ClipFile sampleClip({
      String name = '첫 골.mp4',
      String contentType = 'video/mp4',
      int sizeBytes = 1024,
    }) =>
        ClipFile(
          name: name,
          contentType: contentType,
          sizeBytes: sizeBytes,
          openRead: () => Stream.value(List<int>.filled(sizeBytes, 7)),
        );

    const meta = ClipMeta(durationMs: 10200, width: 1920, height: 1080);

    /* 🔴 **공개 목록은 「내 것」이 아니다** — 남이 공개한 것까지 온다
       (계약 `GET /videos/public`). 구현체가 이걸 `myVideos()` 로 때우면
       다른 사람 영상이 홈에서 통째로 빠지므로, 성질로 못 박는다. */
    group('공개 목록', () {
      test('최근 것이 앞에 온다', () async {
        final videos = await repo.publicVideos();

        expect(videos.length, greaterThan(1));
        for (var i = 1; i < videos.length; i += 1) {
          expect(
            videos[i - 1].createdAt.isAfter(videos[i].createdAt) ||
                videos[i - 1].createdAt.isAtSameMomentAs(videos[i].createdAt),
            isTrue,
            reason: '$i 번째가 앞의 것보다 최근이다',
          );
        }
      });

      /* 🔴 **「내 것이 아닌 것이 있다」로 잰다.** 「올린 사람이 여럿」으로
         재면 구현체가 아니라 **시드의 모양**을 시험하게 되고, 목업 사용자
         구성을 바꿀 때마다 계약이 흔들린다. 지키려는 성질은 이것 하나다 —
         `myVideos()` 로 때우면 여기서 걸린다. */
      test('내 것이 아닌 것도 온다', () async {
        final mine = (await repo.myVideos()).map((v) => v.id).toSet();
        final public = await repo.publicVideos();

        expect(public, isNotEmpty);
        expect(
          public.any((v) => !mine.contains(v.id)),
          isTrue,
          reason: '공개 목록이 내 것만 담고 있다',
        );
      });

      /* 🔴 **크기를 안 준 등록분이 있다** — 이 칸이 생기기 전 것들이다.
         계약이 「그때는 16:9 로 본다」로 정했고, 화면이 칸을 미리 잡는 데
         쓰므로 **`null` 이 그대로 새어 나가면 안 된다.** */
      test('크기를 모르면 16:9 로 답한다', () async {
        final videos = await repo.publicVideos();
        for (final v in videos) {
          expect(v.aspectRatio, greaterThan(0));
          if (v.width == null || v.height == null) {
            expect(v.aspectRatio, closeTo(16 / 9, 0.001));
          }
        }
      });
    });

    /* 🔴 **없는 영상이면 `null` 이다 — 예외가 아니다.** 못 뜨는 영상(형식·길이)도,
       서버에 `ffmpeg` 이 없는 배포도 같은 자리로 떨어진다. 화면이 할 일은 셋 다
       같다(자리표시를 그린다) — 예외로 만들면 그 셋이 홈을 통째로 오류로 만든다. */
    test('없는 영상의 장면은 null 이다', () async {
      expect(await repo.poster('없는-영상'), isNull);
    });

    test('목록은 최근 것이 앞에 온다', () async {
      final videos = await repo.myVideos();

      expect(videos.length, greaterThan(1));
      for (var i = 1; i < videos.length; i += 1) {
        expect(
          videos[i - 1].createdAt.isBefore(videos[i].createdAt),
          isFalse,
          reason: '${videos[i - 1].id} 가 ${videos[i].id} 보다 뒤에 있다',
        );
      }
    });

    /// 🔴 **갈래를 가르는 것은 `analysis_job_id` 다.** `analysis_status` 로
    /// 가르면 분석을 걸었지만 대기 중인 클립이 「그냥 올린 것」으로 새어 나간다.
    test('반려된 클립은 분석 작업이 없다 — 업로드 갈래에 남는다', () async {
      final rejected = (await repo.myVideos())
          .firstWhere((v) => v.id == rejectedVideoId);

      expect(rejected.passed, isFalse);
      expect(rejected.rejectReason, isNotNull);
      expect(rejected.analysisJobId, isNull);
      expect(rejected.analyzed, isFalse);
    });

    test('없는 영상의 재생 주소는 예외가 아니라 null 이다', () async {
      expect(await repo.playbackUrl('no-such-video'), isNull);
    });

    /// 🔴 **보낸 뜻이 아니라 돌아온 응답을 믿는다** — 그래서 계약은
    /// 「`analyze: false` 로 올리면 작업이 안 생긴다」를 응답으로 잰다.
    test('analyze: false 로 올리면 분석 작업이 안 생기고 목록 맨 앞에 온다', () async {
      final saved = await repo.uploadClip(
        file: sampleClip(),
        meta: meta,
        sportCode: 'football',
      );

      expect(saved.analysisJobId, isNull);
      expect(saved.analyzed, isFalse);
      expect((await repo.myVideos()).first.id, equals(saved.id));
    });

    test('보낸 것만 바뀐다 — 제목만 고치면 공개 여부는 그대로', () async {
      final before = (await repo.myVideos()).first;

      final after = await repo.patchVideo(before.id, title: '우리 팀 첫 골');

      expect(after.title, equals('우리 팀 첫 골'));
      expect(after.isPublic, equals(before.isPublic));
      expect(after.isFeatured, equals(before.isFeatured));
    });

    test('공개와 제목을 한 번에 보낸다', () async {
      final target = (await repo.myVideos()).first;

      final after = await repo.patchVideo(
        target.id,
        isPublic: true,
        title: '공개할 장면',
        description: '왼발 감아차기',
      );

      expect(after.isPublic, isTrue);
      expect(after.title, equals('공개할 장면'));
      expect(after.description, equals('왼발 감아차기'));
    });

    /// 🔴 **사람당 하나** — 옛 대표를 화면이 따로 내리지 않는다. 그 규칙을
    /// 클라이언트가 흉내 내면 서버와 두 벌이 되고, 어긋나면 대표가 둘로 보인다.
    test('대표는 사람당 하나다 — 새로 세우면 옛 대표가 내려간다', () async {
      final ok = (await repo.myVideos()).where((v) => v.passed).toList();
      expect(ok.length, greaterThan(1), reason: '대표 둘을 견줄 클립이 필요하다');

      await repo.patchVideo(ok[0].id, isFeatured: true);
      await repo.patchVideo(ok[1].id, isFeatured: true);

      final after = await repo.myVideos();
      expect(after.firstWhere((v) => v.id == ok[0].id).isFeatured, isFalse);
      expect(after.firstWhere((v) => v.id == ok[1].id).isFeatured, isTrue);
    });

    test('같은 영상을 다시 누르면 대표가 풀린다', () async {
      final target = (await repo.myVideos()).firstWhere((v) => v.passed);

      await repo.patchVideo(target.id, isFeatured: true);
      final off = await repo.patchVideo(target.id, isFeatured: false);

      expect(off.isFeatured, isFalse);
    });

    /// 🔴 **반려된 클립은 서버가 안 보는 영상이다** — 422 `CANNOT_FEATURE`.
    test('반려된 클립은 대표로 못 세운다', () async {
      await expectLater(
        repo.patchVideo(rejectedVideoId, isFeatured: true),
        throwsA(anything),
      );
    });

    test('지우면 목록에서 사라진다', () async {
      final target = (await repo.myVideos()).first;

      await repo.deleteVideo(target.id);

      expect(
        (await repo.myVideos()).where((v) => v.id == target.id),
        isEmpty,
      );
    });

    /// 🔴 **「아직」과 「없다」를 가른다.** 뭉치면 분석 중인 클립이 결과 없는
    /// 클립처럼 보인다.
    test('분석이 끝난 영상은 리포트가 온다', () async {
      final got = await repo.report(analyzedVideoId);

      expect(got, isA<ReportReady>());
      expect((got as ReportReady).report.summary, isNotEmpty);
    });

    test('없는 영상의 리포트는 예외가 아니라 missing 이다', () async {
      expect(await repo.report('no-such-video'), isA<ReportMissing>());
    });

    /// 🔴 반려된 클립은 **분석을 아예 안 했다** — 「아직」이 아니라 「없다」다.
    /// 「아직」으로 답하면 화면이 영영 오지 않을 결과를 기다리게 한다.
    test('반려된 클립의 리포트는 「아직」이 아니다', () async {
      expect(await repo.report(rejectedVideoId), isNot(isA<ReportReady>()));
    });
  });
}
