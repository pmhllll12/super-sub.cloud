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

  /* 🔴🔴 **진짜 원인**(2026-09-21, 실기기 로그로 잡았다).
     격자는 3열×4행(12칸)인데 **포메이션 자리는 다섯뿐**이다. 자리가 없는
     칸(예: 5:5 의 (2,0))에 놓을 수 있게 해 둬서:
     - 내 등재가 그 칸에 가면 0단계가 자리를 못 찾아 **판에서 사라진다**
     - 남의 등재가 그 칸에 가면 1단계의 「남는 자리 아무 데나」로 떨어져
       **엉뚱한 자리에 나타난다**
     그래서 **놓을 수 있는 곳은 「칸」이 아니라 「자리」여야 한다.** */
  /* 🔴 **자리 다섯은 격자 위를 돌아다닌다.** 포메이션은 처음 배치일 뿐이라,
     저장된 칸에 자리가 없으면 **남는 자리를 그 칸으로 옮겨 온다.**
     1단계는 원래 이 폴백을 갖고 있었는데 0단계(내 등재)에만 없어서,
     내 카드를 그런 칸으로 옮기면 **판에서 사라졌다.** */
  group('포메이션에 없던 칸', () {
    test('내 등재가 그런 칸에 있어도 판에 그려진다', () {
      final moved = _squad([
        // (2,0) 은 5:5 포메이션의 기본 배치에 없는 칸이다.
        _m(id: 'sm-me', slug: 'mine', nickname: '나', pos: 'FW', col: 2, row: 0),
      ]);

      final seats = seatsFromSquad(moved, SquadSize.five, mySlug: 'mine');

      final mine = seats.slots.where((s) => s.mine).toList();
      expect(mine, hasLength(1), reason: '내 카드가 판에서 사라졌다');
      expect([mine.single.col, mine.single.row], [2, 0]);
    });

    test('내 등재와 남의 등재가 섞여 있어도 각자 제 칸이다', () {
      final moved = _squad([
        _m(id: 'sm-me', slug: 'mine', nickname: '나', pos: 'FW', col: 2, row: 0),
        _m(id: 'sm-a', slug: 's-a', nickname: '가', pos: 'DF', col: 0, row: 2),
      ]);

      final seats = seatsFromSquad(moved, SquadSize.five, mySlug: 'mine');

      final mine = seats.slots.singleWhere((s) => s.mine);
      expect([mine.col, mine.row], [2, 0]);
      final a = seats.slots.singleWhere((s) => seats.mates[s.area] == '가');
      expect([a.col, a.row], [0, 2]);
    });

    test('남의 등재가 그런 칸에 있으면 그 칸에 그려진다', () {
      final broken = _squad([
        _m(id: 'sm-a', slug: 's-a', nickname: '가', pos: 'GK', col: 2, row: 0),
      ]);

      final seats = seatsFromSquad(broken, SquadSize.five, mySlug: 'mine');

      final seat = seats.slots.singleWhere((s) => seats.mates[s.area] == '가');
      // 놓은 칸이 그대로 쓰이지만, 그 칸에는 원래 자리가 없었다.
      expect([seat.col, seat.row], [2, 0]);
    });
  });
}
