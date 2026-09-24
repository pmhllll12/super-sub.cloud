import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/core/theme/app_theme.dart';
import 'package:super_sub/core/widgets/screen_tint.dart';
import 'package:super_sub/features/intro/presentation/brand_mark.dart';
import 'package:super_sub/features/auth/data/auth_providers.dart';
import 'package:super_sub/features/auth/data/auth_repository_mock.dart';
import 'package:super_sub/core/dev/data_source.dart';
import 'package:super_sub/features/auth/presentation/session_controller.dart';
import 'package:super_sub/features/home/presentation/screens/home_screen.dart';
import 'package:super_sub/features/home/presentation/widgets/home_video_strip.dart';
import 'package:super_sub/features/team/data/squad_providers.dart';
import 'package:super_sub/features/profile/presentation/widgets/player_card_view.dart';

/* 🔴 **자리를 재는 시험은 실기기를 그대로 흉내 낸다**(`device: true`).
   아래 값은 2026-09-24 에 실기기에서 `MediaQuery` 를 찍어 온 것이다:

       size=411.4×891.4  dpr=2.625  padding.top=38.5

   기본값(1080×2340 @ dpr 3 = **360×780**, 인셋 0)과 갈리는 것이 셋이고,
   **셋 다 실기기에 없는 겹침을 시험에서만 만든다.**

   1\. **상태 바 자리가 없다** — 홈은 맨 위 것들을 전부 `safeTop + 8` 에서
      시작하므로, 0 이면 판·인사말·「내 프로필」이 통째로 38px 위로 붙는다.
   2\. **세로가 111 짧다** — 아래에서 올라오는 흰 판이 그만큼 위로 붙고,
      그 위에 매달린 소개 두 줄도 같이 올라온다.
   3\. 🔴 **가로가 51 좁다 — 이게 제일 고약하다.** 소개 두 줄(35)은 실기기
      폭에 **간신히** 한 줄로 들어간다. 조금만 좁아도 각 줄이 두 줄로 접혀
      덩이가 두 배가 된다. **411.0 과 411.4 도 갈린다** — 그래서 논리 폭을
      맞추지 말고 `physicalSize`·`devicePixelRatio` 를 기기 값 그대로 준다.

   ⚠️ 실제로 2026-09-24 에 1·2 때문에 「판이 소개 두 줄을 침범한다」고 잘못
   읽고 판을 한 번 늘렸다 되돌렸다. **재는 시험은 기기와 같은 화면에서 잰다.** */
const Size _kDevicePhysicalSize = Size(1080, 2340);
const double _kDeviceDpr = 2.625;
const double _kDeviceTopInset = 38.5 * _kDeviceDpr;

Future<ProviderContainer> _pumpLoggedIn(
  WidgetTester tester, {
  bool device = false,
  bool settle = true,
}) async {
  // **폰 크기로 돌린다.** 홈은 판 · 영상 분석 · 하단 바가 세로로 꽉 차는
  // 화면이라 기본 800×600 에서는 판이 짜부라진다(app_router_test.dart 와 같다).
  tester.view.physicalSize =
      device ? _kDevicePhysicalSize : const Size(1080, 2340);
  tester.view.devicePixelRatio = device ? _kDeviceDpr : 3;
  if (device) {
    tester.view.padding = const FakeViewPadding(top: _kDeviceTopInset);
    tester.view.viewPadding = const FakeViewPadding(top: _kDeviceTopInset);
  }
  addTearDown(tester.view.reset);

  final container = ProviderContainer(
    overrides: [
      authRepositoryProvider.overrideWith(
        (ref) => MockAuthRepository(ref.watch(mockDbProvider)),
      ),
      /* 🔴 **목업으로 고정한다.** 이걸 빼면 카드·스쿼드 provider 가 API
         구현체를 잡아 **시험이 실제 네트워크를 부른다** — 느리고, 서버 상태에
         따라 결과가 흔들린다. 교체 지점이 `useMockProvider` 하나라서 여기만
         덮으면 둘 다 따라온다. */
      useMockProvider.overrideWith(() => _AlwaysMock()),
    ],
  );
  addTearDown(container.dispose);

  await tester.pumpWidget(UncontrolledProviderScope(
    container: container,
    child: const MaterialApp(home: HomeScreen()),
  ));

  // MockAuthRepository는 300ms 지연을 흉내낸다. 위젯 테스트의 가짜 시계는
  // pump로만 흘러가므로, pumpWidget 이전에 이 Future를 직접 await하면
  // 시계가 멈춰 있어 영원히 끝나지 않는다 — login_screen_test.dart와
  // 동일한 관용구(탭/트리거 후 pump)를 따른다.
  unawaited(
    container.read(sessionControllerProvider.notifier).loginAs(MockDb.playerId),
  );
  await tester.pump(const Duration(milliseconds: 500));
  /* 🔴 **더 흘려보낸다 (2026-09-21).** Mock 의 300ms 지연이 **줄줄이** 걸린다:
     로그인이 끝나야 `teams` 를 알아 스쿼드를 부르고, 스쿼드가 와야 그 안의
     팀원 카드를 부른다. 여기서 안 흘려보내면 시험이 「위젯 트리를 버린 뒤에도
     타이머가 남았다」로 깨진다 — 화면 잘못이 아니라 흘려보내기가 모자란 것이다. */
  /* 🔴 **`settle: false` 는 들어오는 동작의 첫 프레임을 보려는 것이다.**
     위 500ms 한 번으로 세션이 와서 인사말이 **막 세워진** 참이라, 여기서
     더 흘려보내지 않으면 들어오기가 아직 0 이다. */
  if (settle) {
    for (var i = 0; i < 3; i += 1) {
      await tester.pump(const Duration(milliseconds: 500));
    }
  }
  // **pumpAndSettle을 쓰지 않는다.** 유리 조각의 테두리를 도는 빛이 무한
  // 반복이라 영영 안 멎는다.
  return container;
}

/// 판을 펼친다 — 손잡이를 누르고 스프링이 앉고 알약이 떠오를 때까지 흘려보낸다.
Future<void> _openSheet(WidgetTester tester) async {
  await tester.tap(find.byKey(const Key('home-squad-handle')));
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 1500));
  await tester.pump(const Duration(milliseconds: 700));
}

/// 화면에서 **실제로 보이는 정도** — 위에 겹친 [Opacity] 를 **전부 곱한다**.
///
/// 🔴 **가장 안쪽 하나만 보지 않는다 (2026-09-22 정정).** 전에는 `.first`
/// 로 제일 가까운 [Opacity] 하나만 읽었는데, 「영상 분석 시작하기」 알약이
/// **겹친 두 [Opacity] 안**에 들어가면서 틀린 답을 냈다 — 바깥(판이 띠가 될
/// 때 걷는 것)은 0 인데 안쪽(떠날 때 걷는 것)이 1 이라 **1 로 읽혔다.**
/// 곱하면 어느 층이 걷었든 「안 보인다」가 0 으로 나온다.
double _opacityAbove(WidgetTester tester, Finder target) {
  /* 🔴 **없는 것을 「다 보인다」로 읽지 않는다 (2026-09-22 정정).** 곱셈으로
     바꾸면서 대상이 **아예 없을 때 곱할 것이 없어 1 이 나왔다** — 글귀를
     고쳐서 못 찾은 것을 「멀쩡히 보인다」로 읽고 시험이 엉뚱한 곳에서
     깨졌다. 없으면 여기서 곧장 알린다. */
  expect(target, findsWidgets, reason: '잴 대상이 화면에 없다');
  return find
      .ancestor(of: target, matching: find.byType(Opacity))
      .evaluate()
      .fold<double>(1, (acc, e) => acc * (e.widget as Opacity).opacity);
}

/// 안내 알약이 **얼마나 보이는가** — 🔴 [Opacity] 가 아니라 **글자 알파**다.
///
/// 🔴 **왜 `_opacityAbove` 로 못 재는가 (2026-09-22).** 이 알약은 안에
/// `BackdropFilter`(유리)가 있어서 [Opacity] 로 걷으면 **흐림이 읽을 뒤가
/// 없어져 깜빡인다**(사용자가 실기기에서 잡았다). 그래서 부르는 쪽이
/// `Opacity` 를 안 쓰고 알약이 **제 알파를 직접** 받는다 — 잴 것도 그쪽이다.
///
/// ⚠️ `_opacityAbove` 로 재면 **감싼 `Opacity` 가 없어 늘 1** 이 나온다.
double _hintAlpha(WidgetTester tester, String label) =>
    tester.widget<Text>(find.text(label)).style!.color!.a;

/// 흔드는 손의 **지금 각도**(라디안) — 회전 행렬에서 되읽는다.
/// 0 이면 안 흔드는 중이다.
double _handAngle(WidgetTester tester) {
  final m = tester
      .widget<Transform>(find.byKey(const Key('home-greeting-hand')))
      .transform;
  return math.atan2(m.storage[1], m.storage[0]);
}

/// 인사말이 화면 왼쪽에서 떨어진 거리 — `home_screen.dart` 의 `_kGreetLeft`.
/// 🔴 그쪽이 정본이고 여기는 옮겨 적은 것이다(비공개라 못 부른다).
const double _kGreetLeft = 20;

Finder _blankSeats() => find.byWidgetPredicate(
      (w) => w.key is ValueKey<String> &&
          (w.key! as ValueKey<String>).value.startsWith('squad-add-'),
    );

class _AlwaysMock extends DataSourceController {
  @override
  bool build() => true;
}

void main() {
  // 2026-09-15 — 홈 짜임을 갈았다: 판 · 영상 분석 · 오른쪽 위 내 프로필.
  testWidgets('위쪽 로고 · 닉네임 · 종목 칩 · 옛 카드들이 없다', (tester) async {
    await _pumpLoggedIn(tester);
    expect(find.text('백성검'), findsNothing);
    expect(find.text('풋살'), findsNothing);
    expect(find.text('야구'), findsNothing);
    for (final gone in const ['용병 매칭', '내 팀', '레슨 · 코치', '내 선수 카드']) {
      expect(find.text(gone), findsNothing, reason: gone);
    }
  });

  testWidgets('종목 목록을 기다리지 않고 바로 그린다', (tester) async {
    tester.view.physicalSize = const Size(1080, 2340);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);
    final container = ProviderContainer();
    addTearDown(container.dispose);

    await tester.pumpWidget(UncontrolledProviderScope(
      container: container,
      child: const MaterialApp(home: HomeScreen()),
    ));
    expect(find.byType(CircularProgressIndicator), findsNothing);
    expect(find.byKey(const Key('home-video-analysis')), findsOneWidget);
    // 컨트롤러 복원 타이머(Mock 300ms)를 흘려보내고 끝낸다.
    await tester.pump(const Duration(milliseconds: 500));
  });

  testWidgets('맨 위에 팀장 · 팀원 · AI 와 내 프로필이 선다', (tester) async {
    await _pumpLoggedIn(tester);
    expect(find.byKey(const Key('home-role-captain')), findsOneWidget);
    expect(find.byKey(const Key('home-role-member')), findsOneWidget);
    expect(find.byKey(const Key('home-ai')), findsOneWidget);
    expect(find.byKey(const Key('home-profile')), findsOneWidget);
    expect(find.text('내 프로필'), findsOneWidget);
  });

  // 2026-09-15 — 스쿼드 판은 위에서 내려오는 판 안에 있다. 들어오면 접혀 있다.
  group('내려오는 판', () {
    double boardWidth(WidgetTester tester) =>
        tester.getSize(find.text('MY SQUAD')).width;

    Future<void> openSheet(WidgetTester tester) async {
      await tester.tap(find.byKey(const Key('home-squad-handle')));
      // 스프링이 앉고(≈1초) 알약이 차례로 떠오를(0.56초) 때까지 흘려보낸다.
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 1500));
      await tester.pump(const Duration(milliseconds: 700));
    }

    testWidgets('접혀 있을 때는 알약이 안 눌리고, 펼치면 눌린다', (tester) async {
      await _pumpLoggedIn(tester);
      await tester.tap(find.byKey(const Key('home-role-member')), warnIfMissed: false);
      await tester.pump();
      expect(find.text('사람을 구하는 팀'), findsNothing);

      await openSheet(tester);
      await tester.tap(find.byKey(const Key('home-role-member')));
      await tester.pump();
      expect(find.text('사람을 구하는 팀'), findsOneWidget);
    });

    testWidgets('접혀 있을 때는 판이 안 눌린다', (tester) async {
      await _pumpLoggedIn(tester);
      await tester.tap(find.byKey(const Key('squad-add-df1')), warnIfMissed: false);
      await tester.pump();
      expect(find.textContaining('선수 넣기'), findsNothing);
    });

    testWidgets('접혔을 때 안내 글 · 내 프로필이 보이고, 펼치면 걷히고, 올리면 돌아온다',
        (tester) async {
      await _pumpLoggedIn(tester);
      const label = '위로 올려 내 팀 만들기';
      final profile = find.byKey(const Key('home-profile'));
      expect(_hintAlpha(tester, label), 1);
      expect(_opacityAbove(tester, profile), 1);
      final profileLeft = tester.getTopLeft(profile).dx;

      await _openSheet(tester);
      expect(_hintAlpha(tester, label), 0);
      expect(_opacityAbove(tester, profile), 0);
      // 오른쪽으로 빠져나갔다.
      expect(tester.getTopLeft(profile).dx, greaterThan(profileLeft));

      await _openSheet(tester); // 손잡이를 다시 누르면 접힌다.
      expect(_hintAlpha(tester, label), 1);
      expect(_opacityAbove(tester, profile), 1);
      expect(tester.getTopLeft(profile).dx, closeTo(profileLeft, 0.5));
    });

    testWidgets('펼치면 팀장 · 팀원은 가운데, AI 는 맨 오른쪽', (tester) async {
      await _pumpLoggedIn(tester);
      await _openSheet(tester);
      final screenW = tester.view.physicalSize.width / tester.view.devicePixelRatio;
      final captain = tester.getRect(find.byKey(const Key('home-role-captain')));
      final member = tester.getRect(find.byKey(const Key('home-role-member')));
      final ai = tester.getRect(find.byKey(const Key('home-ai')));
      final pairCenter = (captain.left + member.right) / 2;
      expect(pairCenter, closeTo(screenW / 2, 2));
      expect(ai.right, closeTo(screenW - 16, 2));
    });

    /* 영상 분석 — 접혔을 때는 사진이 깔린 큰 판, 펼치면 하단 바 바로 위의
       납작한 띠가 된다.

       🔴 **재는 대상을 갈았다 (2026-09-22) — 왜인지 적어 둔다.** 전에는 큰
       판의 **긴 설명**(「…자세를 재고…」)이 있느냐로 갈랐는데, 사용자 요청으로
       그 설명을 통째로 지웠다(「사진 안에 긴 내용들 다 삭제」). 지금 큰 판에만
       있는 것은 **「영상 분석 시작하기」 알약**이라 그것으로 잰다.

       🔴 **`findsNothing` 이 아니라 투명도로 잰다** — 알약은 띠가 돼도 트리에
       남고 [Opacity] 가 0 이 될 뿐이다. */
    testWidgets('펼치면 영상 분석이 납작한 띠로 접혀 든다', (tester) async {
      await _pumpLoggedIn(tester);
      final panel = find.byKey(const Key('home-video-analysis'));
      final start = find.byKey(const Key('home-video-start'));
      final big = tester.getRect(panel);
      expect(big.height, greaterThan(150));
      expect(_opacityAbove(tester, start), 1);

      await _openSheet(tester);
      final flat = tester.getRect(panel);
      expect(flat.height, closeTo(56, 1));
      // 바닥은 그대로다 — 위가 내려와 납작해진다.
      expect(flat.bottom, closeTo(big.bottom, 1));
      expect(_opacityAbove(tester, start), 0);

      await _openSheet(tester); // 다시 접으면 큰 판으로 돌아온다.
      expect(tester.getRect(panel).height, closeTo(big.height, 1));
      expect(_opacityAbove(tester, start), 1);
    });

    /* 🔴 **`SUPER`/`SUB` 가 양옆으로 나가던 시험을 지웠다 (2026-09-23).**
       그 순백 YatraOne 워드마크 자체가 없어졌다 — 하단 바에 있던 `SUPERSUB`
       로고를 화면 맨 위로 올리면서 한 화면에 둘이던 것을 정리했다(사용자
       결정). 지금 그 자리를 지키는 것은 아래 「로고가 화면 맨 위 가운데에
       선다」이다. */

    /* 🔴 **큰 판에서는 판을 눌러도 안 간다 — 알약만 간다**(2026-09-22 사용자
       요청: 「영상분석 시작하기 버튼만 눌리게」). 판 귀퉁이를 눌러 확인한다 —
       가운데를 누르면 그 자리에 알약이 있어서 **눌리든 안 눌리든 통과**한다. */
    testWidgets('큰 판은 알약 밖을 눌러도 안 넘어간다', (tester) async {
      await _pumpLoggedIn(tester);
      final rect = tester.getRect(find.byKey(const Key('home-video-analysis')));
      await tester.tapAt(Offset(rect.left + 12, rect.top + 12));
      await tester.pump(const Duration(milliseconds: 600));

      // 아직 홈이다 — 영상 화면으로 안 갔다.
      expect(find.byKey(const Key('home-video-start')), findsOneWidget);
    });

    // 판을 끌면 손끝 진동을 준다 — 절반을 넘을 때 딸깍, 놓아 붙으러 갈 때 톡.
    testWidgets('판을 끌어내리면 진동이 온다', (tester) async {
      await _pumpLoggedIn(tester);
      final calls = <String?>[];
      tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
        SystemChannels.platform,
        (call) async {
          if (call.method == 'HapticFeedback.vibrate') {
            calls.add(call.arguments as String?);
          }
          return null;
        },
      );
      addTearDown(() => tester.binding.defaultBinaryMessenger
          .setMockMethodCallHandler(SystemChannels.platform, null));

      /* 🔴 **위로 튕긴다 (2026-09-22 정정).** 판이 영상 분석 판 위에 뜬
         카드가 되면서 **위로 늘어난다** — 아래로 튕기면 이제 접는 쪽이다. */
      await tester.fling(
        find.byKey(const Key('home-squad-sheet')),
        const Offset(0, -300),
        1500,
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 1500));

      expect(calls, contains('HapticFeedbackType.selectionClick'));
      expect(calls, contains('HapticFeedbackType.lightImpact'));
    });

    // 알약 셋은 판과 같이 자라지 않고 **판이 다 펼쳐진 뒤** 떠오른다.
    testWidgets('알약은 판이 다 펼쳐진 뒤에 나타난다', (tester) async {
      await _pumpLoggedIn(tester);
      double captainOpacity() => tester
          .widget<Opacity>(find
              .ancestor(
                of: find.byKey(const Key('home-role-captain')),
                matching: find.byType(Opacity),
              )
              .first)
          .opacity;

      expect(captainOpacity(), 0);
      await tester.tap(find.byKey(const Key('home-squad-handle')));
      await tester.pump();
      // 판이 반쯤 내려온 때 — 아직 알약은 없다.
      await tester.pump(const Duration(milliseconds: 80));
      expect(captainOpacity(), 0);

      await tester.pump(const Duration(milliseconds: 1500));
      await tester.pump(const Duration(milliseconds: 700));
      expect(captainOpacity(), 1);
    });

    testWidgets('펼치면 판이 커지고, 끌어올리면 다시 작아진다', (tester) async {
      await _pumpLoggedIn(tester);
      final small = tester.getRect(find.byKey(const ValueKey('squad-seat-gk')));

      /* 🔴 **펼치는 것은 위로 튕기는 것이다 (2026-09-22 정정).**
         아래로 튕기면 접힌다 — 두 번째 fling 이 그쪽이다. */
      await tester.fling(
        find.byKey(const Key('home-squad-sheet')),
        const Offset(0, -300),
        1500,
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 1500));
      await tester.pump(const Duration(milliseconds: 700));
      final big = tester.getRect(find.byKey(const ValueKey('squad-seat-gk')));
      expect(big.height, greaterThan(small.height * 1.3));

      await tester.fling(
        find.byKey(const Key('home-squad-sheet')),
        const Offset(0, 300),
        1500,
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 1500));
      await tester.pump(const Duration(milliseconds: 700));
      final again = tester.getRect(find.byKey(const ValueKey('squad-seat-gk')));
      expect(again.height, closeTo(small.height, 1));
      // 쓰지 않는 도우미 경고를 막는다.
      expect(boardWidth(tester), greaterThan(0));
    });
  });

  /* 🔴 **재는 대상을 갈았다 (2026-09-22).** 전에는 「GK 글자의 아랫변보다
     영상 분석 판이 아래냐」로 쟀다. 지금은 스쿼드 그림이 **접힌 판 안에서
     잘린 채**(보이지도 않는다) 놓여 있어서, 글자의 좌표가 판 밖을 가리킨다 —
     보이는 것과 다른 값을 재게 된다. **두 판의 자리**로 잰다. */
  testWidgets('영상 분석 판은 스쿼드 판 바로 아래에 있다', (tester) async {
    await _pumpLoggedIn(tester);
    final video = tester.getRect(find.byKey(const Key('home-video-analysis')));
    final squad = tester.getRect(find.byKey(const Key('home-squad-sheet')));
    expect(video.top, greaterThan(squad.bottom - 1));
    // 붙어 있다 — 둘 사이가 벌어지면 화면이 성기게 보인다.
    expect(video.top - squad.bottom, lessThan(24));
  });

  group('스쿼드 판', () {
    /* 🔴 **기대를 뒤집었다 (2026-09-21) — 왜인지 적어 둔다.**
       전에는 「내 카드 하나와 빈 자리 넷」이었다. 포메이션의 FW 칸에
       `mine: true` 가 박혀 있어서 **등재하지 않은 사람도 판에 이미 서
       있었기** 때문이다. 웹이 2026-09-16 에 그 규칙을 뒤집었고(내 자리는
       등재했을 때만, 내가 앉힌 칸에) 앱도 따라간다 — 등재가 없으면 판은
       **전부 빈 자리**이고, 「나는 안 뛴다」가 그렇게 표현된다.

       그래서 여기 로그인 대역은 스쿼드가 없는 상태라 카드가 판에 없다.
       실제로 등재가 있을 때의 배치는 `seats_from_squad_test.dart` 가 잡는다. */
    testWidgets('처음은 5:5 — 서버 스쿼드의 팀원이 자리에 앉는다', (tester) async {
      await _pumpLoggedIn(tester);
      expect(find.text('MY SQUAD'), findsOneWidget);
      /* 판에 서는 것 셋:
         - **나** — 자동 착석이 FW 에 앉힌다(아래 「자동 착석」 그룹이 잡는다)
         - **이감독** — GK, 칸이 저장돼 있고 카드 슬러그가 있어 **카드**로
         - **박신입** — MF, 칸이 없어 포지션으로 앉고 슬러그가 없어 **이름표**로
         카드 셋 = 내 카드 + 이감독 + 오른쪽 위 「내 프로필」 입구. */
      expect(find.byType(PlayerCardView), findsNWidgets(3));
      expect(find.text('박신입'), findsOneWidget);
      expect(_blankSeats(), findsNWidgets(2));
      for (final pos in const ['FW', 'DF', 'GK']) {
        expect(find.text(pos), findsOneWidget, reason: pos);
      }
      expect(find.text('MF'), findsNWidgets(2));
    });

    testWidgets('크기를 바꾸면 자리 수가 따라 바뀐다', (tester) async {
      await _pumpLoggedIn(tester);
      await _openSheet(tester);
      await tester.tap(find.byKey(const Key('squad-size-seven')));
      await tester.pump();
      // 앉은 셋은 크기가 바뀌어도 그대로다 — 빈 자리만 는다.
      expect(_blankSeats(), findsNWidgets(4));

      await tester.tap(find.byKey(const Key('squad-size-three')));
      await tester.pump();
      // 3:3 은 자리가 셋뿐이라 꽉 찬다.
      expect(_blankSeats(), findsNothing);
    });

    /* 🔴 **이 회차에 빠져 있던 것**(사용자 지적). 웹은 「카드를 만들면 FW 에
       먼저 앉힌다」인데 앱에는 그 흐름이 통째로 없었다 — 배치 함수는 등재를
       그릴 뿐 만들지 않는다. 자리를 고르는 규칙 자체는 `auto_seat_test.dart` 가
       잡고, 여기서는 **홈이 실제로 그것을 서버에 남기는지**를 본다. */
    testWidgets('자동 착석 — 카드가 있으면 FW 에 앉는다', (tester) async {
      final container = await _pumpLoggedIn(tester);
      final me = container.read(sessionControllerProvider);
      final teamId = (me as SessionLoggedIn).user.ownedTeamId!;

      /* 🔴 **리포지토리를 직접 await 하지 않는다** — Mock 의 300ms 지연을
         가짜 시계가 안 흘려 영영 안 끝난다(`flutter/CLAUDE.md` 의 그 함정).
         provider 가 이미 받아 둔 값을 **동기로** 읽는다. */
      final squad = container.read(squadProvider(teamId)).value;
      final mine = squad!.members
          .where((m) => m.cardPublicSlug == 'baek-seonggeom-3a71')
          .toList();

      expect(mine, hasLength(1), reason: '내 등재가 서버에 남아야 한다');
      expect(mine.single.gridCol, 1);
      expect(mine.single.gridRow, 0); // FW 줄
      expect(mine.single.positionCode, 'FW');
    });

    testWidgets('빈 자리를 누르면 준비 중 안내가 뜬다', (tester) async {
      await _pumpLoggedIn(tester);
      await _openSheet(tester);
      // 🔴 FW 는 자동 착석이, GK 는 이감독이 앉았다 — 남은 빈 자리를 고른다.
      await tester.tap(find.byKey(const Key('squad-add-df1')));
      await tester.pump();
      expect(find.textContaining('선수 넣기'), findsOneWidget);
    });

    testWidgets('팀원을 고르면 판 자리에 팀 목록 자리가 선다', (tester) async {
      await _pumpLoggedIn(tester);
      // 알약은 판을 펼쳐야 눌린다.
      await tester.tap(find.byKey(const Key('home-squad-handle')));
      // 스프링이 앉고(≈1초) 알약이 차례로 떠오를(0.56초) 때까지 흘려보낸다.
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 1500));
      await tester.pump(const Duration(milliseconds: 700));
      await tester.tap(find.byKey(const Key('home-role-member')));
      await tester.pump();
      expect(find.text('MY SQUAD'), findsNothing);
      expect(find.text('사람을 구하는 팀'), findsOneWidget);

      await tester.tap(find.byKey(const Key('home-role-captain')));
      await tester.pump();
      expect(find.text('MY SQUAD'), findsOneWidget);
    });
  });

  /* 흰 판 · 알약 셋 — 2026-09-23 사용자 요청(「스쿼드판이랑 영상분석 판 아래에
     흰색 판 하나」 · 「그 스쿼드판 위에 3개 가로로 나란히 알약 버튼」). */
  group('흰 판 · 지름길 알약 셋', () {
    Finder whiteSheet() => find.byKey(const Key('home-white-sheet'));

    testWidgets('흰 판이 알약 줄과 판 둘을 다 감싼다', (tester) async {
      await _pumpLoggedIn(tester);
      final white = tester.getRect(whiteSheet());
      final squad = tester.getRect(find.byKey(const Key('home-squad-sheet')));
      final video = tester.getRect(find.byKey(const Key('home-video-analysis')));
      final pills = tester.getRect(find.byKey(const Key('home-shortcut-market')));

      for (final (name, r) in [('스쿼드', squad), ('영상 분석', video), ('알약', pills)]) {
        expect(white.top, lessThanOrEqualTo(r.top), reason: '$name 윗변');
        expect(white.bottom, greaterThanOrEqualTo(r.bottom), reason: '$name 아랫변');
        expect(white.left, lessThanOrEqualTo(r.left), reason: '$name 왼변');
        expect(white.right, greaterThanOrEqualTo(r.right), reason: '$name 오른변');
      }
    });

    /* 🔴 **흰 판은 손짓을 안 받는다.** 판 둘보다 뒤에 있지만 겹치는 자리가
       넓어서, 손짓을 받으면 판 가장자리·알약이 먹힌다. */
    testWidgets('흰 판은 손짓을 안 받는다', (tester) async {
      await _pumpLoggedIn(tester);
      expect(
        find.ancestor(of: whiteSheet(), matching: find.byType(IgnorePointer)),
        findsWidgets,
      );
    });

    testWidgets('알약 셋이 서고, 누르면 준비 중 안내가 뜬다', (tester) async {
      await _pumpLoggedIn(tester);
      for (final label in const ['레슨 · 상점', '경기장 예약', '알림']) {
        expect(find.text(label), findsOneWidget, reason: label);
      }
      // 가로로 나란히 — 셋의 윗변이 같다.
      final tops = const ['market', 'venue', 'alarm']
          .map((k) => tester.getRect(find.byKey(Key('home-shortcut-$k'))).top)
          .toList();
      expect(tops[1], closeTo(tops[0], 0.5));
      expect(tops[2], closeTo(tops[0], 0.5));

      await tester.tap(find.byKey(const Key('home-shortcut-venue')));
      await tester.pump();
      expect(find.textContaining('경기장 예약 — 준비 중'), findsOneWidget);
    });

    /* 🔴 **제자리에서 걷힌다**(2026-09-23 정정). 한 번 오른쪽 화면 밖으로
       미는 것으로 만들었다가 사용자가 되돌렸다 — 「사라지는 게 스쿼드판
       올라갈 때 다 보이니까 눈아프다」. ⛔ 옆으로 미는 것을 되살리지 말 것. */
    testWidgets('펼치면 알약이 제자리에서 걷히고, 접으면 돌아온다', (tester) async {
      await _pumpLoggedIn(tester);
      Rect at(String k) =>
          tester.getRect(find.byKey(Key('home-shortcut-$k')));
      const keys = ['market', 'venue', 'alarm'];
      final home = {for (final k in keys) k: at(k)};

      for (final k in keys) {
        expect(_opacityAbove(tester, find.byKey(Key('home-shortcut-$k'))), 1,
            reason: k);
      }

      await _openSheet(tester);
      for (final k in keys) {
        expect(_opacityAbove(tester, find.byKey(Key('home-shortcut-$k'))), 0,
            reason: '$k 걷혔다');
        // 🔴 **자리는 그대로다** — 걷히는 것이지 나가는 것이 아니다.
        expect(at(k).left, closeTo(home[k]!.left, 0.5), reason: '$k 제자리');
      }

      await _openSheet(tester);
      for (final k in keys) {
        expect(_opacityAbove(tester, find.byKey(Key('home-shortcut-$k'))), 1,
            reason: '$k 돌아왔다');
      }
    });

    /* 🔴 **오른쪽 것이 먼저 걷힌다.**
       🔴 **돌아오는 순서는 따로 안 잡는다** — 걷히는 정도가 판 진행도 하나의
       함수라, 접으면 시간이 되감기며 저절로 왼쪽(레슨 · 상점)부터 돌아온다.
       그 성질은 위 시험의 「접으면 돌아온다」가 지킨다. */
    testWidgets('걷히는 순서는 오른쪽부터다', (tester) async {
      await _pumpLoggedIn(tester);
      double alpha(String k) =>
          _opacityAbove(tester, find.byKey(Key('home-shortcut-$k')));

      /* 🔴 **손가락을 든 채로 중간까지만 끈다.** 손잡이를 눌러 스프링에
         맡기면 **한 프레임 만에 셋이 다 걷혀** 순서를 못 잰다. */
      final g = await tester.startGesture(
        tester.getCenter(find.byKey(const Key('home-squad-sheet'))),
      );
      await g.moveBy(const Offset(0, -60));
      await tester.pump();

      expect(alpha('alarm'), lessThan(alpha('venue')), reason: '알림이 앞선다');
      expect(alpha('venue'), lessThanOrEqualTo(alpha('market')),
          reason: '경기장이 레슨보다 앞선다');
      expect(alpha('alarm'), lessThan(1), reason: '적어도 하나는 걷히기 시작했다');

      await g.up();
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 1500));
      await tester.pump(const Duration(milliseconds: 700));
    });

    /* 로고는 **화면 위 바깥으로** 나간다(같은 요청). */
    testWidgets('펼치면 로고가 화면 위로 나가고, 접으면 돌아온다', (tester) async {
      await _pumpLoggedIn(tester);
      final brand = find.byKey(const Key('home-brand'));
      final top0 = tester.getRect(brand).top;

      await _openSheet(tester);
      expect(tester.getRect(brand).bottom, lessThanOrEqualTo(0));

      await _openSheet(tester);
      expect(tester.getRect(brand).top, closeTo(top0, 1));
    });
  });

  /* 🔴 **아무 단추도 아니다**(2026-09-23 사용자 요청). 눌리면 홈에서 홈으로
     가는 길이 둘이 되고, 그 자리는 이제 하단 바의 홈 아이콘이 맡는다. */
  testWidgets('로고가 화면 맨 위 가운데에 서고, 안 눌린다', (tester) async {
    await _pumpLoggedIn(tester);
    final logo = find.byKey(const Key('home-brand'));
    expect(logo, findsOneWidget);

    final r = tester.getRect(logo);
    final screenW = tester.view.physicalSize.width / tester.view.devicePixelRatio;
    expect(r.center.dx, closeTo(screenW / 2, 1));
    expect(r.top, lessThan(120));

    expect(
      find.ancestor(of: logo, matching: find.byType(IgnorePointer)),
      findsWidgets,
    );
  });

  /* 🔴 **앉고 2초 뒤에 흰색으로 물든다**(2026-09-23 사용자 요청).
     기다리는 시간을 「홈이 지어진 때」가 아니라 **`kBrandSettled`** 부터 재는 것이
     이 기능의 핵심이다 — 인트로가 도는 동안 홈은 이미 그 아래에 지어져
     있어서, 화면이 뜨는 대로 재면 로고가 날아오기 전에 흰색이 된다.

     🔴 **`_pumpLoggedIn` 을 쓰지 않는다** — 그 도우미는 목업 지연을 흘리느라
     가짜 시계를 2초 넘게 밀어서, 시험이 시작하자마자 **이미 흰색**을 본다.
     여기서는 시계를 직접 몬다. */
  testWidgets('로고가 1초 뒤 초록에서 흰색으로 물든다', (tester) async {
    tester.view.physicalSize = const Size(1080, 2340);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);
    final container = ProviderContainer();
    addTearDown(container.dispose);

    await tester.pumpWidget(UncontrolledProviderScope(
      container: container,
      child: const MaterialApp(home: HomeScreen()),
    ));

    Color colorNow() => tester
        .widget<Text>(find.descendant(
          of: find.byKey(const Key('home-brand')),
          matching: find.byType(Text),
        ))
        .style!
        .color!;

    expect(colorNow(), AppTheme.seed, reason: '앉자마자는 초록이다');

    // 1초가 되기 전에는 그대로다.
    await tester.pump(const Duration(milliseconds: 900));
    expect(colorNow(), AppTheme.seed, reason: '1초 전');

    // 1초를 넘겨 물드는 도중 — 초록도 흰색도 아니다.
    await tester.pump(const Duration(milliseconds: 200));
    await tester.pump(const Duration(milliseconds: 550));
    final mid = colorNow();
    expect(mid, isNot(AppTheme.seed), reason: '물드는 중');
    expect(mid, isNot(Colors.white), reason: '물드는 중');

    await tester.pump(const Duration(milliseconds: 700));
    expect(colorNow(), Colors.white, reason: '다 물들면 흰색');

    // 컨트롤러 복원 타이머(Mock 300ms)를 흘려보내고 끝낸다.
    await tester.pump(const Duration(milliseconds: 500));
  });

  /* 화면 왼쪽 위 인사말(2026-09-23 사용자 요청 + 레퍼런스). */
  testWidgets('왼쪽 위에 흔드는 손과 인사말이 선다', (tester) async {
    await _pumpLoggedIn(tester);
    final greet = find.textContaining('안녕하세요');
    expect(greet, findsOneWidget);
    /* 🔴 **닉네임은 다음 줄이다**(2026-09-24 사용자 요청: 「안녕하세요, 다음에
       나오는 닉네임은 다음줄로 내려버리자. 길 수도 있으니까」). 한 덩이
       문자열(`'안녕하세요, 백성검 님'`)로 찾으면 **아무것도 못 찾는다.** */
    expect(find.text('안녕하세요,'), findsOneWidget);
    expect(find.text('백성검 님'), findsOneWidget);

    // 왼쪽 위다 — 화면 왼쪽 절반, 위쪽 1/4 안.
    final r = tester.getRect(greet);
    final view = tester.view;
    expect(r.left, lessThan(view.physicalSize.width / view.devicePixelRatio / 2));
    expect(r.top, lessThan(view.physicalSize.height / view.devicePixelRatio / 4));

    /* 🔴 **번들한 굵기가 Black 하나뿐**이라 다른 값을 주면 엔진이 가짜로
       굵게 그려 획이 뭉갠다 — 글꼴과 굵기를 함께 잡아 둔다. */
    final style = tester.widget<Text>(greet).style!;
    expect(style.fontFamily, 'PyeojinGothic');
    expect(style.fontWeight, FontWeight.w900);
  });

  /* 🔴 **인사말은 로고를 안 기다리고 왼쪽 밖에서 들어온다. 흔들기만 기다린다**
     (2026-09-24 사용자 요청: 「글자랑 아이콘 supersub 도착할 때까지 안 나오는
     거 하지 말고 처음부터 왼쪽 밖에서 들어오게 하고, 도착하면 그때 손 흔드는
     애니메이션 나오게 해줘」).

     ⚠️ **2026-09-23 에는 반대였다** — 로고가 앉을 때까지 **안 보였다가**
     스며들었다. 되살리지 말 것. */
  testWidgets('인사말은 로고를 안 기다리고 왼쪽 밖에서 들어온다', (tester) async {
    kBrandSettled.value = false;
    addTearDown(() => kBrandSettled.value = true);

    await _pumpLoggedIn(tester, device: true);
    final greet = find.text('안녕하세요,');

    // 🔴 로고가 아직 안 앉았는데도 **제자리에 다 들어와 있다**.
    expect(tester.getRect(greet).left, closeTo(_kGreetLeft, 1));

    // 🔴 그런데 손은 아직 안 흔든다 — 로고를 기다린다.
    expect(_handAngle(tester), 0, reason: '아직 안 앉았다');

    // 로고가 앉으면 그때 흔든다.
    kBrandSettled.value = true;
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));
    expect(_handAngle(tester), isNot(0), reason: '앉으면 흔든다');

    // 흔들기가 끝나면 손이 제자리로 내려앉는다(진폭이 잦아든다).
    await tester.pump(const Duration(milliseconds: 1700));
    expect(_handAngle(tester), closeTo(0, 0.001), reason: '잦아들어 멎는다');
  });

  /* 들어오는 동작 자체 — 첫 프레임에는 **화면 왼쪽 밖**에 있다. */
  testWidgets('인사말이 화면 왼쪽 밖에서 출발한다', (tester) async {
    await _pumpLoggedIn(tester, device: true, settle: false);
    expect(tester.getRect(find.text('안녕하세요,')).right, lessThan(0),
        reason: '첫 프레임에는 화면 밖 왼쪽');

    await tester.pump(const Duration(milliseconds: 800));
    expect(tester.getRect(find.text('안녕하세요,')).left,
        closeTo(_kGreetLeft, 1));
    await tester.pump(const Duration(milliseconds: 1900));
  });

  /* 🔴 **닉네임이 없으면 줄을 아예 안 세운다** — 「안녕하세요, 님」처럼 이름만
     빠진 줄이 한 번 떴다 바뀌면 그것이 더 눈에 띈다. */
  testWidgets('로그인 전에는 인사말이 없다', (tester) async {
    tester.view.physicalSize = const Size(1080, 2340);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);
    final container = ProviderContainer();
    addTearDown(container.dispose);

    await tester.pumpWidget(UncontrolledProviderScope(
      container: container,
      child: const MaterialApp(home: HomeScreen()),
    ));
    expect(find.textContaining('안녕하세요'), findsNothing);
    await tester.pump(const Duration(milliseconds: 500));
  });

  /* 🔴 **소개 두 줄이 있던 자리에 공개 영상 줄이 선다**(2026-09-24 사용자
     요청: 「그 글자를 없애고, 거기에 우리 실제로 업로드된 영상들 나오게」).
     ⛔ 그 두 줄을 되살리지 말 것 — 아래가 그것도 함께 지킨다. */
  testWidgets('소개 두 줄이 없고, 그 자리에 영상 줄이 선다', (tester) async {
    await _pumpLoggedIn(tester, device: true);

    expect(find.text('함께 뛸 팀을 만들고,'), findsNothing);
    expect(find.text('영상으로 실력을 증명하세요.'), findsNothing);

    final strip = find.byType(HomeVideoStrip);
    expect(strip, findsOneWidget);

    // 다크 판 **아래**, 흰 판 **위**다.
    final r = tester.getRect(strip);
    final panel = tester.getRect(find.byKey(const Key('home-top-panel')));
    final white = tester.getRect(find.byKey(const Key('home-white-sheet')));
    expect(r.top, greaterThanOrEqualTo(panel.bottom));
    expect(r.bottom, lessThanOrEqualTo(white.top));
    expect(r.height, greaterThan(60), reason: '카드가 설 만한 높이는 된다');
  });

  /* 🔴 **맨 위 다크 판**(2026-09-24 사용자 요청 + 레퍼런스: 「내 프로필 글자
     아래로 … 이 색상으로 판 하나 주자」). 판이 담는 것은 **인사말과 「내
     프로필」까지만**이고, 소개 두 줄은 판 **밖 아래**에 남는다. */
  testWidgets('맨 위 다크 판이 인사말과 「내 프로필」을 덮는다', (tester) async {
    await _pumpLoggedIn(tester, device: true);
    final panel = find.byKey(const Key('home-top-panel'));
    expect(panel, findsOneWidget);

    final p = tester.getRect(panel);
    final view = tester.view;
    final screenW = view.physicalSize.width / view.devicePixelRatio;

    // 화면 맨 위에서 좌우 끝까지 — 흰 판과 같은 방식이다.
    expect(p.top, 0);
    expect(p.left, 0);
    expect(p.right, screenW);

    // 인사말 두 줄과 「내 프로필」이 **판 안**에 든다.
    for (final inside in [
      find.text('안녕하세요,'),
      find.text('백성검 님'),
      find.text('내 프로필'),
    ]) {
      final r = tester.getRect(inside);
      expect(p.contains(r.topLeft), isTrue, reason: '$inside 이 판 밖이다');
      expect(p.contains(r.bottomRight), isTrue, reason: '$inside 이 판 밖이다');
    }

    /* 🔴 **소개 두 줄이 들어설 자리가 판 아래에 남아 있다** — 사용자가 자리를
       갈랐다(「그 판을 함께 내 프로필 아래쪽으로 해줘. 함께 뛸 팀을 만들고
       여기까지 하지 말고」). 판이 그 자리를 먹으면 어두운 글자가 어두운 판에
       얹혀 **그대로 사라진다.**

       🔴 **렌더된 글자 상자를 재지 않는다 — 두 번 속았다.** 그 줄은 실기기
       폭에 **간신히** 들어가서, 시험 환경의 글꼴 지표가 조금만 달라도 한 줄이
       더 접히고 상자가 통째로 위로 올라온다(같은 폭·dpr 로 맞춰도 그랬다).
       그래서 **자리를 계산해서** 잰다 — 소개 두 줄은 흰 판 윗변에서 10 위에
       매달린 **2줄(35 × 1.25 × 2 = 87.5)** 덩이다.

       실기기 실측(2026-09-24): 판 아랫변 225.94 · 소개 두 줄 윗변 239.74 —
       **13.8 여유.** 아래 단언이 그 여유를 지킨다. */
    const taglineBlockH = 35 * 1.25 * 2;
    const taglineGap = 10;
    final white = tester.getRect(find.byKey(const Key('home-white-sheet')));
    expect(p.bottom, lessThan(white.top - taglineGap - taglineBlockH));

    // 판 면은 어둡다 — 안의 흰 글자가 사는 근거다.
    final deco =
        tester.widget<DecoratedBox>(panel).decoration as BoxDecoration;
    expect(deco.color!.computeLuminance(), lessThan(0.05));
  });

  /* 🔴 **닉네임이 길어도 「내 프로필」을 안 침범한다** — 인사말 칸을 그 앞에서
     끊어 두고 넘치면 줄을 바꾼다. 목업 닉네임이 짧아 글자로는 못 재므로
     **칸 자체의 오른쪽 끝**을 잰다(칸은 좌우가 묶여 있어 닉네임 길이와 무관하다). */
  testWidgets('인사말 칸은 「내 프로필」 앞에서 끝난다', (tester) async {
    await _pumpLoggedIn(tester);
    final band = tester.getRect(find.byKey(const Key('home-greeting')));
    final profile = tester.getRect(find.text('내 프로필'));
    expect(band.right, lessThanOrEqualTo(profile.left));
  });

  /* 🔴 **바탕이 밝아졌다**(2026-09-24 사용자 요청 + 색 견본). 판 안의 흰
     글자가 사는 근거는 그 위가 다크 판이라는 것뿐이다.
     ⚠️ 같은 날 **판 밖의 어두운 글자**(소개 두 줄)도 함께 봤는데, 그 두 줄이
     영상 줄로 바뀌면서 **판 밖에 글자가 하나도 안 남았다.** */
  testWidgets('바탕은 라이트그레이고, 판 안의 글자는 희다', (tester) async {
    expect(ScreenTint.mintBase, const Color(0xFFE4E9E7));

    await _pumpLoggedIn(tester);
    for (final t in [find.text('안녕하세요,'), find.text('백성검 님')]) {
      expect(tester.widget<Text>(t).style!.color, const Color(0xFFFFFFFF),
          reason: '판 안: $t');
    }
  });

  testWidgets('바 메뉴를 열면 로그아웃 칸이 선다', (tester) async {
    await _pumpLoggedIn(tester);
    // 닫혀 있을 때는 아무 칸도 세우지 않는다.
    expect(find.byKey(const Key('barmenu-logout')), findsNothing);

    await tester.tap(find.byKey(const Key('navbar-icon-menu')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));

    expect(find.byKey(const Key('barmenu-logout')), findsOneWidget);
    // 로그인·로그아웃은 함께 설 수 없다.
    expect(find.byKey(const Key('barmenu-login')), findsNothing);
  });

  testWidgets('바 메뉴의 로그아웃으로 세션이 끝난다', (tester) async {
    final container = await _pumpLoggedIn(tester);

    await tester.tap(find.byKey(const Key('navbar-icon-menu')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 500));
    await tester.tap(find.byKey(const Key('barmenu-logout')));
    await tester.pump(const Duration(milliseconds: 500));

    expect(container.read(sessionControllerProvider), isA<SessionLoggedOut>());

    /* 🔴 로그아웃하면 카드·스쿼드 provider 가 **다시 돈다**(보는 사람이
       바뀌었으니 당연하다). 그 Mock 지연을 흘려보내지 않으면 시험이
       「트리를 버린 뒤에도 타이머가 남았다」로 깨진다 — 화면 잘못이 아니다. */
    for (var i = 0; i < 3; i += 1) {
      await tester.pump(const Duration(milliseconds: 500));
    }
  });
}
