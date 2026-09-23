import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/dev/data_source.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/video/data/video_providers.dart';
import 'package:super_sub/features/video/data/video_repository_mock.dart';
import 'package:super_sub/features/video/presentation/my_videos_controller.dart';
import 'package:super_sub/features/video/presentation/screens/my_videos_screen.dart';

/// 🔴 **목업으로 고정한다.** 안 덮으면 `videoRepositoryProvider` 가 API
/// 구현체를 잡아 **시험이 실제 네트워크를 부른다**(앞 회차에 홈 시험이 실제로
/// 그랬다).
class _AlwaysMock extends DataSourceController {
  @override
  bool build() => true;
}

/// 🔴 **Mock 지연이 줄줄이 걸린다.** 목록이 와야 영상을 알고, 영상을 알아야
/// 재생 주소를 부른다 — 300ms 가 둘이다. 모자라게 흘리면 「트리를 버린 뒤에도
/// 타이머가 남았다」로 깨지는데, **그건 화면 잘못이 아니다**(앞 회차에도 같은
/// 것에 걸렸다).
///
/// 🔴 `pumpAndSettle` 은 안 쓴다 — 이 화면에는 로딩 인디케이터가 있어서
/// 안 멎는다(`flutter/CLAUDE.md`).
Future<void> settle(WidgetTester tester) async {
  await tester.pump(const Duration(milliseconds: 400));
  await tester.pump(const Duration(milliseconds: 400));
}

/// 🔴 **누르기 전에 화면 안으로 끌어온다.** 목록이 길어 아래쪽 단추가 창
/// 밖에 있으면 `tap` 이 조용히 빗나간다(「warnIfMissed」).
Future<void> tapKey(WidgetTester tester, String key) async {
  final finder = find.byKey(Key(key));
  await tester.ensureVisible(finder);
  await tester.pump();
  await tester.tap(finder);
  await settle(tester);
}

Future<ProviderContainer> pumpScreen(
  WidgetTester tester, {
  String userId = MockDb.playerId,
}) async {
  final container = ProviderContainer(
    overrides: [
      useMockProvider.overrideWith(_AlwaysMock.new),
      videoRepositoryProvider.overrideWithValue(
        MockVideoRepository(MockDb(), userId: userId),
      ),
    ],
  );
  addTearDown(container.dispose);

  await tester.pumpWidget(UncontrolledProviderScope(
    container: container,
    child: const MaterialApp(home: MyVideosScreen()),
  ));
  await settle(tester);
  return container;
}

void main() {
  testWidgets('분석 갈래로 열리고 편수가 보인다', (tester) async {
    await pumpScreen(tester);

    // 시드: 분석 둘(v-analyzed · v-running) · 업로드 둘(v-raw · v-rejected)
    expect(find.text('1 / 2'), findsOneWidget);
  });

  testWidgets('갈래를 바꾸면 업로드 쪽 목록으로 간다', (tester) async {
    await pumpScreen(tester);

    await tapKey(tester, 'tab-uploaded');

    expect(find.text('1 / 2'), findsOneWidget);
    // 🔴 반려 사유는 업로드 갈래에서 보여야 한다 — 그것 말고는 왜 안 됐는지
    //    알 데가 없다.
    await tapKey(tester, 'videos-next');
    expect(find.textContaining('상한을 넘습니다'), findsOneWidget);
  });

  /// 🔴 목록이 짧아 끝이 금방 온다 — 끝에서 반대쪽으로 돈다.
  testWidgets('끝에서 넘기면 처음으로 돈다', (tester) async {
    await pumpScreen(tester);

    await tapKey(tester, 'videos-next');
    expect(find.text('2 / 2'), findsOneWidget);

    await tapKey(tester, 'videos-next');
    expect(find.text('1 / 2'), findsOneWidget);
  });

  testWidgets('스트립에서 고르면 그 편으로 간다', (tester) async {
    await pumpScreen(tester);

    await tapKey(tester, 'strip-1');

    expect(find.text('2 / 2'), findsOneWidget);
  });

  /// 🔴 **업로드 갈래에서만** 낸다. 그냥 올린 영상은 리포트가 없어 추천 판에
  /// 아예 안 들어가므로, 거기 대표 단추를 두면 아무 데도 안 쓰이는 값을
  /// 고르게 된다.
  testWidgets('대표 단추는 분석 갈래에만, 공개 단추는 업로드 갈래에만 있다', (tester) async {
    await pumpScreen(tester);

    expect(find.byKey(const Key('videos-featured')), findsOneWidget);
    expect(find.byKey(const Key('videos-publish')), findsNothing);

    await tapKey(tester, 'tab-uploaded');

    expect(find.byKey(const Key('videos-featured')), findsNothing);
    expect(find.byKey(const Key('videos-publish')), findsOneWidget);
  });

  /// 🔴 **반려된 클립도 지울 수 있어야 한다.** 분석도 대표도 안 되는 영상이
  /// 지우지도 못하면 목록에 영영 남는다 — 「쓸 데도 없고 치울 수도 없는 것」이
  /// 된다.
  testWidgets('반려된 클립도 지울 수 있다', (tester) async {
    await pumpScreen(tester);

    await tapKey(tester, 'tab-uploaded');
    // 2번째가 반려된 클립이다(시드).
    await tapKey(tester, 'videos-next');
    expect(find.textContaining('상한을 넘습니다'), findsOneWidget);

    expect(find.byKey(const Key('videos-delete')), findsOneWidget);
    // 🔴 대표 단추는 없다 — 서버가 422 `CANNOT_FEATURE` 로 막는 영상이다.
    expect(find.byKey(const Key('videos-featured')), findsNothing);
  });

  testWidgets('대표를 세우면 안내가 뜬다', (tester) async {
    await pumpScreen(tester);

    await tapKey(tester, 'videos-featured');

    expect(find.textContaining('이 장면이 돕니다'), findsOneWidget);
  });

  /// 🔴 **되돌릴 수 없어서 곧바로 안 지운다.**
  testWidgets('삭제는 한 번 더 묻는다', (tester) async {
    await pumpScreen(tester);

    await tapKey(tester, 'videos-delete');

    expect(find.byKey(const Key('videos-delete-confirm')), findsOneWidget);
    expect(find.byKey(const Key('videos-delete-cancel')), findsOneWidget);
  });

  testWidgets('취소하면 안 지운다', (tester) async {
    final c = await pumpScreen(tester);
    final before = c.read(myVideosProvider).value!.length;

    await tapKey(tester, 'videos-delete');
    await tapKey(tester, 'videos-delete-cancel');

    expect(c.read(myVideosProvider).value!.length, equals(before));
  });

  testWidgets('정말 지우면 목록에서 빠진다', (tester) async {
    final c = await pumpScreen(tester);
    final before = c.read(myVideosProvider).value!.length;

    await tapKey(tester, 'videos-delete');
    await tapKey(tester, 'videos-delete-confirm');

    expect(c.read(myVideosProvider).value!.length, equals(before - 1));
  });

  /// 🔴 공개는 **제목과 함께 한 번에** 보낸다 — 나눠 보내면 그 사이에
  /// 끊겼을 때 이름 없는 영상이 남에게 보인다. 그래서 제목이 비면 안 눌린다.
  testWidgets('공개 폼은 제목이 비면 안 눌린다', (tester) async {
    await pumpScreen(tester);

    await tapKey(tester, 'tab-uploaded');
    await tapKey(tester, 'videos-publish');

    final save = tester.widget<FilledButton>(
      find.byKey(const Key('publish-save')),
    );
    expect(save.onPressed, isNull);

    await tester.enterText(find.byKey(const Key('publish-title')), '우리 팀 첫 골');
    await settle(tester);

    final after = tester.widget<FilledButton>(
      find.byKey(const Key('publish-save')),
    );
    expect(after.onPressed, isNotNull);
  });

  testWidgets('공개하면 단추가 「전체 공개 중」이 된다', (tester) async {
    await pumpScreen(tester);

    await tapKey(tester, 'tab-uploaded');
    await tapKey(tester, 'videos-publish');
    await tester.enterText(find.byKey(const Key('publish-title')), '우리 팀 첫 골');
    await settle(tester);
    await tapKey(tester, 'publish-save');

    expect(find.text('전체 공개 중'), findsOneWidget);
  });

  testWidgets('영상이 없으면 갈래에 맞는 빈 문구가 나온다', (tester) async {
    final container = ProviderContainer(
      overrides: [
        useMockProvider.overrideWith(_AlwaysMock.new),
        videoRepositoryProvider.overrideWithValue(
          // 신규 가입자는 영상이 하나도 없다.
          MockVideoRepository(MockDb(), userId: MockDb.newbieId),
        ),
      ],
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(UncontrolledProviderScope(
      container: container,
      child: const MaterialApp(home: MyVideosScreen()),
    ));
    await settle(tester);

    expect(find.text('아직 분석한 영상이 없습니다.'), findsOneWidget);

    await tapKey(tester, 'tab-uploaded');

    expect(find.text('아직 업로드한 영상이 없습니다.'), findsOneWidget);
  });
}
