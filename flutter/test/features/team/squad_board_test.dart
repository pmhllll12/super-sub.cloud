import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/profile/presentation/widgets/player_card_view.dart';
import 'package:super_sub/features/card/data/models/player_card.dart';
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

/// 시험용 내 카드 — 슬러그가 곧 씨앗이자 「어느 등재가 나인지」의 열쇠다.
const _myCard = PlayerCard(publicSlug: 'mine', nickname: '나');

void main() {
  testWidgets('서버 스쿼드의 사람이 판에 뜬다', (tester) async {
    await _pump(
      tester,
      SquadBoard(
        myCard: _myCard,
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
        myCard: _myCard,
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
        myCard: _myCard,
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
        myCard: _myCard,
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
        myCard: _myCard,
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
        myCard: _myCard,
        squad: _squad([_m(slug: 'mine', nickname: '나', pos: 'DF', col: 1, row: 2)]),
        onSeatTap: (_) {},
      ),
    );

    expect(find.byType(PlayerCardView), findsOneWidget);
    // 🔴 내 자리에는 이름표가 안 붙는다 — 거기는 내 카드가 그린다.
    expect(find.text('나'), findsNothing);
  });

  /// 🔴 카드가 없으면(myCard == null) 내 자리도 그릴 것이 없다 — 터지지
  /// 않아야 한다.
  testWidgets('카드가 없어도 터지지 않는다', (tester) async {
    await _pump(
      tester,
      SquadBoard(
        myCard: null,
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
          myCard: _myCard,
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
          myCard: _myCard,
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
          myCard: _myCard,
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
          myCard: _myCard,
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

  group('길게 눌러 집고 끌기', () {
    /// 카드를 집어 다른 칸에 놓는다. 좌표는 자리 키로 찾는다.
    Future<void> dragFromTo(
      WidgetTester tester,
      String fromArea,
      String toArea,
    ) async {
      final from = tester.getCenter(find.byKey(ValueKey('squad-seat-$fromArea')));
      final to = tester.getCenter(find.byKey(ValueKey('squad-seat-$toArea')));
      final gesture = await tester.startGesture(from);
      // 길게 눌러야 집힌다.
      await tester.pump(const Duration(milliseconds: 600));
      await gesture.moveTo(to);
      await tester.pump();
      await gesture.up();
      await tester.pump();
    }

    testWidgets('집어서 빈 칸에 놓으면 그 칸을 알려준다', (tester) async {
      String? movedMember;
      String? movedPos;
      int? movedCol;
      int? movedRow;
      await _pump(
        tester,
        SquadBoard(
          myCard: _myCard,
          squad: _squad([_m(id: 'sm-9', nickname: '김철수', pos: 'GK', col: 1, row: 3)]),
          onSeatTap: (_) {},
          onSeatMoved: (id, pos, col, row) {
            movedMember = id;
            movedPos = pos;
            movedCol = col;
            movedRow = row;
          },
        ),
      );

      await dragFromTo(tester, 'gk', 'fw1');

      expect(movedMember, 'sm-9');
      // 🔴 포지션은 **놓인 행**이 정한다 — FW 줄에 놓았으니 GK 가 아니다.
      expect(movedPos, 'FW');
      expect(movedCol, 1);
      expect(movedRow, 0);
    });

    /// 🔴 옮겨도 403 이라 끌린 뒤 되돌아가는 것보다 못 집게 하는 편이 낫다.
    testWidgets('onSeatMoved 가 없으면(주장이 아니면) 아예 안 집힌다', (tester) async {
      await _pump(
        tester,
        SquadBoard(
          myCard: _myCard,
          squad: _squad([_m(id: 'sm-9', nickname: '김철수', pos: 'GK', col: 1, row: 3)]),
          onSeatTap: (_) {},
        ),
      );

      expect(find.byKey(const Key('squad-drag-gk')), findsNothing);
    });

    testWidgets('빈 자리는 못 집는다 — 옮길 등재가 없다', (tester) async {
      await _pump(
        tester,
        SquadBoard(
          myCard: _myCard,
          squad: _squad(const []),
          onSeatTap: (_) {},
          onSeatMoved: (_, _, _, _) {},
        ),
      );

      expect(find.byKey(const Key('squad-drag-fw1')), findsNothing);
    });

    /// 🔴 서로 자리를 바꾸려면 등재 둘을 한 번에 고쳐야 하는데 계약에 그런
    /// 경로가 없다 — 한쪽씩 보내면 중간에 같은 칸에 둘이 된다.
    testWidgets('이미 찬 칸에 놓으면 아무 일도 안 일어난다', (tester) async {
      var called = 0;
      await _pump(
        tester,
        SquadBoard(
          myCard: _myCard,
          squad: _squad([
            _m(id: 'sm-1', slug: 's1', nickname: '가', pos: 'GK', col: 1, row: 3),
            _m(id: 'sm-2', slug: 's2', nickname: '나', pos: 'FW', col: 1, row: 0),
          ]),
          onSeatTap: (_) {},
          onSeatMoved: (_, _, _, _) => called += 1,
        ),
      );

      await dragFromTo(tester, 'gk', 'fw1');

      expect(called, isZero);
    });

    testWidgets('제자리에 놓으면 서버를 안 부른다', (tester) async {
      var called = 0;
      await _pump(
        tester,
        SquadBoard(
          myCard: _myCard,
          squad: _squad([_m(id: 'sm-9', nickname: '김철수', pos: 'GK', col: 1, row: 3)]),
          onSeatTap: (_) {},
          onSeatMoved: (_, _, _, _) => called += 1,
        ),
      );

      await dragFromTo(tester, 'gk', 'gk');

      expect(called, isZero);
    });

    testWidgets('내 카드도 집을 수 있다', (tester) async {
      String? moved;
      await _pump(
        tester,
        SquadBoard(
          myCard: _myCard,
          squad: _squad([
            _m(id: 'sm-me', slug: 'mine', nickname: '나', pos: 'GK', col: 1, row: 3),
          ]),
          onSeatTap: (_) {},
          onSeatMoved: (id, _, _, _) => moved = id,
        ),
      );

      await dragFromTo(tester, 'gk', 'df1');

      expect(moved, 'sm-me');
    });
  });

  group('판에서 빼기 (⊗)', () {
    testWidgets('⊗ 를 누르면 등재 id 와 슬러그를 알려준다', (tester) async {
      String? removedId;
      String? removedSlug;
      await _pump(
        tester,
        SquadBoard(
          myCard: _myCard,
          squad: _squad([
            _m(id: 'sm-9', slug: 's1', nickname: '김철수', col: 0, row: 1),
          ]),
          onSeatTap: (_) {},
          onSeatRemoved: (id, slug) {
            removedId = id;
            removedSlug = slug;
          },
        ),
      );

      await tester.tap(find.byKey(const Key('squad-remove-mf1')));
      await tester.pump();

      expect(removedId, 'sm-9');
      // 🔴 슬러그가 있어야 팀에서도 내보낼 수 있다(주인을 알아내는 열쇠).
      expect(removedSlug, 's1');
    });

    /// 🔴 웹 2026-09-17 사용자 판단 — 내 카드는 옮기기만 한다. 스스로를 빼면
    /// 주장이 팀에서 나가는 셈이라 서버도 409 LAST_OWNER 로 막는다.
    testWidgets('내 카드에는 ⊗ 가 없다', (tester) async {
      await _pump(
        tester,
        SquadBoard(
          myCard: _myCard,
          squad: _squad([
            _m(id: 'sm-me', slug: 'mine', nickname: '나', pos: 'GK', col: 1, row: 3),
          ]),
          onSeatTap: (_) {},
          onSeatRemoved: (_, _) {},
        ),
      );

      expect(find.byKey(const Key('squad-remove-gk')), findsNothing);
    });

    /// 🔴 주장이 아니면 빼도 403 이다 — 그럴 때 웹도 ⊗ 를 안 그린다.
    testWidgets('onSeatRemoved 가 없으면(주장이 아니면) ⊗ 가 없다', (tester) async {
      await _pump(
        tester,
        SquadBoard(
          myCard: _myCard,
          squad: _squad([_m(id: 'sm-9', nickname: '김철수', col: 0, row: 1)]),
          onSeatTap: (_) {},
        ),
      );

      expect(find.byKey(const Key('squad-remove-mf1')), findsNothing);
    });

    testWidgets('빈 자리에는 ⊗ 가 없다', (tester) async {
      await _pump(
        tester,
        SquadBoard(
          myCard: _myCard,
          squad: _squad(const []),
          onSeatTap: (_) {},
          onSeatRemoved: (_, _) {},
        ),
      );

      expect(find.byKey(const Key('squad-remove-fw1')), findsNothing);
    });

    /// 🔴 판의 카드는 폰에서 아주 작다 — 보이는 크기 그대로 두면 손가락으로
    /// 못 누른다.
    testWidgets('⊗ 의 누르는 자리는 40×40 이상이다', (tester) async {
      await _pump(
        tester,
        SquadBoard(
          myCard: _myCard,
          squad: _squad([_m(id: 'sm-9', nickname: '김철수', col: 0, row: 1)]),
          onSeatTap: (_) {},
          onSeatRemoved: (_, _) {},
        ),
      );

      final size = tester.getSize(find.byKey(const Key('squad-remove-mf1')));
      expect(size.width, greaterThanOrEqualTo(40));
      expect(size.height, greaterThanOrEqualTo(40));
    });
  });

  /* 🔴 **사용자가 실기기에서 잡은 것**(2026-09-21). 위젯 시험이 초록이었는데도
     났다 — 시험은 **한 번의 콜백**만 봤고, 「끄는 중에 판이 다시 그려지면」을
     안 봤다. */
  group('끌던 중 판이 바뀌어도', () {
    testWidgets('쥔 카드가 다른 사람으로 안 바뀐다', (tester) async {
      String? movedId;
      // GK 에 '가', FW 에 '나' 가 앉은 판.
      final before = _squad([
        _m(id: 'sm-gk', slug: 's-gk', nickname: '가', pos: 'GK', col: 1, row: 3),
        _m(id: 'sm-fw', slug: 's-fw', nickname: '나', pos: 'FW', col: 1, row: 0),
      ]);
      await _pump(
        tester,
        SquadBoard(
          myCard: _myCard,
          squad: before,
          onSeatTap: (_) {},
          onSeatMoved: (id, _, _, _) => movedId = id,
        ),
      );

      // GK 카드를 집는다.
      final from = tester.getCenter(find.byKey(const ValueKey('squad-seat-gk')));
      final gesture = await tester.startGesture(from);
      await tester.pump(const Duration(milliseconds: 600));

      /* 🔴 **끄는 도중에 판이 바뀐다** — 서버 응답이 늦게 오거나 부모가 다시
         그리는 상황이다. 자리 이름으로 붙들고 있으면 여기서 엉뚱한 카드가
         끌린다(그게 「골키퍼를 옮기면 포워드가 간다」였다). */
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SizedBox(
              height: 700,
              child: SquadBoard(
                myCard: _myCard,
                // 둘의 자리가 뒤바뀐 판이 도착했다.
                squad: _squad([
                  _m(id: 'sm-gk', slug: 's-gk', nickname: '가', pos: 'MF', col: 0, row: 1),
                  _m(id: 'sm-fw', slug: 's-fw', nickname: '나', pos: 'GK', col: 1, row: 3),
                ]),
                onSeatTap: (_) {},
                onSeatMoved: (id, _, _, _) => movedId = id,
              ),
            ),
          ),
        ),
      );
      await tester.pump();

      final to = tester.getCenter(find.byKey(const ValueKey('squad-seat-df1')));
      await gesture.moveTo(to);
      await tester.pump();
      await gesture.up();
      await tester.pump();

      // 🔴 집은 것은 **GK 자리**가 아니라 **그 등재**다.
      expect(movedId, 'sm-gk');
    });
  });

  testWidgets('빈 자리를 누르면 그 자리를 알려준다', (tester) async {
    SquadSlot? tapped;
    await _pump(
      tester,
      SquadBoard(
        myCard: _myCard,
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
