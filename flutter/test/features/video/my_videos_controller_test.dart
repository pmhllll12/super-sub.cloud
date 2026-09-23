import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/dev/data_source.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/video/data/clip_file.dart';
import 'package:super_sub/features/video/data/models/my_video.dart';
import 'package:super_sub/features/video/data/video_providers.dart';
import 'package:super_sub/features/video/data/video_repository_mock.dart';
import 'package:super_sub/features/video/presentation/my_videos_controller.dart';

/// 🔴 **목업으로 고정한다.** 안 덮으면 `videoRepositoryProvider` 가 API
/// 구현체를 잡아 **시험이 실제 네트워크를 부른다**(앞 회차에 홈 시험이 실제로
/// 그랬다). 교체 지점이 `useMockProvider` 하나라 여기만 덮으면 따라온다.
class _AlwaysMock extends DataSourceController {
  @override
  bool build() => true;
}

ProviderContainer makeContainer() {
  final container = ProviderContainer(
    overrides: [
      useMockProvider.overrideWith(_AlwaysMock.new),
      // 세션을 안 거치고 **직접** 물린다 — 컨트롤러만 재는 자리라 로그인
      // 흐름까지 끌어오면 무엇이 깨졌는지 흐려진다.
      videoRepositoryProvider.overrideWithValue(
        MockVideoRepository(MockDb(), userId: MockDb.playerId),
      ),
    ],
  );
  addTearDown(container.dispose);
  return container;
}

Future<List<MyVideo>> load(ProviderContainer c) =>
    c.read(myVideosProvider.future);

void main() {
  group('MyVideosController', () {
    test('목록을 읽는다', () async {
      final c = makeContainer();

      expect(await load(c), isNotEmpty);
    });

    /// 🔴 갈래를 가르는 것은 `analysis_job_id` 다. 분석을 걸었지만 **대기
    /// 중인** 클립이 「그냥 올린 것」으로 새어 나가면 안 된다.
    test('분석 중인 클립은 업로드 갈래로 새지 않는다', () async {
      final c = makeContainer();

      final split = splitVideos(await load(c));

      expect(split.analyzed.map((v) => v.id), contains('v-running'));
      expect(split.uploaded.map((v) => v.id), isNot(contains('v-running')));
    });

    /// 🔴 반려된 클립은 작업이 없으므로 업로드 쪽이 사실이다.
    test('반려된 클립은 업로드 갈래에 남는다', () async {
      final c = makeContainer();

      final split = splitVideos(await load(c));

      expect(split.uploaded.map((v) => v.id), contains('v-rejected'));
    });

    test('올린 것이 목록 맨 앞에 온다', () async {
      final c = makeContainer();
      await load(c);

      final saved = await c.read(myVideosProvider.notifier).upload(
            file: ClipFile(
              name: '새 영상.mp4',
              contentType: 'video/mp4',
              sizeBytes: 10,
              openRead: () => Stream.value(const [1, 2, 3]),
            ),
            meta: const ClipMeta(durationMs: 9000, width: 1920, height: 1080),
            sportCode: 'football',
          );

      expect(c.read(myVideosProvider).value!.first.id, equals(saved.id));
    });

    /// 🔴 **응답에는 바뀐 한 줄만 온다.** 서버는 옛 대표를 이미 내렸는데
    /// 화면이 그걸 반영 안 하면 **대표가 둘로 보인다.**
    test('대표를 옮기면 옛 대표가 화면에서도 내려간다', () async {
      final c = makeContainer();
      final all = await load(c);
      final ok = all.where((v) => v.passed).toList();
      final notifier = c.read(myVideosProvider.notifier);

      await notifier.setFeatured(ok[0].id, true);
      await notifier.setFeatured(ok[1].id, true);

      final after = c.read(myVideosProvider).value!;
      expect(after.where((v) => v.isFeatured).map((v) => v.id), [ok[1].id]);
    });

    /// 🔴 **서버가 바꾼 뒤에 화면을 바꾼다.** 실패했는데 공개로 보이면
    /// 되돌릴 수 없는 쪽으로 틀린 것이다.
    test('대표 세우기가 실패하면 화면도 안 바뀐다', () async {
      final c = makeContainer();
      final all = await load(c);
      final rejected = all.firstWhere((v) => !v.passed);

      await expectLater(
        c.read(myVideosProvider.notifier).setFeatured(rejected.id, true),
        throwsA(anything),
      );

      final after = c.read(myVideosProvider).value!;
      expect(after.firstWhere((v) => v.id == rejected.id).isFeatured, isFalse);
    });

    test('공개하면 제목과 함께 그 줄만 바뀐다', () async {
      final c = makeContainer();
      final all = await load(c);
      final target = all.firstWhere((v) => !v.analyzed && v.passed);

      await c.read(myVideosProvider.notifier).publish(
            target.id,
            title: '우리 팀 첫 골',
            description: '왼발 감아차기',
          );

      final after = c.read(myVideosProvider).value!;
      final row = after.firstWhere((v) => v.id == target.id);
      expect(row.isPublic, isTrue);
      expect(row.title, equals('우리 팀 첫 골'));
      expect(after, hasLength(all.length));
    });

    test('공개를 풀면 제목은 남고 공개만 꺼진다', () async {
      final c = makeContainer();
      final all = await load(c);
      final target = all.firstWhere((v) => !v.analyzed && v.passed);
      final notifier = c.read(myVideosProvider.notifier);

      await notifier.publish(target.id, title: '제목', description: '');
      await notifier.unpublish(target.id);

      final row = c.read(myVideosProvider).value!
          .firstWhere((v) => v.id == target.id);
      expect(row.isPublic, isFalse);
      expect(row.title, equals('제목'));
    });

    test('지우면 목록에서 빠진다', () async {
      final c = makeContainer();
      final all = await load(c);

      await c.read(myVideosProvider.notifier).remove(all.first.id);

      expect(
        c.read(myVideosProvider).value!.map((v) => v.id),
        isNot(contains(all.first.id)),
      );
    });

    /// 🔴 서버가 안 지웠는데 화면에서 사라지면 「사라진 것처럼 보이는데
    /// 실제로는 남아 있다」가 된다.
    test('지우기가 실패하면 목록에 그대로 남는다', () async {
      final c = makeContainer();
      final all = await load(c);

      await expectLater(
        c.read(myVideosProvider.notifier).remove('no-such-video'),
        throwsA(anything),
      );

      expect(c.read(myVideosProvider).value, hasLength(all.length));
    });
  });
}
