import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:super_sub/core/mock/mock_db.dart';
import 'package:super_sub/features/auth/data/auth_providers.dart';
import 'package:super_sub/features/auth/data/auth_repository_mock.dart';
import 'package:super_sub/features/auth/presentation/session_controller.dart';
import 'package:super_sub/core/dev/data_source.dart';
import 'package:super_sub/features/profile/presentation/screens/profile_screen.dart';

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
  /* 🔴 **두 번 흘린다 (2026-09-22).** 프로필에 「내 영상」 요약과 카드 색을
     따르는 배경 전환(1.2초)이 붙으면서 지연이 겹쳤다 — 모자라게 흘리면
     「트리를 버린 뒤에도 타이머가 남았다」로 깨지는데 **화면 잘못이 아니다.** */
  await tester.pump(const Duration(milliseconds: 500));
  await tester.pump(const Duration(milliseconds: 1500));
  await tester.pumpAndSettle();
  return container;
}

class _AlwaysMock extends DataSourceController {
  @override
  bool build() => true;
}

void main() {
  testWidgets('닉네임과 이메일을 보여준다', (tester) async {
    await _pump(tester, MockDb.playerId);
    expect(find.text('백성검'), findsOneWidget);
    expect(find.text('player@supersub.test'), findsOneWidget);
  });

  testWidgets('바텀시트에서 닉네임을 바꾼다', (tester) async {
    final container = await _pump(tester, MockDb.playerId);

    await tester.tap(find.byKey(const Key('profile-edit')));
    await tester.pumpAndSettle();

    await tester.enterText(find.byKey(const Key('profile-nickname')), '김교체');
    await tester.tap(find.byKey(const Key('profile-save')));
    // 저장은 리포지토리를 거치므로 300ms 지연이 있다. 저장 중에는
    // 인디케이터가 계속 애니메이션하므로 pumpAndSettle을 쓰면 안 된다.
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pumpAndSettle();

    final state = container.read(sessionControllerProvider) as SessionLoggedIn;
    expect(state.user.nickname, equals('김교체'));
    expect(find.text('김교체'), findsOneWidget);
  });

  testWidgets('저장하는 동안 진행 표시가 뜨고 버튼이 잠긴다', (tester) async {
    await _pump(tester, MockDb.playerId);

    await tester.tap(find.byKey(const Key('profile-edit')));
    await tester.pumpAndSettle();

    await tester.enterText(find.byKey(const Key('profile-nickname')), '김교체');
    await tester.tap(find.byKey(const Key('profile-save')));
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    final button = tester.widget<FilledButton>(
      find.byKey(const Key('profile-save')),
    );
    expect(button.onPressed, isNull);

    await tester.pump(const Duration(milliseconds: 500));
    await tester.pumpAndSettle();
  });

  testWidgets('저장에 실패하면 시트가 닫히지 않고 오류를 보여준다', (tester) async {
    final container = await _pump(tester, MockDb.playerId);

    await tester.tap(find.byKey(const Key('profile-edit')));
    await tester.pumpAndSettle();

    // 세션이 끊긴 상태에서의 저장 = 서버가 거절하는 경우.
    // 여기서도 Future를 직접 await하면 가짜 시계가 멈춰 있어 끝나지 않는다.
    unawaited(container.read(authRepositoryProvider).logout());
    await tester.pump(const Duration(milliseconds: 500));

    await tester.enterText(find.byKey(const Key('profile-nickname')), '김교체');
    await tester.tap(find.byKey(const Key('profile-save')));
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pumpAndSettle();

    expect(find.text('로그인이 필요합니다'), findsOneWidget);
    expect(find.byKey(const Key('profile-nickname')), findsOneWidget);
  });

  /* 🔴 **폰 세로 화면이라 아래 칸은 화면 밖이다** — 웹은 좌우 두 단인데
     여기서는 한 줄로 쌓아서(이식 지침 §2-2) 「계정」이 스크롤 아래에 있다.
     찾기 전에 끌어 올린다. */
  Future<void> scrollTo(WidgetTester tester, Finder target) async {
    await tester.scrollUntilVisible(target, 200, scrollable: find.byType(Scrollable).first);
    await tester.pumpAndSettle();
  }

  group('웹에서 옮긴 칸들', () {
    testWidgets('소속 · 정보 · 내 경기 · 계정 칸이 선다', (tester) async {
      await _pump(tester, MockDb.playerId);

      for (final title in const ['내 선수 카드', '소속', '정보', '내 경기', '계정']) {
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
    testWidgets('카드가 없으면 만들기 단추가 선다', (tester) async {
      await _pump(tester, MockDb.newbieId);

      expect(find.text('카드 만들기'), findsOneWidget);
    });

    testWidgets('카드가 있으면 수정 입구가 선다', (tester) async {
      await _pump(tester, MockDb.playerId);

      expect(find.text('프로필 카드 수정'), findsOneWidget);
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
      await tester.pumpAndSettle();

      final me = container.read(sessionControllerProvider) as SessionLoggedIn;
      expect(me.user.isNicknameSearchable, isFalse);
    });
  });
}
