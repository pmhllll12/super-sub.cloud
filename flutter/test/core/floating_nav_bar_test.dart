import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:material_symbols_icons/symbols.dart';
import 'package:super_sub/core/widgets/floating_nav_bar.dart';
import 'package:super_sub/features/team/data/inbox_providers.dart';
import 'package:super_sub/features/team/data/models/team_invitation.dart';
import 'package:super_sub/features/auth/data/models/app_user.dart';
import 'package:super_sub/features/auth/presentation/session_controller.dart';

/// 🔴 **바가 세션을 스스로 본다** — 맨 오른쪽 칸이 로그인이냐 로그아웃이냐를
/// 가르기 때문이다(2026-09-25 사용자 요청). 그래서 시험도 세션을 준다.
class _Session extends SessionController {
  _Session(this.initial);

  final SessionState initial;

  @override
  SessionState build() => initial;

  /* 🔴 **진짜 로그아웃을 부르지 않는다.** 원본은 `authRepositoryProvider` 를
     읽는데, 이 시험에는 그 덮개가 없어서 **API 구현체가 실제 네트워크를
     친다.** 여기서 지키려는 것은 「바가 로그아웃을 부른다」 하나다. */
  @override
  Future<void> logout() async => state = const SessionLoggedOut();
}

SessionState _loggedIn() => SessionLoggedIn(
      AppUser(
        id: 'u-1',
        email: 'a@b.c',
        nickname: '백성검',
        createdAt: DateTime(2026),
      ),
    );

/* 하단 바 — 2026-09-23 사용자 요청으로 **한 덩이 둥근 막대**가 됐다.
   전에는 윗변에서 로고 자리만 파낸 한 장(`_LogoNotch`)에 `SUPERSUB` 알약이
   **따로 떠 있었다.** 그 둘을 합친 것이 이 파일이 지키는 성질이다. */

Future<ProviderContainer> _pump(
  WidgetTester tester, {
  List<int>? taps,
  SessionState? session,
  int pending = 0,
}) async {
  tester.view.physicalSize = const Size(1080, 2340);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);

  final container = ProviderContainer(
    overrides: [
      sessionControllerProvider
          .overrideWith(() => _Session(session ?? _loggedIn())),
      /* 🔴 **알림함을 고정한다** (2026-09-29, 바가 알림을 직접 맡으면서).
         진짜 [inboxProvider] 는 **15초마다 도는 타이머**를 건다 — 그대로
         두면 시험이 「틀을 버린 뒤에도 타이머가 남았다」로 깨진다. */
      inboxProvider.overrideWith(
        (ref) => Stream.value(
          Inbox(
            invitations: [
              for (var i = 0; i < pending; i++)
                TeamInvitation(
                  id: 'inv-$i',
                  teamId: 't-1',
                  invitedUserId: 'u-1',
                  status: 'pending',
                ),
            ],
          ),
        ),
      ),
    ],
  );
  addTearDown(container.dispose);

  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: MaterialApp(
        home: Scaffold(
          bottomNavigationBar: FloatingNavBar(
            currentIndex: 0,
            onTap: (i) => taps?.add(i),
          ),
        ),
      ),
    ),
  );
  return container;
}

Finder _bar() => find.byKey(const Key('navbar-bar'));

void main() {
  testWidgets('로고와 아이콘이 모두 한 막대 안에 있다', (tester) async {
    await _pump(tester);
    final bar = tester.getRect(_bar());

    for (final key in const [
      'navbar-icon-0',
      'navbar-icon-1',
      'navbar-icon-3',
      'navbar-icon-auth',
    ]) {
      final r = tester.getRect(find.byKey(Key(key)));
      expect(bar.top, lessThanOrEqualTo(r.top), reason: '$key 윗변');
      expect(bar.bottom, greaterThanOrEqualTo(r.bottom), reason: '$key 아랫변');
      expect(bar.left, lessThanOrEqualTo(r.left), reason: '$key 왼변');
      expect(bar.right, greaterThanOrEqualTo(r.right), reason: '$key 오른변');
    }
  });

  /* 🔴 **화면 양끝까지 안 간다**(사용자 요청: 「이 하단바는 양쪽 끝까지 굳이
     안 가도 됨」). 옛 바는 **일부러 화면 밖까지** 나가서 어깨가 안 보였다 —
     되살리지 말 것. */
  testWidgets('막대가 화면 양끝에서 떨어져 있다', (tester) async {
    await _pump(tester);
    final bar = tester.getRect(_bar());
    final screenW = tester.view.physicalSize.width / tester.view.devicePixelRatio;

    expect(bar.left, greaterThan(0));
    expect(bar.right, lessThan(screenW));
    // 양옆이 같아야 막대가 가운데 선다.
    expect(bar.left, closeTo(screenW - bar.right, 0.5));

    /* 🔴 **칸이 하나 줄어든 만큼 좁아졌다** (2026-09-25 사용자 지시: 「5개에서
       4개로 줄였으니 가운데 없애고 그만큼 좌우 폭 줄이자」). 다섯 칸 시절의
       폭은 화면의 78% 였다. */
    expect(bar.width / screenW, lessThan(0.7));
  });

  testWidgets('홈은 0번을 알린다', (tester) async {
    final taps = <int>[];
    await _pump(tester, taps: taps);

    await tester.tap(find.byKey(const Key('navbar-icon-0')));
    expect(taps, [0]);
  });

  /* ⚠️ **2번은 이제 알림 칸이다** (2026-09-29 사용자 지시: 「하단바에서 홈
     버튼 바로 오른쪽에 알림으로 넣어줘」). 걷어낸 「레슨 · 코치」가 쓰던
     번호를 **재사용했다** — 남은 칸(0 홈 · 1 영상 · 3 프로필)의 번호를
     안 건드리려는 것이다([kNavAlarmIndex] 머리말). */
  testWidgets('2번은 알림 칸이다', (tester) async {
    await _pump(tester);

    expect(
      find.byKey(const Key('navbar-icon-$kNavAlarmIndex')),
      findsOneWidget,
    );
  });

  /// 🔴 **로그인 전에는 알림 칸이 없다** — 볼 것도 열 것도 없다.
  testWidgets('로그아웃 상태면 알림 칸이 없다', (tester) async {
    await _pump(tester, session: const SessionLoggedOut());

    expect(
      find.byKey(const Key('navbar-icon-$kNavAlarmIndex')),
      findsNothing,
    );
  });

  /* 🔴 **안 읽은 것이 있으면 빨간 배지가 붙고 종도 빨개진다** (2026-09-29
     사용자 요청). ⛔ 배지만 빨갛게 두지 말 것 — 바를 훑을 때 안 들어온다. */
  testWidgets('안 읽은 것이 있으면 배지와 빨간 종', (tester) async {
    await _pump(tester, pending: 2);
    // 🔴 알림함은 스트림이라 첫 값이 한 프레임 뒤에 온다.
    await tester.pump();

    expect(find.byKey(const Key('navbar-badge')), findsOneWidget);
    expect(find.text('2'), findsOneWidget);

    final bell = tester.widget<Icon>(
      find.descendant(
        of: find.byKey(const Key('navbar-icon-$kNavAlarmIndex')),
        matching: find.byType(Icon),
      ),
    );
    expect(bell.color, kNavBadgeRed);
  });

  testWidgets('안 읽은 것이 없으면 배지가 없다', (tester) async {
    await _pump(tester);

    expect(find.byKey(const Key('navbar-badge')), findsNothing);
  });

  /* 🔴 **맨 오른쪽은 로그인/로그아웃이다** (같은 지시). 로그인했으면
     로그아웃이 보인다. */
  testWidgets('로그인 상태면 로그아웃 아이콘이다', (tester) async {
    await _pump(tester);

    final icon = tester.widget<Icon>(
      find.descendant(
        of: find.byKey(const Key('navbar-icon-auth')),
        matching: find.byType(Icon),
      ),
    );
    expect(icon.icon, Symbols.logout);
  });

  testWidgets('로그아웃 상태면 로그인 아이콘이다', (tester) async {
    await _pump(tester, session: const SessionLoggedOut());

    final icon = tester.widget<Icon>(
      find.descendant(
        of: find.byKey(const Key('navbar-icon-auth')),
        matching: find.byType(Icon),
      ),
    );
    expect(icon.icon, Symbols.login);
  });

  /* 🔴 **누르면 그 자리에서 세션이 끝난다** — 전에는 메뉴를 열어 그 안의
     칸을 눌러야 했다(두 번). */
  testWidgets('누르면 로그아웃된다', (tester) async {
    final c = await _pump(tester);

    await tester.tap(find.byKey(const Key('navbar-icon-auth')));
    await tester.pump();

    expect(c.read(sessionControllerProvider), isA<SessionLoggedOut>());
  });

  /* 칸이 다섯이면 사이는 넷이다 — 레퍼런스가 칸마다 선을 긋는다.
     ⚠️ 알림 칸이 들어오며 넷 → 다섯이 됐다(2026-09-29). */
  testWidgets('칸과 칸 사이마다 세로선이 선다', (tester) async {
    await _pump(tester);
    final dividers = find.byWidgetPredicate(
      (w) =>
          w.key is ValueKey<String> &&
          (w.key! as ValueKey<String>).value.startsWith('navbar-divider'),
    );
    expect(dividers, findsNWidgets(4));

    /* 🔴 **높이가 0 이 아니어야 한다 — 실제로 0 이었다(2026-09-23).**
       [SizedBox] 에 **폭만** 주었더니 [Row] 의 느슨한 세로 제약 아래
       [ColoredBox] 가 높이 0 으로 앉았다. 트리에는 있고 화면에는 없어서,
       개수만 세는 시험은 **통과하면서** 선이 안 보였다. */
    for (final e in dividers.evaluate()) {
      final size = (e.renderObject! as RenderBox).size;
      expect(size.height, greaterThan(0), reason: '세로선 높이');
      expect(size.width, greaterThan(0), reason: '세로선 굵기');
    }
  });
}
