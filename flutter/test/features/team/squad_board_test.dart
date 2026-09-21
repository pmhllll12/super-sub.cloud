import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/profile/presentation/widgets/player_card_view.dart';
import 'package:super_sub/features/team/data/models/squad.dart';
import 'package:super_sub/features/team/presentation/widgets/squad_board.dart';
import 'package:super_sub/features/team/seats_from_squad.dart';

SquadMember _m({
  String id = '1',
  String? slug = 's1',
  String nickname = '김철수',
  String pos = 'MF',
  int? col,
  int? row,
  bool accepted = true,
}) =>
    SquadMember(
      id: id,
      playerCardId: 'card-$id',
      cardPublicSlug: slug,
      nickname: nickname,
      positionCode: pos,
      positionLabel: pos,
      gridCol: col,
      gridRow: row,
      accepted: accepted,
    );

Squad _squad(List<SquadMember> members, {String? formation = '5:5'}) => Squad(
      id: 's',
      teamId: 't',
      publicSlug: 'p',
      formation: formation,
      members: members,
    );

/// 판은 무한 애니메이션이 없으므로 `pump` 로 충분하다 — 🔴 홈과 달리
/// `pumpAndSettle` 을 써도 되지만, 화면마다 다르므로 여기서도 안 쓴다.
Future<void> _pump(WidgetTester tester, Widget board) async {
  tester.view.physicalSize = const Size(1080, 2340);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    MaterialApp(home: Scaffold(body: SizedBox(height: 700, child: board))),
  );
  await tester.pump();
}

Finder _blankSeats() => find.byWidgetPredicate(
      (w) =>
          w.key is ValueKey<String> &&
          (w.key! as ValueKey<String>).value.startsWith('squad-add-'),
    );

void main() {
  testWidgets('서버 스쿼드의 사람이 판에 뜬다', (tester) async {
    await _pump(
      tester,
      SquadBoard(
        cardSeed: 'mine',
        mySlug: 'mine',
        squad: _squad([_m(nickname: '김철수', col: 0, row: 1)]),
        onSeatTap: (_) {},
      ),
    );

    expect(find.text('김철수'), findsOneWidget);
    // 다섯 자리 중 하나가 찼다.
    expect(_blankSeats(), findsNWidgets(4));
  });

  testWidgets('formation 이 서버 값으로 열린다', (tester) async {
    await _pump(
      tester,
      SquadBoard(
        cardSeed: 'mine',
        mySlug: 'mine',
        squad: _squad(const [], formation: '3:3'),
        onSeatTap: (_) {},
      ),
    );

    expect(_blankSeats(), findsNWidgets(3));
  });

  /// ⚠️ 2026-09-18 이전 스쿼드가 전부 null 이다.
  testWidgets('formation 이 null 이면 기본 판(5:5)으로 연다', (tester) async {
    await _pump(
      tester,
      SquadBoard(
        cardSeed: 'mine',
        mySlug: 'mine',
        squad: _squad(const [], formation: null),
        onSeatTap: (_) {},
      ),
    );

    expect(_blankSeats(), findsNWidgets(5));
  });

  /// 🔴 안 그러면 판을 3:3 으로 바꾼 직후 스쿼드가 다시 도착하면서 5:5 로
  /// 되돌아간다.
  testWidgets('사람이 고른 크기가 서버 값을 이긴다', (tester) async {
    await _pump(
      tester,
      SquadBoard(
        cardSeed: 'mine',
        mySlug: 'mine',
        squad: _squad(const [], formation: '5:5'),
        onSeatTap: (_) {},
      ),
    );

    await tester.tap(find.byKey(const Key('squad-size-three')));
    await tester.pump();

    expect(_blankSeats(), findsNWidgets(3));
  });

  testWidgets('등재하지 않았으면 내 카드가 판에 없다', (tester) async {
    await _pump(
      tester,
      SquadBoard(
        cardSeed: 'mine',
        mySlug: 'mine',
        squad: _squad(const []),
        onSeatTap: (_) {},
      ),
    );

    expect(find.byType(PlayerCardView), findsNothing);
    expect(_blankSeats(), findsNWidgets(5));
  });

  testWidgets('등재했으면 내가 앉힌 칸에 내 카드가 선다', (tester) async {
    await _pump(
      tester,
      SquadBoard(
        cardSeed: 'mine',
        mySlug: 'mine',
        squad: _squad([_m(slug: 'mine', nickname: '나', pos: 'DF', col: 1, row: 2)]),
        onSeatTap: (_) {},
      ),
    );

    expect(find.byType(PlayerCardView), findsOneWidget);
    // 🔴 내 자리에는 이름표가 안 붙는다 — 거기는 내 카드가 그린다.
    expect(find.text('나'), findsNothing);
  });

  /// 🔴 카드가 없으면(cardSeed == null) 내 자리도 그릴 것이 없다 — 터지지
  /// 않아야 한다.
  testWidgets('카드가 없어도 터지지 않는다', (tester) async {
    await _pump(
      tester,
      SquadBoard(
        cardSeed: null,
        mySlug: null,
        squad: _squad([_m(nickname: '김철수', col: 0, row: 1)]),
        onSeatTap: (_) {},
      ),
    );

    expect(tester.takeException(), isNull);
    expect(find.text('김철수'), findsOneWidget);
  });

  group('팀원 카드', () {
    testWidgets('카드가 오면 이름표 대신 카드를 그린다', (tester) async {
      await _pump(
        tester,
        SquadBoard(
          cardSeed: 'mine',
          mySlug: 'mine',
          squad: _squad([_m(slug: 's1', nickname: '김철수', col: 0, row: 1)]),
          mateCardBuilder: (slug, width) =>
              PlayerCardView(width: width, seed: slug),
          onSeatTap: (_) {},
        ),
      );

      expect(find.byType(PlayerCardView), findsOneWidget);
      expect(find.text('김철수'), findsNothing);
    });

    /// 🔴 판 전체를 로딩으로 덮지 않는다 — 나머지 자리는 이미 그릴 수 있다.
    testWidgets('카드가 아직 안 왔으면 이름표로 물러난다', (tester) async {
      await _pump(
        tester,
        SquadBoard(
          cardSeed: 'mine',
          mySlug: 'mine',
          squad: _squad([_m(slug: 's1', nickname: '김철수', col: 0, row: 1)]),
          mateCardBuilder: (slug, width) => null,
          onSeatTap: (_) {},
        ),
      );

      expect(find.text('김철수'), findsOneWidget);
    });

    testWidgets('슬러그가 없으면 카드를 부르지 않는다', (tester) async {
      var called = 0;
      await _pump(
        tester,
        SquadBoard(
          cardSeed: 'mine',
          mySlug: 'mine',
          squad: _squad([_m(slug: null, nickname: '김철수', col: 0, row: 1)]),
          mateCardBuilder: (slug, width) {
            called += 1;
            return null;
          },
          onSeatTap: (_) {},
        ),
      );

      expect(called, isZero);
      expect(find.text('김철수'), findsOneWidget);
    });

    testWidgets('수락 대기중인 사람은 흐리게 그린다', (tester) async {
      await _pump(
        tester,
        SquadBoard(
          cardSeed: 'mine',
          mySlug: 'mine',
          squad: _squad([
            _m(nickname: '대기', col: 0, row: 1, accepted: false),
          ]),
          onSeatTap: (_) {},
        ),
      );

      final opacity = tester.widget<Opacity>(
        find
            .ancestor(
              of: find.byKey(const Key('squad-mate-mf1')),
              matching: find.byType(Opacity),
            )
            .first,
      );
      expect(opacity.opacity, lessThan(1));
    });
  });

  testWidgets('빈 자리를 누르면 그 자리를 알려준다', (tester) async {
    SquadSlot? tapped;
    await _pump(
      tester,
      SquadBoard(
        cardSeed: 'mine',
        mySlug: 'mine',
        squad: _squad(const []),
        onSeatTap: (s) => tapped = s,
      ),
    );

    await tester.tap(find.byKey(const Key('squad-add-gk')));
    await tester.pump();

    expect(tapped, isNotNull);
    expect(tapped!.position, 'GK');
  });
}
