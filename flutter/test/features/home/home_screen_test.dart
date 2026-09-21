import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/auth/data/auth_providers.dart';
import 'package:super_sub/features/auth/data/auth_repository_mock.dart';
import 'package:super_sub/core/dev/data_source.dart';
import 'package:super_sub/features/auth/presentation/session_controller.dart';
import 'package:super_sub/features/home/presentation/screens/home_screen.dart';
import 'package:super_sub/features/team/data/squad_providers.dart';
import 'package:super_sub/features/profile/presentation/widgets/player_card_view.dart';

Future<ProviderContainer> _pumpLoggedIn(WidgetTester tester) async {
  // **폰 크기로 돌린다.** 홈은 판 · 영상 분석 · 하단 바가 세로로 꽉 차는
  // 화면이라 기본 800×600 에서는 판이 짜부라진다(app_router_test.dart 와 같다).
  tester.view.physicalSize = const Size(1080, 2340);
  tester.view.devicePixelRatio = 3;
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
  for (var i = 0; i < 3; i += 1) {
    await tester.pump(const Duration(milliseconds: 500));
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

double _opacityAbove(WidgetTester tester, Finder target) => tester
    .widget<Opacity>(
      find.ancestor(of: target, matching: find.byType(Opacity)).first,
    )
    .opacity;

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
      final hint = find.text('아래로 내려 내 팀 만들기');
      final profile = find.byKey(const Key('home-profile'));
      expect(_opacityAbove(tester, hint), 1);
      expect(_opacityAbove(tester, profile), 1);
      final profileLeft = tester.getTopLeft(profile).dx;

      await _openSheet(tester);
      expect(_opacityAbove(tester, hint), 0);
      expect(_opacityAbove(tester, profile), 0);
      // 오른쪽으로 빠져나갔다.
      expect(tester.getTopLeft(profile).dx, greaterThan(profileLeft));

      await _openSheet(tester); // 손잡이를 다시 누르면 접힌다.
      expect(_opacityAbove(tester, hint), 1);
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

    // 영상 분석 — 접혔을 때는 판 아래부터 하단 바 위까지 채우는 큰 판(설명 있음),
    // 펼치면 하단 바 바로 위의 납작한 띠(설명 없음)가 된다.
    testWidgets('펼치면 영상 분석이 납작한 띠로 접혀 든다', (tester) async {
      await _pumpLoggedIn(tester);
      final panel = find.byKey(const Key('home-video-analysis'));
      final big = tester.getRect(panel);
      expect(big.height, greaterThan(150));
      expect(_opacityAbove(tester, find.textContaining('자세를 재고')), 1);

      await _openSheet(tester);
      final flat = tester.getRect(panel);
      expect(flat.height, closeTo(56, 1));
      // 바닥은 그대로다 — 위가 내려와 납작해진다.
      expect(flat.bottom, closeTo(big.bottom, 1));
      expect(find.textContaining('자세를 재고'), findsNothing);

      await _openSheet(tester); // 다시 접으면 큰 판으로 돌아온다.
      expect(tester.getRect(panel).height, closeTo(big.height, 1));
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

      await tester.fling(
        find.byKey(const Key('home-squad-sheet')),
        const Offset(0, 300),
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

      await tester.fling(
        find.byKey(const Key('home-squad-sheet')),
        const Offset(0, 300),
        1500,
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 1500));
      await tester.pump(const Duration(milliseconds: 700));
      final big = tester.getRect(find.byKey(const ValueKey('squad-seat-gk')));
      expect(big.height, greaterThan(small.height * 1.3));

      await tester.fling(
        find.byKey(const Key('home-squad-sheet')),
        const Offset(0, -300),
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

  testWidgets('영상 분석은 판 아래(하단 바 바로 위)에 있다', (tester) async {
    await _pumpLoggedIn(tester);
    final video = tester.getTopLeft(find.byKey(const Key('home-video-analysis')));
    final squad = tester.getBottomLeft(find.text('GK'));
    expect(video.dy, greaterThan(squad.dy));
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
