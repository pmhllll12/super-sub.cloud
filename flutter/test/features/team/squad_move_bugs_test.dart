import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/models/squad.dart';
import 'package:super_sub/features/team/seats_from_squad.dart';

/// 🔴 **사용자가 실기기에서 잡은 것 셋**(2026-09-21):
///
/// 1. 내 카드를 옮기려고 하면 **내 카드가 사라진다**
/// 2. 골키퍼 카드를 다른 데로 옮기면 **포워드 카드가 골키퍼 자리로 간다**
/// 3. 한 번에 안 옮겨지고 **제자리로 갔다가** 옮겨진다
///
/// 위젯 시험이 초록이었는데도 났다 — 시험은 **한 번의 콜백**만 봤고,
/// 「옮긴 뒤 판을 다시 그리면 어떻게 되는가」를 안 봤다.
SquadMember _m({
  required String id,
  String? slug,
  required String nickname,
  required String pos,
  int? col,
  int? row,
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
      accepted: true,
    );

Squad _squad(List<SquadMember> members) => Squad(
      id: 's',
      teamId: 't',
      publicSlug: 'p',
      formation: '5:5',
      members: members,
    );

/// 서버가 등재 하나의 칸·포지션을 바꾼 뒤의 스쿼드.
Squad _afterMove(Squad squad, String memberId, int col, int row) => _squad([
      for (final m in squad.members)
        if (m.id == memberId)
          _m(
            id: m.id,
            slug: m.cardPublicSlug,
            nickname: m.nickname,
            pos: const ['FW', 'MF', 'DF', 'GK'][row],
            col: col,
            row: row,
          )
        else
          m,
    ]);

void main() {
  /// 판 하나에 내 카드(FW)와 남(GK)이 있는 흔한 상태.
  Squad boardWithMeAndGk() => _squad([
        _m(id: 'sm-me', slug: 'mine', nickname: '나', pos: 'FW', col: 1, row: 0),
        _m(id: 'sm-gk', slug: 's-gk', nickname: '골키퍼', pos: 'GK', col: 1, row: 3),
      ]);

  group('버그 1 — 내 카드를 옮기면 사라진다', () {
    test('내 카드를 빈 칸으로 옮겨도 판에 남아 있어야 한다', () {
      final moved = _afterMove(boardWithMeAndGk(), 'sm-me', 1, 2); // DF 자리로

      final seats = seatsFromSquad(moved, SquadSize.five, mySlug: 'mine');

      final mine = seats.slots.where((s) => s.mine).toList();
      expect(mine, hasLength(1), reason: '내 카드가 판에서 사라졌다');
      expect(mine.single.col, 1);
      expect(mine.single.row, 2);
    });

    test('내 카드를 옮겨도 이름표로 바뀌지 않는다', () {
      final moved = _afterMove(boardWithMeAndGk(), 'sm-me', 0, 1);

      final seats = seatsFromSquad(moved, SquadSize.five, mySlug: 'mine');

      expect(seats.mates.values, isNot(contains('나')));
    });
  });

  group('버그 2 — 남을 옮기면 내 카드가 딸려 간다', () {
    test('골키퍼를 옮겨도 내 카드는 제자리다', () {
      final moved = _afterMove(boardWithMeAndGk(), 'sm-gk', 0, 1); // MF 왼쪽으로

      final seats = seatsFromSquad(moved, SquadSize.five, mySlug: 'mine');

      final mine = seats.slots.singleWhere((s) => s.mine);
      expect(mine.col, 1, reason: '내 카드가 딸려 갔다');
      expect(mine.row, 0, reason: '내 카드가 딸려 갔다');
    });

    test('골키퍼를 옮기면 GK 자리는 빈다', () {
      final moved = _afterMove(boardWithMeAndGk(), 'sm-gk', 0, 1);

      final seats = seatsFromSquad(moved, SquadSize.five, mySlug: 'mine');

      // (1,3) 에 앉은 자리가 있으면 안 된다.
      final atGk = seats.slots.where((s) => s.col == 1 && s.row == 3);
      for (final s in atGk) {
        expect(s.mine, isFalse, reason: 'GK 자리에 내 카드가 왔다');
        expect(seats.mates.containsKey(s.area), isFalse,
            reason: 'GK 자리에 남이 남아 있다');
      }
    });

    test('골키퍼가 간 자리에 골키퍼가 있다', () {
      final moved = _afterMove(boardWithMeAndGk(), 'sm-gk', 0, 1);

      final seats = seatsFromSquad(moved, SquadSize.five, mySlug: 'mine');

      final seat = seats.slots.singleWhere(
        (s) => seats.mates[s.area] == '골키퍼',
      );
      expect(seat.col, 0);
      expect(seat.row, 1);
    });
  });

  group('여럿이 얽힌 판', () {
    test('셋이 앉은 판에서 하나를 옮겨도 나머지가 제자리다', () {
      final before = _squad([
        _m(id: 'sm-me', slug: 'mine', nickname: '나', pos: 'FW', col: 1, row: 0),
        _m(id: 'sm-a', slug: 's-a', nickname: '가', pos: 'MF', col: 0, row: 1),
        _m(id: 'sm-b', slug: 's-b', nickname: '나나', pos: 'GK', col: 1, row: 3),
      ]);

      final moved = _afterMove(before, 'sm-a', 2, 1); // MF 왼쪽 → 오른쪽

      final seats = seatsFromSquad(moved, SquadSize.five, mySlug: 'mine');
      final mine = seats.slots.singleWhere((s) => s.mine);
      expect([mine.col, mine.row], [1, 0]);
      final b = seats.slots.singleWhere((s) => seats.mates[s.area] == '나나');
      expect([b.col, b.row], [1, 3]);
      final a = seats.slots.singleWhere((s) => seats.mates[s.area] == '가');
      expect([a.col, a.row], [2, 1]);
    });
  });
}
