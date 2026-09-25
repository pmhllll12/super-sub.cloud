import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/core/dev/data_source.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/video/data/video_providers.dart';
import 'package:super_sub/features/video/data/video_repository_mock.dart';
import 'package:super_sub/features/video/presentation/my_videos_controller.dart';
import 'package:super_sub/core/widgets/silver_sweep_border.dart';
import 'package:super_sub/features/video/presentation/screens/my_videos_screen.dart';
import 'package:super_sub/features/video/presentation/widgets/report_panel.dart';

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

  _skinTests();
}

/// 🔴 **이 화면은 「영상 분석」 화면과 한 식구다** (2026-09-25 사용자: 「UI 가
/// 혼자 따로 놀거든? … 영상 분석 시작하기 누르면 나오는 그런 스타일로」).
///
/// 위 3분의 1은 검은 영상 자리, 아래는 밝은 판 — [AnalyzeScreen] 과 같은
/// 골격이다. 여기 시험은 **그 골격이 다시 흩어지지 않게** 지킨다.
void _skinTests() {
  /// 🔴 **갈래 둘 + 업로드가 한 줄이다** (같은 요청: 「업로드 버튼도 한 줄에
  /// 둬. 총 3개」). 전에는 업로드만 **앱바 아이콘**으로 떨어져 있었다.
  testWidgets('위 한 줄에 단추가 셋이다', (tester) async {
    await pumpScreen(tester);

    final ys = [
      for (final k in ['tab-analyzed', 'tab-uploaded', 'videos-upload'])
        tester.getCenter(find.byKey(Key(k))).dy,
    ];

    expect(find.byKey(const Key('videos-upload')), findsOneWidget);
    expect(ys[1], closeTo(ys[0], 1), reason: '$ys');
    expect(ys[2], closeTo(ys[0], 1), reason: '$ys');
  });

  /// 🔴 **지우기는 완전한 빨강이다** (같은 요청). 흐린 회색 글자 단추였는데,
  /// 되돌릴 수 없는 것이 다른 단추와 같은 무게로 보이면 안 된다.
  testWidgets('지우기 단추는 빨간 면이다', (tester) async {
    await pumpScreen(tester);

    final box = tester.widget<Container>(
      find
          .descendant(
            of: find.byKey(const Key('videos-delete')),
            matching: find.byType(Container),
          )
          .first,
    );

    expect((box.decoration! as BoxDecoration).color, kVideoDanger);
  });

  /// 🔴 **리포트 단추가 좌우를 꽉 채우지 않는다** (같은 요청: 「컴팩트하게
  /// 좌우 쫙 줄여」). 전에는 `minimumSize: Size.fromHeight(44)` 라 **폭을
  /// 통째로** 먹었다.
  testWidgets('리포트 단추는 좁다', (tester) async {
    await pumpScreen(tester);

    final w = tester.getSize(find.byKey(const Key('videos-report'))).width;

    expect(w, lessThan(tester.view.physicalSize.width / 3));
  });

  /// 🔴 **줄 차례가 정해져 있다** (2026-09-25 사용자 지시): 갈래 셋 → 영상 →
  /// 분석 완료들(스트립) → 다음 영상 고르기 → 삭제·대표 → 리포트.
  ///
  /// ⚠️ 이 시험은 **위에서 아래로의 차례**만 본다. 간격·색은 안 본다 —
  /// 그것까지 박으면 손볼 때마다 시험이 깨진다.
  testWidgets('줄 차례가 위에서 아래로 정해져 있다', (tester) async {
    await pumpScreen(tester);

    double y(String k) => tester.getCenter(find.byKey(Key(k))).dy;

    expect(y('tab-analyzed'), lessThan(y('strip-0')));
    expect(y('strip-0'), lessThan(y('videos-next')));
    expect(y('videos-next'), lessThan(y('videos-delete')));
    expect(y('videos-delete'), lessThan(y('videos-report')));
  });

  /// 🔴 **맨 위에는 뒤로가기만 있다** (2026-09-25 정정 — 사용자: 「맨 윗줄
  /// 뒤로 가기 있는 곳만 영상이랑 안겹치게 그 뒤로가기 크기 만큼만 위에
  /// 남겨두고, 분석영상 업로드 영상 업로드 하기 버튼 영상 아래에 두자」).
  ///
  /// ⚠️ 앞서는 셋을 **뒤로가기 옆**에 뒀었다 — 그러면 알약이 좁아져 글자가
  /// 잘리고, 화살표와 한 줄에 섞여 무엇이 갈래인지 안 읽혔다.
  testWidgets('갈래 줄은 영상 아래에 있다', (tester) async {
    await pumpScreen(tester);

    final back = tester.getRect(find.byKey(const Key('videos-back')));
    final tab = tester.getRect(find.byKey(const Key('tab-analyzed')));

    expect(tab.top, greaterThan(back.bottom), reason: '$back / $tab');
  });

  /// 🔴 **「분석 완료」 칸은 완전한 원이다** (2026-09-25 사용자 요청) — 네모를
  /// 뺀 다음 단계다. 고른 칸에만 **실버가 돈다.**
  testWidgets('영상 칸은 원이고 고른 것만 실버가 돈다', (tester) async {
    await pumpScreen(tester);

    final box = tester.getSize(find.byKey(const Key('strip-0')));
    expect(box.width, closeTo(box.height, 0.5), reason: '$box');

    // 도는 테는 **고른 칸에만** 하나 — 여럿이면 화면이 산만해진다.
    expect(find.byType(SilverSweepBorder), findsOneWidget);
  });

  /// 🔴 **고른 칸이 더 잘 보여야 한다** (2026-09-25 사용자: 「내가 선택한게
  /// 오히려 더 안보이고 선택 안한게 오히려 선택한거 처럼 잘 보여」).
  ///
  /// 까닭은 [SilverSweepBorder] 의 기본 실버(`#E8F0F4`)가 **검은 화면용**
  /// 밝은 값이라 **밝은 판에 붙어 사라졌기** 때문이다. 하단 바가 흰 막대가
  /// 되면서 같은 것을 겪었다 — 「흰 막대에서는 진할수록 보인다」.
  testWidgets('고른 칸의 테가 안 고른 칸보다 진하다', (tester) async {
    await pumpScreen(tester);

    final sweep = tester.widget<SilverSweepBorder>(
      find.byType(SilverSweepBorder),
    );
    // 밝은 판 위다 — 도는 빛이 **어두워야** 보인다.
    expect(sweep.color!.computeLuminance(), lessThan(0.5));

    // 안 고른 칸의 테는 그보다 **옅다**.
    final off = tester.widget<DecoratedBox>(
      find
          .descendant(
            of: find.byKey(const Key('strip-1')),
            matching: find.byType(DecoratedBox),
          )
          .first,
    );
    final side = (off.decoration as BoxDecoration).border!.top;
    expect(side.color.a, lessThan(sweep.color!.a));
  });

  /// 🔴 **삭제·대표 바로 위에 얇은 검정 선** (같은 요청) — 그 위(넘기는 줄)와
  /// 가른다.
  testWidgets('삭제·대표 위에 가르는 선이 있다', (tester) async {
    await pumpScreen(tester);

    final line = tester.getRect(find.byKey(const Key('videos-actions-line')));
    final del = tester.getRect(find.byKey(const Key('videos-delete')));

    expect(line.bottom, lessThanOrEqualTo(del.top));
  });

  /// 🔴 **삭제는 왼쪽, 대표는 오른쪽**(같은 지시) — 같은 줄에 선다.
  testWidgets('삭제가 왼쪽 대표가 오른쪽에 나란히 선다', (tester) async {
    await pumpScreen(tester);

    final del = tester.getRect(find.byKey(const Key('videos-delete')));
    final fav = tester.getRect(find.byKey(const Key('videos-featured')));

    expect(del.center.dx, lessThan(fav.center.dx));
    expect(del.center.dy, closeTo(fav.center.dy, 1));
  });

  /// 🔴 **리포트는 새 화면으로 안 간다** (같은 지시: 「새로운 리포트 탭이
  /// 나오는게 아니라 부드럽고 자연스럽게 펴지면서 아래로」). 화면을 밀면 위의
  /// 영상이 사라졌다 돌아오고, 닫으려면 뒤로 가야 한다.
  /// 🔴 **분석 갈래에서는 리포트가 처음부터 펴져 있다** (2026-09-25 사용자:
  /// 「리포트는 분석 영상에서는 기본값은 보여주는 거로 하자. 들어가면 바로
  /// 리포트 보이게 하고, 사용자가 닫게 하자」).
  ///
  /// 까닭: 분석 영상을 보러 온 사람이 보려는 것이 **리포트**다 — 한 번 더
  /// 누르게 하면 그 화면의 목적이 한 단 뒤로 밀린다.
  testWidgets('분석 갈래에서는 리포트가 처음부터 펴져 있다', (tester) async {
    await pumpScreen(tester);

    // 🔴 **여전히 이 화면이다** — 새 경로를 밀지 않았다.
    expect(find.byType(MyVideosScreen), findsOneWidget);
    expect(find.byKey(const Key('inline-report')), findsOneWidget);

    await tapKey(tester, 'videos-report');
    // 접히는 동안은 남아 있다 — 다 접힐 때까지 흘린다.
    await settle(tester);

    expect(find.byKey(const Key('inline-report')), findsNothing);
  });

  /// 🔴 **영상을 넘기면 열려 있던 리포트를 닫는다** — 안 닫으면 앞 영상의
  /// 리포트가 다음 영상 아래에 그대로 붙어 있다.
  /// 🔴 **넘기면 앞 영상의 리포트를 안 물고 간다** — 열린 채 넘기면 다음
  /// 영상 아래에 **앞 영상의 리포트**가 붙어 있다. 넘긴 자리에서 그 영상의
  /// 리포트로 다시 펴진다.
  testWidgets('다른 영상으로 넘겨도 그 영상의 리포트를 편다', (tester) async {
    await pumpScreen(tester);

    await tapKey(tester, 'videos-next');
    await settle(tester);

    final panel = tester.widget<ReportPanel>(find.byType(ReportPanel));
    expect(panel.videoId, isNot('v-analyzed'));
  });
}
