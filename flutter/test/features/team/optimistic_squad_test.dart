import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/data/models/squad.dart';
import 'package:super_sub/features/team/optimistic_squad.dart';
import 'package:super_sub/features/team/seats_from_squad.dart';

Squad _empty() => const Squad(
      id: 's',
      teamId: 't',
      publicSlug: 'p',
      formation: '5:5',
      members: [],
    );

void main() {
  _pinTests();
  _swapTests();

  group('squadWithSeatInvited', () {
    /// 🔴 **부른 즉시 판에 선다**(웹과 같다). 수락을 기다렸다 그리면, 사람이
    /// 방금 고른 사람이 **아무 데도 안 보이는** 몇 초가 생긴다.
    test('부른 사람이 그 칸에 바로 앉는다', () {
      final after = squadWithSeatInvited(
        _empty(),
        invitationId: 'inv-1',
        nickname: '라인세우기',
        cardPublicSlug: 'line-1',
        positionCode: 'DF',
        gridCol: 0,
        gridRow: 2,
      );

      expect(after.members, hasLength(1));
      final m = after.members.single;
      expect(m.nickname, '라인세우기');
      expect(m.cardPublicSlug, 'line-1');
      expect(m.gridCol, 0);
      expect(m.gridRow, 2);
      expect(m.positionCode, 'DF');
    });

    /// 🔴 **아직 수락 전이다** — 판이 이 값으로 「수락 대기중」을 그린다.
    test('수락 전으로 앉는다', () {
      final after = squadWithSeatInvited(
        _empty(),
        invitationId: 'inv-1',
        nickname: '라인세우기',
        positionCode: 'DF',
        gridCol: 0,
        gridRow: 2,
      );

      expect(after.members.single.accepted, isFalse);
    });

    /// 🔴 **등재 id 는 초대 id 로 둔다.** 아직 스쿼드 등재가 아니라 서버가 준
    /// `squad_member.id` 가 없다 — ⊗ 로 뺄 때 이 id 로 되찾는다.
    test('초대 id 로 판에서 되찾을 수 있다', () {
      final after = squadWithSeatInvited(
        _empty(),
        invitationId: 'inv-9',
        nickname: 'ㄱ',
        positionCode: 'GK',
        gridCol: 1,
        gridRow: 3,
      );

      expect(after.members.single.id, 'inv-9');
      expect(
        squadWithSeatRemoved(after, memberId: 'inv-9').members,
        isEmpty,
      );
    });
  });

  group('squadWithSeatAccepted', () {
    /// 🔴 시연용 자동 수락이 부르는 자리 — 같은 사람을 **수락함**으로 바꾼다.
    test('그 자리를 수락함으로 바꾼다', () {
      final invited = squadWithSeatInvited(
        _empty(),
        invitationId: 'inv-1',
        nickname: '라인세우기',
        positionCode: 'DF',
        gridCol: 0,
        gridRow: 2,
      );

      final after = squadWithSeatAccepted(invited, memberId: 'inv-1');

      expect(after.members.single.accepted, isTrue);
      expect(after.members.single.nickname, '라인세우기');
    });

    /// 🔴 이미 ⊗ 로 뺀 자리를 수락으로 되살리지 않는다 — 시연 중에 빼 놓은
    /// 사람이 1.5초 뒤 되살아나면 그게 더 이상하다.
    test('없는 자리는 되살리지 않는다', () {
      final after = squadWithSeatAccepted(_empty(), memberId: 'inv-1');

      expect(after.members, isEmpty);
    });
  });
}

/// 🔴 **떠돌이 버그의 뿌리를 막는다** (2026-09-25).
/// `seatsFromSquad` 는 **칸이 저장 안 된 등재**를 「그때 비어 있는 자리」에 새로
/// 앉힌다. 그래서 내가 다른 카드를 옮겨 빈 자리 구성이 바뀌면 **손도 안 댄
/// 사람이 딸려 움직인다**(`seats_from_squad_test.dart` 가 그 기전을 고정한다).
/// 지금 보이는 자리를 등재에 박아 두면 그 다시-앉히기가 아예 안 일어난다.
void _pinTests() {
  SquadMember mem(String id, String pos, {int? col, int? row}) => SquadMember(
        id: id,
        playerCardId: 'card-$id',
        cardPublicSlug: 's-$id',
        nickname: id,
        positionCode: pos,
        positionLabel: pos,
        gridCol: col,
        gridRow: row,
        accepted: true,
      );

  Squad sq(List<SquadMember> m) => Squad(
        id: 's',
        teamId: 't',
        publicSlug: 'p',
        formation: '5:5',
        members: m,
      );

  group('squadWithShownCellsPinned', () {
    test('칸 없는 등재가 지금 보이는 칸을 갖는다', () {
      final after = squadWithShownCellsPinned(
        sq([mem('A', 'MF'), mem('B', 'MF', col: 0, row: 1)]),
        SquadSize.five,
        mySlug: null,
      );

      final a = after.members.firstWhere((m) => m.id == 'A');
      expect(a.hasSeat, isTrue, reason: 'A 도 칸을 갖는다');
      expect((a.gridCol, a.gridRow), (2, 1), reason: '지금 보이던 그 칸이다');
    });

    /// 🔴 **이미 칸이 있는 등재는 한 글자도 안 건드린다** — 건드리면 그것이
    /// 곧 「내가 안 옮겼는데 움직였다」가 된다.
    test('칸이 있던 등재는 그대로다', () {
      final after = squadWithShownCellsPinned(
        sq([mem('A', 'MF'), mem('B', 'MF', col: 0, row: 1)]),
        SquadSize.five,
        mySlug: null,
      );

      final b = after.members.firstWhere((m) => m.id == 'B');
      expect((b.gridCol, b.gridRow), (0, 1));
    });

    /// 박은 뒤에는 **남이 움직여도 안 따라간다** — 이 시험이 버그의 재발을
    /// 잡는 자리다.
    test('박아 두면 남이 움직여도 안 따라간다', () {
      final pinned = squadWithShownCellsPinned(
        sq([mem('A', 'MF'), mem('B', 'MF', col: 0, row: 1)]),
        SquadSize.five,
        mySlug: null,
      );
      final aBefore = pinned.members.firstWhere((m) => m.id == 'A');

      // B 만 (1,1) 로 옮긴다.
      final moved = squadWithSeatMoved(pinned,
          memberId: 'B', positionCode: 'MF', gridCol: 1, gridRow: 1);
      final seats = seatsFromSquad(moved, SquadSize.five);

      final aSlot = seats.slots.firstWhere((s) => seats.mates[s.area] == 'A');
      expect((aSlot.col, aSlot.row), (aBefore.gridCol, aBefore.gridRow));
    });
  });
}

/// 🔴 **이미 사람이 있는 칸에 대면 둘이 자리를 맞바꾼다**
/// (2026-09-25 사용자: 「거기에 대면 둘이 서로 바뀌는건 당연한 거고」).
/// 전에는 막고 제자리로 돌려보냈다 — 계약에 「둘을 한 번에」가 없다는 이유
/// 였는데, **셋으로 나눠 보내면 된다**(비우기 → 채우기 → 채우기).
void _swapTests() {
  SquadMember mem(String id, String pos, int col, int row) => SquadMember(
        id: id,
        playerCardId: 'card-$id',
        cardPublicSlug: 's-$id',
        nickname: id,
        positionCode: pos,
        positionLabel: pos,
        gridCol: col,
        gridRow: row,
        accepted: true,
      );

  Squad sq(List<SquadMember> m) => Squad(
        id: 's',
        teamId: 't',
        publicSlug: 'p',
        formation: '5:5',
        members: m,
      );

  group('squadWithSeatsSwapped', () {
    test('둘의 칸이 서로 바뀐다', () {
      final after = squadWithSeatsSwapped(
        sq([mem('A', 'MF', 0, 1), mem('B', 'DF', 1, 2)]),
        aId: 'A',
        bId: 'B',
      );

      final a = after.members.firstWhere((m) => m.id == 'A');
      final b = after.members.firstWhere((m) => m.id == 'B');
      expect((a.gridCol, a.gridRow), (1, 2));
      expect((b.gridCol, b.gridRow), (0, 1));
    });

    /// 🔴 **포지션도 따라간다** — 행이 곧 포지션 라인이라, 칸만 바꾸면
    /// DF 줄에 선 사람의 이름표가 MF 로 남는다.
    test('포지션도 그 줄의 것으로 바뀐다', () {
      final after = squadWithSeatsSwapped(
        sq([mem('A', 'MF', 0, 1), mem('B', 'DF', 1, 2)]),
        aId: 'A',
        bId: 'B',
      );

      expect(after.members.firstWhere((m) => m.id == 'A').positionCode, 'DF');
      expect(after.members.firstWhere((m) => m.id == 'B').positionCode, 'MF');
    });

    /// 🔴 **나머지는 한 글자도 안 건드린다** — 그게 이 회차의 요구 전부다.
    test('둘 말고는 아무도 안 움직인다', () {
      final after = squadWithSeatsSwapped(
        sq([
          mem('A', 'MF', 0, 1),
          mem('B', 'DF', 1, 2),
          mem('C', 'GK', 1, 3),
        ]),
        aId: 'A',
        bId: 'B',
      );

      final c = after.members.firstWhere((m) => m.id == 'C');
      expect((c.gridCol, c.gridRow), (1, 3));
      expect(c.positionCode, 'GK');
    });
  });
}
