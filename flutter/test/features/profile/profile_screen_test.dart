import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/auth/data/auth_providers.dart';
import 'package:super_sub/features/auth/data/auth_repository_mock.dart';
import 'package:super_sub/features/auth/presentation/session_controller.dart';
import 'package:super_sub/core/dev/data_source.dart';
import 'package:super_sub/core/widgets/floating_nav_bar.dart';
import 'package:super_sub/features/profile/presentation/screens/profile_screen.dart';

/// 🔴 **`pumpAndSettle` 을 안 쓴다 (2026-09-22).** 프로필 배경의 빛무리가
/// **영영 도는 애니메이션**이라(`AnimatedAuroraBackground`) 안 멎고 10분
/// 타임아웃까지 간다 — `flutter/CLAUDE.md` 의 그 함정이다.
///
/// 🔴 **여러 프레임으로 나눠 흘린다.** 한 번에 크게 흘리면 바텀시트가 올라오는
/// 길목에서 멈춰 **단추가 화면 밖에 있다**(`tap` 이 빗나간다). 라우트 연출은
/// 프레임마다 나아간다.
Future<void> _settle(WidgetTester tester) async {
  for (var i = 0; i < 8; i += 1) {
    await tester.pump(const Duration(milliseconds: 250));
  }
}

/// 🔴 **폰 세로 화면이라 아래 칸은 화면 밖이다** — 웹은 좌우 두 단인데
/// 여기서는 한 줄로 쌓아서(이식 지침 §2-2) 「정보」부터가 스크롤 아래에 있다.
/// 카드가 화면의 첫 얼굴이 되면서(2026-09-22) 더 내려갔다. 찾기 전에 끌어 올린다.
Future<void> scrollTo(WidgetTester tester, Finder target) async {
  await tester.scrollUntilVisible(
    target,
    200,
    scrollable: find.byType(Scrollable).first,
  );
  await _settle(tester);
}

Future<ProviderContainer> _pump(WidgetTester tester, String userId) async {
  final container = ProviderContainer(
    overrides: [
      authRepositoryProvider.overrideWith(
        (ref) => MockAuthRepository(ref.watch(mockDbProvider)),
      ),
      /* 🔴 **목업으로 고정한다.** 안 그러면 카드 provider 가 API 구현체를
         잡아 시험이 실제 네트워크를 부른다(홈 시험과 같은 이유). */
      useMockProvider.overrideWith(() => _AlwaysMock()),
    ],
  );
  addTearDown(container.dispose);

  await tester.pumpWidget(UncontrolledProviderScope(
    container: container,
    child: const MaterialApp(home: ProfileScreen()),
  ));

  // MockAuthRepository는 300ms 지연을 흉내낸다. pumpWidget 이전에 이 Future를
  // 직접 await하면 위젯 테스트의 가짜 시계가 아직 흐르지 않아 영원히 끝나지
  // 않는다 — home_screen_test.dart / login_screen_test.dart와 동일한
  // 관용구(먼저 pumpWidget, 그 다음 트리거, pump(500ms)로 소화)를 따른다.
  unawaited(
    container.read(sessionControllerProvider.notifier).loginAs(userId),
  );
  await _settle(tester);
  return container;
}

class _AlwaysMock extends DataSourceController {
  @override
  bool build() => true;
}

void main() {
  testWidgets('닉네임과 이메일을 보여준다', (tester) async {
    await _pump(tester, MockDb.playerId);
    /* 🔴 닉네임이 **둘** 나온다 (2026-09-22) — 카드 아래 큰 글자와 카드
       그림 안의 글자다. 카드가 화면의 첫 얼굴이 되면서 생긴 정상 상태다. */
    expect(find.text('백성검'), findsWidgets);

    await scrollTo(tester, find.text('player@supersub.test'));
    expect(find.text('player@supersub.test'), findsOneWidget);
  });

  testWidgets('바텀시트에서 닉네임을 바꾼다', (tester) async {
    final container = await _pump(tester, MockDb.playerId);

    await tester.tap(find.byKey(const Key('profile-edit')));
    await _settle(tester);

    await tester.enterText(find.byKey(const Key('profile-nickname')), '김교체');
    await tester.tap(find.byKey(const Key('profile-save')));
    // 저장은 리포지토리를 거치므로 300ms 지연이 있다. 저장 중에는
    // 인디케이터가 계속 애니메이션하므로 pumpAndSettle을 쓰면 안 된다.
    await tester.pump(const Duration(milliseconds: 500));
    await _settle(tester);

    final state = container.read(sessionControllerProvider) as SessionLoggedIn;
    expect(state.user.nickname, equals('김교체'));
    expect(find.text('김교체'), findsOneWidget);
  });

  testWidgets('저장하는 동안 진행 표시가 뜨고 버튼이 잠긴다', (tester) async {
    await _pump(tester, MockDb.playerId);

    await tester.tap(find.byKey(const Key('profile-edit')));
    await _settle(tester);

    await tester.enterText(find.byKey(const Key('profile-nickname')), '김교체');
    await tester.tap(find.byKey(const Key('profile-save')));
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    final button = tester.widget<FilledButton>(
      find.byKey(const Key('profile-save')),
    );
    expect(button.onPressed, isNull);

    await tester.pump(const Duration(milliseconds: 500));
    await _settle(tester);
  });

  testWidgets('저장에 실패하면 시트가 닫히지 않고 오류를 보여준다', (tester) async {
    final container = await _pump(tester, MockDb.playerId);

    await tester.tap(find.byKey(const Key('profile-edit')));
    await _settle(tester);

    // 세션이 끊긴 상태에서의 저장 = 서버가 거절하는 경우.
    // 여기서도 Future를 직접 await하면 가짜 시계가 멈춰 있어 끝나지 않는다.
    unawaited(container.read(authRepositoryProvider).logout());
    await tester.pump(const Duration(milliseconds: 500));

    await tester.enterText(find.byKey(const Key('profile-nickname')), '김교체');
    await tester.tap(find.byKey(const Key('profile-save')));
    await tester.pump(const Duration(milliseconds: 500));
    await _settle(tester);

    expect(find.text('로그인이 필요합니다'), findsOneWidget);
    expect(find.byKey(const Key('profile-nickname')), findsOneWidget);
  });

  group('웹에서 옮긴 칸들', () {
    testWidgets('소속 · 정보 · 내 경기 · 계정 칸이 선다', (tester) async {
      await _pump(tester, MockDb.playerId);

      /* 🔴 「내 선수 카드」는 **없앴다** (2026-09-22, 사용자 요청) — 카드
         자체가 무엇인지 말하고 있어서 같은 말을 두 번 하던 자리다. */
      for (final title in const ['소속', '정보', '내 경기', '계정']) {
        await scrollTo(tester, find.text(title));
        expect(find.text(title), findsOneWidget, reason: title);
      }
    });

    testWidgets('소속에 팀 이름과 주장 표식이 뜬다', (tester) async {
      await _pump(tester, MockDb.playerId);

      expect(find.text('번개 풋살클럽'), findsOneWidget);
      // playerId 는 t-thunder 의 주장이다(MockDb 시드).
      expect(find.text('주장'), findsOneWidget);
    });

    testWidgets('팀이 없으면 그렇게 말한다', (tester) async {
      await _pump(tester, MockDb.newbieId);

      expect(find.text('아직 팀이 없습니다'), findsOneWidget);
    });

    /// 🔴 카드가 없으면 「카드 만들기」다 — 카드는 요청할 때 생긴다(계약).
    /// 🔴 **글자가 아니라 동그란 아이콘 단추다** (2026-09-22) — 카드 오른쪽
    /// 위에 붙어서 글자를 넣을 자리가 없다. 뜻은 `tooltip` 이 든다.
    testWidgets('카드가 없으면 만들기 단추가 선다', (tester) async {
      await _pump(tester, MockDb.newbieId);

      expect(find.byKey(const Key('profile-card-edit')), findsOneWidget);
      expect(find.text('카드 만들기'), findsOneWidget);
    });

    testWidgets('카드가 있으면 수정 입구가 선다', (tester) async {
      await _pump(tester, MockDb.playerId);

      expect(find.byKey(const Key('profile-card-edit')), findsOneWidget);
      /* 🔴 **글자다**(2026-09-22) — 아이콘(`tune`)은 무엇을 고치는 단추인지
         안 읽혔다. */
      expect(find.text('카드 수정'), findsOneWidget);
    });

    /// 🔴 **머리칸을 걷으면서 나가는 길이 없어지지 않게** 아래 바를 붙였다
    /// (2026-09-22, 사용자 요청). 로고 알약이 홈이다.
    testWidgets('머리칸 대신 아래 바로 나간다', (tester) async {
      await _pump(tester, MockDb.playerId);

      expect(find.text('MY PROFILE'), findsNothing);
      expect(find.byType(BackButton), findsNothing);
      expect(find.byType(FloatingNavBar), findsOneWidget);
    });

    testWidgets('지인 검색 토글이 서버 값을 따른다', (tester) async {
      final container = await _pump(tester, MockDb.playerId);
      final me = container.read(sessionControllerProvider) as SessionLoggedIn;

      await scrollTo(tester, find.byKey(const Key('profile-searchable')));
      final sw = tester.widget<SwitchListTile>(
        find.byKey(const Key('profile-searchable')),
      );
      expect(sw.value, me.user.isNicknameSearchable);
    });

    testWidgets('토글을 끄면 서버에 남는다', (tester) async {
      final container = await _pump(tester, MockDb.playerId);

      await scrollTo(tester, find.byKey(const Key('profile-searchable')));
      await tester.tap(find.byKey(const Key('profile-searchable')));
      await tester.pump(const Duration(milliseconds: 500));
      await _settle(tester);

      final me = container.read(sessionControllerProvider) as SessionLoggedIn;
      expect(me.user.isNicknameSearchable, isFalse);
    });
  });

  group('팀', () {
    testWidgets('팀 만들기 입구가 늘 있다', (tester) async {
      await _pump(tester, MockDb.newbieId);

      expect(find.byKey(const Key('profile-team-create')), findsOneWidget);
    });

    /// 🔴 **주장에게는 「나가기」를 안 낸다** — 서버가 409 로 막는다(남은
    /// 사람들의 팀이 주인 없이 남는다). 내주면 눌러 보고 거절만 받는다.
    testWidgets('주장에게는 수정·해체가 뜬다', (tester) async {
      await _pump(tester, MockDb.playerId);

      expect(find.byKey(const Key('team-edit-t-thunder')), findsOneWidget);
      expect(find.text('팀 해체'), findsOneWidget);
      expect(find.text('팀 나가기'), findsNothing);
    });

    testWidgets('팀원에게는 나가기만 뜬다', (tester) async {
      await _pump(tester, MockDb.managerId);

      expect(find.byKey(const Key('team-edit-t-thunder')), findsNothing);
      expect(find.text('팀 나가기'), findsOneWidget);
    });

    /// 🔴 되돌릴 수 없어서 곧바로 안 한다.
    testWidgets('해체는 한 번 더 묻는다', (tester) async {
      await _pump(tester, MockDb.playerId);

      await tester.tap(find.byKey(const Key('team-leave-t-thunder')));
      await _settle(tester);

      expect(find.text('정말 해체합니다'), findsOneWidget);
      expect(find.byKey(const Key('team-cancel-t-thunder')), findsOneWidget);
    });

    testWidgets('해체하면 소속에서 사라진다', (tester) async {
      await _pump(tester, MockDb.playerId);

      await tester.tap(find.byKey(const Key('team-leave-t-thunder')));
      await _settle(tester);
      await tester.tap(find.byKey(const Key('team-confirm-t-thunder')));
      await _settle(tester);

      expect(find.text('번개 풋살클럽'), findsNothing);
      expect(find.text('아직 팀이 없습니다'), findsOneWidget);
    });

    /// 🔴 **지역이 목록의 값일 때만 만들어진다** — 자유 입력을 받으면 저장은
    /// 되는데 남의 검색에서 이 팀이 빠진다.
    testWidgets('지역을 안 고르면 만들기가 안 눌린다', (tester) async {
      await _pump(tester, MockDb.newbieId);

      await tester.ensureVisible(find.byKey(const Key('profile-team-create')));
      await _settle(tester);
      await tester.tap(find.byKey(const Key('profile-team-create')));
      await _settle(tester);

      await tester.enterText(find.byKey(const Key('team-name')), '새 팀');
      await _settle(tester);
      expect(
        tester.widget<FilledButton>(find.byKey(const Key('team-save'))).onPressed,
        isNull,
      );

      await tester.enterText(find.byKey(const Key('team-region')), '서울 마포');
      await _settle(tester);
      expect(
        tester.widget<FilledButton>(find.byKey(const Key('team-save'))).onPressed,
        isNull,
        reason: '「서울 마포」는 목록에 없다 — 「서울 마포구」여야 한다',
      );

      await tester.enterText(find.byKey(const Key('team-region')), '서울 마포구');
      await _settle(tester);
      expect(
        tester.widget<FilledButton>(find.byKey(const Key('team-save'))).onPressed,
        isNotNull,
      );
    });

    testWidgets('만들면 소속에 뜬다', (tester) async {
      await _pump(tester, MockDb.newbieId);

      await tester.ensureVisible(find.byKey(const Key('profile-team-create')));
      await _settle(tester);
      await tester.tap(find.byKey(const Key('profile-team-create')));
      await _settle(tester);
      await tester.enterText(find.byKey(const Key('team-name')), '새 팀');
      await tester.enterText(find.byKey(const Key('team-region')), '서울 마포구');
      await _settle(tester);
      /* 🔴 폼이 **제자리에서 펼쳐지므로**(2026-09-22) 저장 단추가 창 밖에
         있을 수 있다 — 누르기 전에 화면 안으로 끌어온다. `ensureVisible` 은
         스크롤 대상을 따로 안 찾아서 여기서는 이쪽이 안전하다. */
      await tester.ensureVisible(find.byKey(const Key('team-save')));
      await _settle(tester);
      await tester.tap(find.byKey(const Key('team-save')));
      await _settle(tester);

      /* 🔴 **위로 되올려서 본다.** `ListView` 는 보이는 것만 짓기 때문에,
         저장 단추까지 내려간 채로 찾으면 「소속」 칸이 **트리에 아예 없어서**
         못 찾는다(화면 잘못이 아니다). */
      await tester.scrollUntilVisible(
        find.text('소속'),
        -200,
        scrollable: find.byType(Scrollable).first,
      );
      await _settle(tester);

      expect(find.text('새 팀'), findsOneWidget);
      // 🔴 만든 사람이 주장으로 들어간다(계약).
      expect(find.text('주장'), findsOneWidget);
    });
  });
}
