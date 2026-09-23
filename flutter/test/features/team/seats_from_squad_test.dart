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

  /// 🔴 같은 사람이 두 번 나오지 않게 하는 규칙이 여기서도 지켜져야 한다.
  test('같은 칸에 둘이면 뒤엣것을 건너뛴다', () {
    final r = seatsFromSquad(
      _squad([
        _m(id: '1', nickname: '먼저', pos: 'MF', col: 0, row: 1),
        _m(id: '2', slug: 's2', nickname: '나중', pos: 'MF', col: 0, row: 1),
      ]),
      SquadSize.five,
    );

    expect(r.mates.values, contains('먼저'));
    expect(r.mates.values, isNot(contains('나중')));
  });

  /// 🔴 내 자리와 겹치는 등재가 이 갈래로 들어온다.
  test('내가 앉은 칸에 남이 또 있으면 남을 건너뛴다', () {
    final r = seatsFromSquad(
      _squad([
        _m(id: '1', slug: 'mine', nickname: '나', pos: 'DF', col: 1, row: 2),
        _m(id: '2', slug: 's2', nickname: '남', pos: 'DF', col: 1, row: 2),
      ]),
      SquadSize.five,
      mySlug: 'mine',
    );

    expect(r.slots.singleWhere((s) => s.mine).col, 1);
    expect(r.mates.values, isNot(contains('남')));
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
