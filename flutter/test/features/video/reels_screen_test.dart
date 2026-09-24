import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/app.dart';
import 'package:super_sub/core/dev/data_source.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/core/router/app_router.dart';
import 'package:super_sub/features/auth/data/auth_providers.dart';
import 'package:super_sub/features/auth/data/auth_repository_mock.dart';
import 'package:super_sub/features/auth/presentation/session_controller.dart';
import 'package:super_sub/features/intro/presentation/intro_gate.dart';
import 'package:super_sub/features/profile/presentation/widgets/player_card_view.dart';
import 'package:super_sub/features/video/presentation/screens/reels_screen.dart';

/* 공개 영상 **전체화면 보기**(2026-09-24). 홈 영상 줄에서 누른 **그 영상**이
   열려야 하고, 레퍼런스에서 **일부러 뺀 것들**이 되살아나지 않아야 한다.

   관용구는 `app_router_test.dart` 와 같다 — 목업 지연이 줄줄이 걸리므로
   `pumpAndSettle` 대신 정해진 만큼 흘려보낸다(이 화면은 목록을 기다리는 동안
   **무한 애니메이션**인 로딩 동그라미를 띄우므로 `pumpAndSettle` 은 10분
   타임아웃까지 간다). */

/// 목 시드의 공개 영상 둘 — **새것부터** 온다(`publicVideos()` 가 내림차순).
const _newest = 'v-public-manager';
const _older = 'v-public-manager-2';

Future<void> _settle(WidgetTester tester) async {
  for (var i = 0; i < 6; i += 1) {
    await tester.pump(const Duration(milliseconds: 400));
  }
}

class _AlwaysMock extends DataSourceController {
  @override
  bool build() => true;
}

/// 로그인한 채로 앱을 띄우고 그 영상의 전체화면으로 들어간다.
Future<ProviderContainer> _pumpReel(WidgetTester tester, String videoId) async {
  tester.view.physicalSize = const Size(1080, 2340);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);

  final container = ProviderContainer(
    overrides: [
      introEnabledProvider.overrideWithValue(false),
      authRepositoryProvider.overrideWith(
        (ref) => MockAuthRepository(ref.watch(mockDbProvider)),
      ),
      // 🔴 목업으로 고정한다 — 안 덮으면 시험이 실제 네트워크를 부른다.
      useMockProvider.overrideWith(_AlwaysMock.new),
    ],
  );
  addTearDown(container.dispose);

  await tester.pumpWidget(UncontrolledProviderScope(
    container: container,
    child: const SuperSubApp(),
  ));
  unawaited(
    container.read(sessionControllerProvider.notifier).loginAs(MockDb.playerId),
  );
  await _settle(tester);

  container.read(routerProvider).push('/videos/$videoId');
  await _settle(tester);
  return container;
}

/// 목 시드의 공개 영상 수 — 아래 나머지 계산에 쓴다.
const _publicCount = 2;

/// 시작 자리가 **목록에서 몇 번째인가**.
///
/// 🔴 **나머지를 본다** (2026-09-24). 끝없이 돌기 위해 **1000 바퀴 앞**에서
/// 시작하므로(`_kLoopBase`) 실제 `initialPage` 는 2000 대의 수다 — 자리를 그대로
/// 비교하면 「끝없이」를 넣는 순간 이 시험이 깨진다(실제로 깨져서 알았다).
int _startIndex(WidgetTester tester) {
  final pv = tester.widget<PageView>(find.byType(PageView));
  final page = (pv.controller as PageController).initialPage;
  /* 🔴 **한 바퀴 위에서 시작하는지도 함께 본다** — 나머지만 보면 0 에서
     시작하는 구현(위로 못 넘김)도 통과한다. */
  expect(page, greaterThanOrEqualTo(_publicCount), reason: '위로도 넘길 자리가 있어야 한다');
  return page % _publicCount;
}

void main() {
  testWidgets('누른 그 영상에서 시작한다', (tester) async {
    /* 🔴 **목록의 첫째가 아닌 것을 고른다.** 첫째(`_newest`)로 시험하면 시작
       자리가 0 이라, **id 를 아예 안 보고 늘 0 으로 여는 구현**도 통과한다. */
    await _pumpReel(tester, _older);

    expect(find.byType(ReelsScreen), findsOneWidget);
    expect(_startIndex(tester), 1, reason: '둘째 영상이므로 1');
  });

  testWidgets('첫 영상을 누르면 0 에서 시작한다', (tester) async {
    await _pumpReel(tester, _newest);
    expect(_startIndex(tester), 0);
  });

  /* 🔴 **끝이 없다** (2026-09-24 사용자 요청: 「영상 다 내리면 끝이 아니라,
     올라온 영상들 계속 나오게」). `itemCount` 가 `null` 이라야 쪽이 무한히
     이어진다 — 목록 길이를 넣으면 마지막에서 멈춘다. */
  testWidgets('쪽 넘김에 끝이 없다', (tester) async {
    await _pumpReel(tester, _newest);
    final pv = tester.widget<PageView>(find.byType(PageView));
    expect(
      pv.childrenDelegate.estimatedChildCount,
      isNull,
      reason: '끝이 있으면 그 수가 나온다',
    );
  });

  /* ⛔ **레퍼런스에서 뺀 것들** (2026-09-24 사용자 지시). 되살리면 이 시험이
     깨져서 알려 준다 — 「빼 달라」는 요청은 시간이 지나면 **왜 없는지**를
     아무도 모르게 되는 종류라, 없다는 것 자체를 못 박아 둔다. */
  testWidgets('북마크·공유·Follow·음악 알약이 없다', (tester) async {
    await _pumpReel(tester, _newest);

    expect(find.byIcon(Icons.bookmark_border), findsNothing, reason: '북마크');
    expect(find.byIcon(Icons.bookmark), findsNothing, reason: '북마크');
    expect(find.byIcon(Icons.ios_share), findsNothing, reason: '공유');
    expect(find.byIcon(Icons.share), findsNothing, reason: '공유');
    expect(find.text('Follow'), findsNothing, reason: '팔로우 단추');
    expect(find.text('팔로우'), findsNothing, reason: '팔로우 단추');
    expect(find.byIcon(Icons.music_note), findsNothing, reason: '음악 알약');
  });

  testWidgets('주인은 닉네임만 나오고 좋아요·댓글은 0 에서 시작한다', (tester) async {
    await _pumpReel(tester, _newest);

    // 목 시드의 공개 영상 둘은 모두 이감독 것이다.
    expect(find.text('이감독'), findsOneWidget);

    /* 🔴 **주인 카드가 실제로 그려진다.** 목 리포지토리는 2026-09-24 까지
       `uploaderCardSlug` 를 **안 줬고**, 그래서 목 모드에서는 이 자리가 영영
       비어 있었다 — 오류가 안 나는 종류라 시험이 없으면 못 알아챈다. */
    expect(find.byType(PlayerCardView), findsOneWidget, reason: '주인 카드');

    /* 🔴 **0 에서 시작한다** — 지어낸 큰 수(45.2k 같은)를 안 쓴다. 시연에서
       그 수를 묻는 사람이 생기고, 그때 「가짜입니다」라고 답하게 된다. */
    expect(find.text('0'), findsNWidgets(2), reason: '좋아요·댓글 둘 다 0');
    expect(find.text('45.2k'), findsNothing);
  });

  /* 🔴 **아이콘이 아니라 키로 집는다** — 하트가 「빈 것 ↔ 찬 것」에서
     「흰 것 ↔ 분홍 것」으로 바뀌면서(2026-09-24 레퍼런스) `Icons.favorite_border`
     로 집던 시험이 깨졌다. 모양은 또 바뀔 수 있고 **자리는 안 바뀐다.** */
  testWidgets('좋아요를 누르면 1 이 되고 다시 누르면 0 으로 돌아온다', (tester) async {
    await _pumpReel(tester, _newest);

    await tester.tap(find.byKey(const Key('reel-like')));
    await tester.pump();
    expect(find.text('1'), findsOneWidget);

    await tester.tap(find.byKey(const Key('reel-like')));
    await tester.pump();
    expect(find.text('0'), findsNWidgets(2));
  });

  testWidgets('댓글을 쓰면 그 수가 올라간다', (tester) async {
    await _pumpReel(tester, _newest);

    await tester.enterText(find.byKey(const Key('reel-comment-field')), '좋은데요');
    await tester.tap(find.byKey(const Key('reel-comment-send')));
    await tester.pump();

    expect(find.text('1'), findsOneWidget, reason: '댓글 수');
    /* 🔴 **보낸 뒤 입력칸이 비어야 한다** — 안 비우면 다음 댓글이 앞의 것에
       이어 붙는다. */
    expect(find.text('좋은데요'), findsNothing);
  });

  /* 🔴 **쓴 댓글을 다시 볼 수 있어야 한다** (2026-09-24 사용자 지적: 「댓글
     썼으면 댓글 아이콘 누르면 보여야지」). 전에는 말풍선을 눌러도 아래 입력줄로
     **초점만** 옮겨서, 쓴 것이 어디에도 안 남았다. */
  testWidgets('말풍선을 누르면 쓴 댓글이 보인다', (tester) async {
    await _pumpReel(tester, _newest);

    await tester.enterText(find.byKey(const Key('reel-comment-field')), '골 좋네요');
    await tester.tap(find.byKey(const Key('reel-comment-send')));
    await tester.pump();
    // 아직 접혀 있다 — 보낸 것만으로 펼쳐지지는 않는다.
    expect(find.text('골 좋네요'), findsNothing);

    await tester.tap(find.byKey(const Key('reel-comment')));
    await tester.pump();
    expect(find.byKey(const Key('reel-comment-list')), findsOneWidget);
    expect(find.text('골 좋네요'), findsOneWidget);

    // 다시 누르면 접힌다.
    await tester.tap(find.byKey(const Key('reel-comment')));
    await tester.pump();
    expect(find.text('골 좋네요'), findsNothing);
  });

  /* 🔴 **영상을 잘라내지 않는다** (2026-09-24 사용자 지적: 「가로 영상인데 다
     세로로 자르면 어떻게 해? 영상은 다 보여야지」). 남는 자리는 검정이다.
     ⛔ `BoxFit.cover` 로 되돌리면 이 시험이 깨진다. */
  test('영상과 포스터는 잘리지 않고 통째로 들어간다', () {
    /* ⚠️ **그리는 자리에서 읽지 않는다 — 헛시험이었다.** 처음엔 화면을 띄워
       [FittedBox] 의 `fit` 을 모아 봤는데, 위젯 시험에서는 재생기가 초기화되지
       않아 그 [FittedBox] 가 **아예 안 생긴다** — `cover` 로 되돌려도 그냥
       통과했다(일부러 되돌려 확인했다). 값 자체를 못 박아야 잡힌다. */
    expect(kReelFit, BoxFit.contain);
  });

  testWidgets('없는 영상 id 로 들어가면 그 자리에 머물지 않는다', (tester) async {
    /* 공개를 내렸거나 지워진 영상을 가리키는 링크로 들어온 경우다.
       🔴 **엉뚱한 영상을 말없이 보여 주지 않는다** — 누른 것과 다른 것이
       뜨면 버그로 읽힌다. 물러나는 쪽을 골랐다. */
    await _pumpReel(tester, 'v-does-not-exist');
    expect(find.byType(ReelsScreen), findsNothing);
  });
}
