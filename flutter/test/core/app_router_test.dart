import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/app.dart';
import 'package:super_sub/core/dev/data_source.dart';
import 'package:super_sub/core/widgets/floating_nav_bar.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/auth/data/auth_providers.dart';
import 'package:super_sub/features/auth/data/auth_repository_mock.dart';
import 'package:super_sub/features/auth/presentation/session_controller.dart';
import 'package:super_sub/features/intro/presentation/intro_gate.dart';

// redirect는 앱의 내비게이션 정책 전체를 담고 있다 — 복원 중, 로그아웃,
// 로그인 화면에 남은 로그인 사용자, 통과. 네 갈래를 모두 착지 화면으로
// 확인한다. 종목은 더 이상 진입 조건이 아니다(홈의 칩으로 옮겼다).
//
// 관용구 주의: Mock은 300ms 지연을 흉내내고 위젯 테스트의 가짜 시계는
// pump로만 흐른다. pumpWidget 전에 Mock Future를 await하면 영원히 끝나지
// 않고, 로딩 인디케이터는 무한 애니메이션이라 pumpAndSettle도 쓰지 않는다
// (home_screen_test.dart의 주석 참고).

/// 🔴 **목업 지연이 줄줄이 걸린다 (2026-09-22).** 로그인이 끝나야 팀을 알고,
/// 팀을 알아야 스쿼드를, 스쿼드가 와야 팀원 카드를 부른다 — 여기에 프로필의
/// 「내 영상」까지 붙어 300ms 가 여러 겹이다. 모자라게 흘리면 「트리를 버린
/// 뒤에도 타이머가 남았다」로 깨지는데 **화면 잘못이 아니다.**
Future<void> _settle(WidgetTester tester) async {
  for (var i = 0; i < 6; i += 1) {
    await tester.pump(const Duration(milliseconds: 400));
  }
}

class _AlwaysMock extends DataSourceController {
  @override
  bool build() => true;
}

Future<ProviderContainer> _pumpApp(WidgetTester tester) async {
  // **폰 크기로 돌린다.** 기본 800×600은 이 앱의 화면보다 훨씬 짧아, 하단
  // 바까지 있는 화면에서 내용이 넘친다.
  tester.view.physicalSize = const Size(1080, 2340);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);

  // 인트로를 끈다 — 켜 두면 3.1초 동안 모든 라우트를 덮어 착지 화면 대신
  // 인트로만 보인다. 인트로 자체는 glitch_intro_screen_test.dart가 본다.
  final container = ProviderContainer(
    overrides: [
      introEnabledProvider.overrideWithValue(false),
      authRepositoryProvider.overrideWith(
        (ref) => MockAuthRepository(ref.watch(mockDbProvider)),
      ),
      /* 🔴 **목업으로 고정한다 (2026-09-22).** 이걸 안 덮으면 카드·스쿼드·영상
         provider 가 API 구현체를 잡아 **시험이 실제 네트워크를 부른다** —
         느리고, 서버 상태에 따라 결과가 흔들리고, 끝나지 않은 연결이 「트리를
         버린 뒤에도 타이머가 남았다」로 터진다. 프로필에 「내 영상」 블록이
         붙으면서 실제로 그렇게 깨져서 드러났다(그전에도 카드가 같은 길로
         나가고 있었다). 교체 지점이 `useMockProvider` 하나라 여기만 덮으면
         전부 따라온다 — `home_screen_test.dart` 와 같은 처리다. */
      useMockProvider.overrideWith(_AlwaysMock.new),
    ],
  );
  addTearDown(container.dispose);

  await tester.pumpWidget(UncontrolledProviderScope(
    container: container,
    child: const SuperSubApp(),
  ));
  return container;
}

Future<ProviderContainer> _pumpHome(WidgetTester tester) async {
  final container = await _pumpApp(tester);
  unawaited(
    container.read(sessionControllerProvider.notifier).loginAs(MockDb.playerId),
  );
  await _settle(tester);
  return container;
}

void main() {
  testWidgets('복원이 끝나기 전에는 로그인으로 보내지 않는다', (tester) async {
    await _pumpApp(tester);
    // 첫 프레임의 세션 상태는 SessionUnknown이다. 이때 로그인으로 보내면
    // 세션이 살아 있는 사용자도 매번 로그인 화면을 스친다.
    expect(find.text('로그인'), findsNothing);

    // 복원·종목 조회 타이머를 소화하고 끝낸다.
    await _settle(tester);
  });

  testWidgets('로그아웃 상태면 로그인 화면에 착지한다', (tester) async {
    await _pumpApp(tester);
    await _settle(tester);

    expect(find.text('로그인'), findsWidgets);
  });

  testWidgets('로그인하면 종목을 안 골라도 홈에 착지한다', (tester) async {
    await _pumpHome(tester);

    // 홈은 스쿼드 판과 「영상 분석」 판을 보여 준다.
    expect(find.byKey(const Key('home-video-analysis')), findsOneWidget);
    expect(find.text('로그인'), findsNothing);
  });

  testWidgets('홈에서 로그아웃하면 로그인으로 돌아간다', (tester) async {
    await _pumpHome(tester);

    // 로그아웃은 하단 바 넷째 아이콘에서 열리는 메뉴 안에 있다.
    await tester.tap(find.byKey(const Key('navbar-icon-menu')));
    await tester.pump();
    await _settle(tester);
    await tester.tap(find.byKey(const Key('barmenu-logout')));
    await _settle(tester);

    expect(find.text('로그인'), findsWidgets);
    expect(find.byKey(const Key('home-video-analysis')), findsNothing);
  });

  testWidgets('영상 분석 카드가 자기 화면으로 데려간다', (tester) async {
    await _pumpHome(tester);

    /* 🔴 **판이 아니라 알약을 누른다 (2026-09-22 정정).** 전에는 판 전체가
       단추라 `home-video-analysis` 를 눌렀는데, 이제 큰 판에서 눌리는 것은
       사진 가운데의 「영상 분석 시작하기」 **하나뿐**이다(사용자 요청).
       ⚠️ 판을 눌러도 **지금은 통과한다** — 알약이 마침 판 한가운데라
       `tap` 의 기본 지점이 알약에 떨어지기 때문이다. 그건 우연이라
       기대면 안 된다. */
    await tester.tap(find.byKey(const Key('home-video-start')));
    await _settle(tester);

    expect(find.text('분석할 영상을 골라주세요'), findsOneWidget);

    // 판을 누르면 어디서 가져올지 둘로 펼쳐진다.
    await tester.tap(find.byKey(const Key('video-pick')));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.byKey(const Key('video-pick-camera')), findsOneWidget);
    expect(find.byKey(const Key('video-pick-gallery')), findsOneWidget);
  });

  testWidgets('로그인 상태에서 다른 라우트는 그대로 통과한다', (tester) async {
    await _pumpHome(tester);

    // 「내 프로필」은 홈 카드가 아니라 오른쪽 위 단추다(2026-09-15).
    await tester.tap(find.byKey(const Key('home-profile')));
    await _settle(tester);

    /* redirect 가 개입하지 않고 /profile 에 머무른다.
       🔴 **머리칸을 걷었다 (2026-09-22, 사용자 요청)** — 제목(「MY PROFILE」)도
       뒤로가기도 없다. 카드가 이 화면의 첫 얼굴이고, 그 위에 띠가 하나 더
       있으면 카드가 밀려 내려간다. 착지했는지는 **카드 수정 입구**로 본다. */
    expect(find.byKey(const Key('profile-card-edit')), findsOneWidget);
    expect(find.text('MY PROFILE'), findsNothing);
    /* 🔴 **나가는 길은 아래 바가 맡는다** — 뒤로가기를 걷으면서 길이 하나도
       없어지지 않게 같이 붙인 것이다(로고 알약이 홈). */
    expect(find.byType(FloatingNavBar), findsWidgets);
  });
}
