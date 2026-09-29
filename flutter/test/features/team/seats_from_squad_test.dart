import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/models/squad.dart';
import 'package:super_sub/features/team/seats_from_squad.dart';

SquadMember _m({
  String id = '1',
  String? slug = 's1',
  String nickname = '아무개',
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

void main() {
  _cellLessMemberDrifts();
  _noStackingTests();

  _onlyTheMovedCardMoves();

  test('스쿼드가 없으면 빈 포메이션 그대로다', () {
    final r = seatsFromSquad(null, SquadSize.five);

    expect(r.slots, hasLength(5));
    expect(r.mates, isEmpty);
    expect(r.slots.any((s) => s.mine), isFalse);
  });

  /// 🔴 웹이 2026-09-16 에 뒤집은 규칙 — 전에는 포메이션의 FW 한 칸에
  /// `mine: true` 가 박혀 있어 **처음 들어온 사람도 판에 이미 서 있었다.**
  /// 이제는 등재했을 때만 선다(「나는 안 뛴다」가 그렇게 표현된다).
  test('내 등재가 없으면 판에 내 카드가 없다', () {
    final r = seatsFromSquad(
      _squad([_m(slug: 'other', nickname: '남', pos: 'GK', col: 1, row: 3)]),
      SquadSize.five,
      mySlug: 'mine',
    );

    expect(r.slots.any((s) => s.mine), isFalse);
  });

  test('내 슬러그를 안 주면 아무도 나로 치지 않는다', () {
    final r = seatsFromSquad(
      _squad([_m(slug: 'mine', col: 1, row: 2)]),
      SquadSize.five,
    );

    expect(r.slots.any((s) => s.mine), isFalse);
  });

  test('내 등재는 내가 앉힌 칸에 선다', () {
    final r = seatsFromSquad(
      _squad([_m(slug: 'mine', nickname: '나', pos: 'DF', col: 1, row: 2)]),
      SquadSize.five,
      mySlug: 'mine',
    );

    final mine = r.slots.singleWhere((s) => s.mine);
    expect(mine.col, 1);
    expect(mine.row, 2);
  });

  /// 🔴 `mates` 에 이름이 들어가면 판이 그 자리를 「남이 앉은 카드」로 그려서
  /// 내 카드 대신 이름표가 선다.
  test('내 자리에는 이름표를 안 붙인다', () {
    final r = seatsFromSquad(
      _squad([_m(slug: 'mine', nickname: '나', pos: 'DF', col: 1, row: 2)]),
      SquadSize.five,
      mySlug: 'mine',
    );

    expect(r.mates.values, isNot(contains('나')));
    expect(r.memberIds.values, contains('1'));
  });

  test('칸이 저장된 등재는 그 칸에 앉는다', () {
    final r = seatsFromSquad(
      _squad([_m(nickname: '김철수', pos: 'MF', col: 0, row: 1)]),
      SquadSize.five,
    );

    final seat = r.slots.singleWhere((s) => r.mates[s.area] == '김철수');
    expect(seat.col, 0);
    expect(seat.row, 1);
    expect(r.slugs[seat.area], 's1');
  });

  /// 🔴 **2026-09-25에 뒤집었다.** 전에는 뒤엣것을 **건너뛰어** 판에서
  /// 사라지게 했는데, 사용자가 「같은 자리에 4개 카드가 있었는데」로 잡았다 —
  /// 사라지는 쪽도 포개지는 쪽도 나쁘다. 이제 **빈 칸으로 비켜 앉힌다.**
  test('같은 칸에 둘이면 뒤엣것이 빈 칸으로 비킨다', () {
    final r = seatsFromSquad(
      _squad([
        _m(id: '1', nickname: '먼저', pos: 'MF', col: 0, row: 1),
        _m(id: '2', slug: 's2', nickname: '나중', pos: 'MF', col: 0, row: 1),
      ]),
      SquadSize.five,
    );

    expect(r.mates.values, contains('먼저'));
    expect(r.mates.values, contains('나중'), reason: '아무도 안 사라진다');

    final first = r.slots.firstWhere((s) => r.mates[s.area] == '먼저');
    final later = r.slots.firstWhere((s) => r.mates[s.area] == '나중');
    expect((first.col, first.row), (0, 1), reason: '먼저 온 쪽이 그 칸을 갖는다');
    expect((later.col, later.row), isNot((0, 1)), reason: '겹치지 않는다');
  });

  /// 🔴 내 자리와 겹치는 등재도 **안 사라진다** — 옆 빈 칸으로 비킨다.
  /// (내 **중복 행**은 여전히 건너뛴다 — 아래 시험.)
  test('내가 앉은 칸에 남이 또 있으면 남이 비킨다', () {
    final r = seatsFromSquad(
      _squad([
        _m(id: '1', slug: 'mine', nickname: '나', pos: 'DF', col: 1, row: 2),
        _m(id: '2', slug: 's2', nickname: '남', pos: 'DF', col: 1, row: 2),
      ]),
      SquadSize.five,
      mySlug: 'mine',
    );

    expect(r.slots.singleWhere((s) => s.mine).col, 1);
    expect(r.mates.values, contains('남'), reason: '남이 사라지면 안 된다');
    final other = r.slots.firstWhere((s) => r.mates[s.area] == '남');
    expect((other.col, other.row), isNot((1, 2)), reason: '내 칸을 안 덮는다');
  });

  /// 🔴 **내 중복 행은 건너뛴다** — 서버 목록에 내가 들어 있을 수 있고,
  /// 내 카드는 0단계가 이미 세웠다. 같은 사람을 두 번 그리지 않는다.
  test('내 중복 행은 안 그린다', () {
    final r = seatsFromSquad(
      _squad([
        _m(id: '1', slug: 'mine', nickname: '나', pos: 'DF', col: 1, row: 2),
        _m(id: '2', slug: 'mine', nickname: '나', pos: 'DF', col: 1, row: 2),
      ]),
      SquadSize.five,
      mySlug: 'mine',
    );

    expect(r.mates.values, isEmpty);
    expect(r.slots.where((s) => s.mine), hasLength(1));
  });

  /// 🔴 아무 빈 자리나 끌어다 옮기면 자리들이 통째로 뒤엉켜, 원래 그 칸에
  /// 있던 자리가 밀려나며 카드가 겹쳐 사라진다.
  test('그 칸에 있는 자리를 먼저 쓴다', () {
    // 5:5 에서 (0,1)·(2,1) 이 MF 자리다. (2,1) 에 앉히면 그 자리가 쓰여야지
    // (0,1) 이 끌려와서는 안 된다.
    final r = seatsFromSquad(
      _squad([_m(nickname: '오른쪽', pos: 'MF', col: 2, row: 1)]),
      SquadSize.five,
    );

    final seat = r.slots.singleWhere((s) => r.mates[s.area] == '오른쪽');
    expect(seat.area, 'mf2');
    // (0,1) 자리는 제자리에 남아 있어야 한다.
    expect(r.slots.singleWhere((s) => s.area == 'mf1').col, 0);
  });

  test('그 칸에 자리가 아예 없으면 남는 자리를 옮겨 온다', () {
    // (0,3) 은 5:5 포메이션에 없는 칸이다(골키퍼 줄은 가운데 하나뿐).
    final r = seatsFromSquad(
      _squad([_m(nickname: '구석', pos: 'GK', col: 0, row: 3)]),
      SquadSize.five,
    );

    final seat = r.slots.singleWhere((s) => r.mates[s.area] == '구석');
    expect(seat.col, 0);
    expect(seat.row, 3);
  });

  /// ⚠️ 계약대로면 「판에 안 올린 등재」라 안 그리는 것이 맞지만, 서버의 기존
  /// 행이 전부 null 이라 그러면 판이 통째로 비어 보인다 — 등재된 사람이
  /// 화면에서 사라지는 쪽이 더 나쁘다.
  test('칸이 없는 등재는 포지션이 맞는 빈 자리에 앉는다', () {
    final r = seatsFromSquad(
      _squad([_m(nickname: '이영희', pos: 'GK')]),
      SquadSize.five,
    );

    final seat = r.slots.singleWhere((s) => r.mates[s.area] == '이영희');
    expect(seat.position, 'GK');
  });

  test('포지션이 맞는 빈 자리가 없으면 안 앉힌다', () {
    // 3:3 에는 DF 자리가 없다.
    final r = seatsFromSquad(
      _squad([_m(nickname: '수비수', pos: 'DF')]),
      SquadSize.three,
    );

    expect(r.mates, isEmpty);
  });

  /* 🔴 2026-09-18 에 웹이 데인 것. 0단계는 **칸이 있는** 내 등재만 잡고
     1단계는 me 를 건너뛰므로, 여기서까지 건너뛰면 칸 없는 내 등재는 세 단계
     어디에도 안 걸려 판에서 사라진다. 계약 60이 「수락하면 칸은 null 로
     등재」를 만든 뒤로는 **수락해서 들어온 사람 전부**가 자기 판에서 자기를
     못 보게 됐다. */
  test('칸이 없는 내 등재도 앉는다 — 여기서 me 를 빼면 안 된다', () {
    final r = seatsFromSquad(
      _squad([_m(slug: 'mine', nickname: '나', pos: 'FW')]),
      SquadSize.five,
      mySlug: 'mine',
    );

    expect(r.slots.any((s) => s.mine), isTrue);
    expect(r.mates.values, isNot(contains('나')));
  });

  test('수락 대기중인 사람이 표시된다', () {
    final r = seatsFromSquad(
      _squad([
        _m(nickname: '대기', pos: 'MF', col: 0, row: 1, accepted: false),
      ]),
      SquadSize.five,
    );

    final seat = r.slots.singleWhere((s) => r.mates[s.area] == '대기');
    expect(r.ready[seat.area], isFalse);
  });

  /// 🔴 포지션은 **저장된 값**을 쓴다 — 손으로 정했을 수 있어 행에서
  /// 역산하면 안 된다.
  test('저장된 포지션이 행보다 우선한다', () {
    // (1,1) 은 MF 행인데 등재는 FW 로 저장돼 있다.
    final r = seatsFromSquad(
      _squad([_m(nickname: '전진', pos: 'FW', col: 1, row: 1)]),
      SquadSize.seven,
    );

    final seat = r.slots.singleWhere((s) => r.mates[s.area] == '전진');
    expect(seat.position, 'FW');
  });

  /// 🔴 kFormations 는 모듈 상수다. 자리를 제자리에서 고치면 다음 호출이
  /// 남의 배치를 물려받는다.
  test('포메이션 상수를 더럽히지 않는다', () {
    seatsFromSquad(
      _squad([_m(nickname: '김', pos: 'MF', col: 2, row: 0)]),
      SquadSize.five,
    );

    final fresh = seatsFromSquad(null, SquadSize.five);
    expect(
      fresh.slots.map((s) => '${s.col},${s.row}').toList(),
      equals(
        kFormations[SquadSize.five]!.map((s) => '${s.col},${s.row}').toList(),
      ),
    );
    expect(fresh.slots.any((s) => s.mine), isFalse);
  });

  group('squadSizeOf', () {
    test('아는 값을 옮긴다', () {
      expect(squadSizeOf('3:3'), SquadSize.three);
      expect(squadSizeOf('5:5'), SquadSize.five);
      expect(squadSizeOf('7:7'), SquadSize.seven);
    });

    /// ⚠️ 2026-09-18 이전 스쿼드가 전부 null 이다 — 「모르는 값이면 기본
    /// 판으로 연다」를 지킨다.
    test('모르는 값·null 은 기본 판(5:5)이다', () {
      expect(squadSizeOf(null), SquadSize.five);
      expect(squadSizeOf('11:11'), SquadSize.five);
      expect(squadSizeOf(''), SquadSize.five);
    });
  });
}

/// 🔴 **내가 옮긴 카드 하나만 움직여야 한다** (2026-09-25, 사용자가 실기기에서
/// 잡은 것: 「다른 사람들의 카드가 그 자리로 옮겨가지 않게」).
void _onlyTheMovedCardMoves() {
  /// 그 사람이 지금 서 있는 칸.
  (int, int)? cellOf(SeatAssignment r, String nickname) {
    for (final s in r.slots) {
      if (r.mates[s.area] == nickname) return (s.col, s.row);
    }
    return null;
  }

  test('자리 없던 칸으로 옮겨도 남들은 제자리다', () {
    /* 5:5 의 기본 칸은 fw1(1,0) · mf1(0,1) · mf2(2,1) · df1(1,2) · gk(1,3).
       dtd 를 **자리가 없던 칸**(2,0)으로 옮긴 판이다 — 판은 그 칸에 놓는 것을
       허락한다(자리 다섯은 격자 위를 돌아다닌다). */
    final r = seatsFromSquad(
      _squad([
        _m(id: '1', slug: 'a', nickname: '정상호', pos: 'MF', col: 0, row: 1),
        _m(id: '2', slug: 'b', nickname: 'dtd', pos: 'FW', col: 2, row: 0),
        _m(id: '3', slug: 'c', nickname: '같이뛰실분', pos: 'DF', col: 1, row: 2),
        _m(id: '4', slug: 'd', nickname: '새내기키퍼', pos: 'GK', col: 1, row: 3),
      ]),
      SquadSize.five,
    );

    expect(cellOf(r, 'dtd'), (2, 0), reason: '옮긴 사람은 옮긴 칸에');
    expect(cellOf(r, '정상호'), (0, 1), reason: '남은 제자리여야 한다');
    expect(cellOf(r, '같이뛰실분'), (1, 2), reason: '남은 제자리여야 한다');
    expect(cellOf(r, '새내기키퍼'), (1, 3), reason: '남은 제자리여야 한다');
  });

  /// 🔴 서버가 주는 순서에 기대면 안 된다 — 같은 판인데 순서만 달라도 결과가
  /// 같아야 한다.
  test('서버 목록 순서가 달라도 같은 자리다', () {
    final forward = seatsFromSquad(
      _squad([
        _m(id: '1', slug: 'a', nickname: '정상호', pos: 'MF', col: 0, row: 1),
        _m(id: '2', slug: 'b', nickname: 'dtd', pos: 'FW', col: 2, row: 0),
        _m(id: '3', slug: 'c', nickname: '같이뛰실분', pos: 'DF', col: 1, row: 2),
      ]),
      SquadSize.five,
    );
    final backward = seatsFromSquad(
      _squad([
        _m(id: '3', slug: 'c', nickname: '같이뛰실분', pos: 'DF', col: 1, row: 2),
        _m(id: '2', slug: 'b', nickname: 'dtd', pos: 'FW', col: 2, row: 0),
        _m(id: '1', slug: 'a', nickname: '정상호', pos: 'MF', col: 0, row: 1),
      ]),
      SquadSize.five,
    );

    for (final n in ['정상호', 'dtd', '같이뛰실분']) {
      expect(cellOf(backward, n), cellOf(forward, n), reason: '$n 의 칸');
    }
  });
}

/// 🔴 **버그의 기전** (2026-09-25, 사용자: 「내가 바꾼 뒤에 나중에 혼자 다시
/// 다른자리에 바껴」). 칸이 저장 안 된 등재는 **그때 비어 있는 자리**에 새로
/// 앉으므로, 남이 움직여 빈 자리 구성이 바뀌면 **손도 안 댄 사람이 딸려
/// 움직인다.**
void _cellLessMemberDrifts() {
  (int, int)? cellOf(SeatAssignment r, String nickname) {
    for (final s in r.slots) {
      if (r.mates[s.area] == nickname) return (s.col, s.row);
    }
    return null;
  }

  /// 🔴 **이것은 고침이 아니라 기록이다.** 이 함수는 **일부러** 이렇게 둔다 —
  /// 칸이 없는 등재라도 판에서 사라지는 것보다는 어디든 앉히는 쪽이 낫다는
  /// 판단(2단계 주석)이 먼저 있었다.
  ///
  /// 🔴 **막는 자리는 부르는 쪽이다** — 주장이 뭔가 옮길 때
  /// `squadWithShownCellsPinned` 가 보이는 칸을 등재에 박아서, 이 갈래가 아예
  /// 안 돌아가게 한다. 그쪽 시험이
  /// `optimistic_squad_test.dart` 의 「박아 두면 남이 움직여도 안 따라간다」다.
  test('칸 없는 등재는 남이 움직이면 따라 움직인다 (알려진 성질)', () {
    SeatAssignment board(int bCol, int bRow) => seatsFromSquad(
          _squad([
            _m(id: 'A', slug: 'a', nickname: 'A', pos: 'MF'),
            _m(id: 'B', slug: 'b', nickname: 'B', pos: 'MF', col: bCol, row: bRow),
          ]),
          SquadSize.five,
        );

    // B 만 (1,1) 로 옮겼는데 A 도 따라 움직인다 — 이것이 버그의 기전이다.
    expect(cellOf(board(0, 1), 'A'), (2, 1));
    expect(cellOf(board(1, 1), 'A'), (0, 1));
  });
}

/// 🔴 **자리 둘이 같은 칸에 서지 않는다** (2026-09-25, 사용자: 「새로 빌드되면
/// 같은 자리에 4개 카드가 있었는데」).
///
/// 서버에 같은 칸을 가진 등재가 여럿 있으면(옛 데이터·중복 등재), 1단계의
/// 폴백이 **남는 자리를 끌어와 그 칸으로 옮겨** 그대로 겹쳐 쌓였다. 카드가
/// 포개져 맨 위 것만 보이고, ⊗ 로 지우면 뒤엣것이 나온다.
void _noStackingTests() {
  test('같은 칸을 가진 등재가 여럿이어도 겹치지 않는다', () {
    final r = seatsFromSquad(
      _squad([
        _m(id: '1', slug: 'a', nickname: 'A', pos: 'DF', col: 1, row: 2),
        _m(id: '2', slug: 'b', nickname: 'B', pos: 'DF', col: 1, row: 2),
        _m(id: '3', slug: 'c', nickname: 'C', pos: 'DF', col: 1, row: 2),
        _m(id: '4', slug: 'd', nickname: 'D', pos: 'DF', col: 1, row: 2),
      ]),
      SquadSize.five,
    );

    final cells = <String>{};
    for (final s in r.slots) {
      expect(cells.add('${s.col},${s.row}'), isTrue,
          reason: '(${s.col},${s.row}) 에 자리가 둘이다');
    }
  });

  /// 🔴 **먼저 온 사람이 그 칸을 갖는다** — 나머지는 빈 칸으로 흩어진다.
  test('첫 사람은 제 칸에 남는다', () {
    final r = seatsFromSquad(
      _squad([
        _m(id: '1', slug: 'a', nickname: 'A', pos: 'DF', col: 1, row: 2),
        _m(id: '2', slug: 'b', nickname: 'B', pos: 'DF', col: 1, row: 2),
      ]),
      SquadSize.five,
    );

    final a = r.slots.firstWhere((s) => r.mates[s.area] == 'A');
    expect((a.col, a.row), (1, 2));
    expect(r.mates.values, containsAll(['A', 'B']), reason: '아무도 안 사라진다');
  });
}
