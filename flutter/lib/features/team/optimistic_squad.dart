import 'board_geometry.dart';
import 'data/models/squad.dart';
import 'seats_from_squad.dart';

/// 서버에 보내기 **전에** 화면이 먼저 보여 줄 판을 만든다.
///
/// 🔴 **왜 있나 (2026-09-21, 사용자가 실기기에서 잡은 것).** 전에는 옮기면
/// 화면이 이렇게 움직였다:
///
/// 1. 손을 떼면 집은 카드가 **제자리로 튄다**(끌던 값을 버리므로)
/// 2. 서버 왕복 300ms 를 기다린다
/// 3. 그제야 새 자리로 옮겨진다
///
/// 그래서 「한 번에 안 옮겨지고 제자리로 갔다가 옮겨진다」가 됐다. 게다가 그
/// 사이 판을 다시 읽느라 값이 비면 **카드가 통째로 사라져 보였다.**
///
/// 이 함수가 만드는 판을 화면이 **그 자리에서** 그리고, 서버 응답이 오면
/// 그것으로 덮는다. 실패하면 서버 값으로 되돌린다.
///
/// 🔴 **서버가 할 일을 흉내 내는 것이지 대신하는 것이 아니다** — 여기서 만든
/// 판은 화면용이고, 참인 것은 서버가 돌려주는 스쿼드다.

/// 등재 하나를 [gridCol]·[gridRow] 로 옮긴 판.
///
/// 🔴 **포지션도 함께 바꾼다** — 계약이 `position_code` 를 늘 요구하고, 자리를
/// 옮기면 그 행이 뜻하는 포지션이 된다. 여기서 안 바꾸면 화면이 옛 포지션으로
/// 한 번 그려졌다가 서버 응답에 덮여 **이름표가 깜빡인다.**
Squad squadWithSeatMoved(
  Squad squad, {
  required String memberId,
  required String positionCode,
  required int gridCol,
  required int gridRow,
}) =>
    _replacing(squad, (m) {
      if (m.id != memberId) return m;
      return SquadMember(
        id: m.id,
        playerCardId: m.playerCardId,
        cardPublicSlug: m.cardPublicSlug,
        nickname: m.nickname,
        positionCode: positionCode,
        positionLabel: m.positionLabel,
        gridCol: gridCol,
        gridRow: gridRow,
        accepted: m.accepted,
      );
    });

/// 지금 **보이는 자리**를 등재에 박아 둔 판.
///
/// 🔴 **왜 있나 (2026-09-25, 사용자: 「내가 바꾼 뒤에 나중에 혼자 다시 다른
/// 자리에 바껴」).** [seatsFromSquad] 는 **칸이 저장 안 된 등재**를 「그때 비어
/// 있는 자리」에 새로 앉힌다(그 함수의 2단계). 그래서 내가 **다른** 카드를
/// 옮겨 빈 자리 구성이 바뀌면, **손도 안 댄 사람이 딸려 움직인다.**
/// `seats_from_squad_test.dart` 의 「칸 없는 등재는 남이 움직이면 따라
/// 움직인다」가 그 기전을 고정해 둔다.
///
/// 🔴 **고치는 자리는 「다시 앉히기」가 아니라 「칸이 없다」쪽이다.** 배정
/// 규칙을 아무리 손봐도 칸이 없는 한 남의 움직임과 얽힌다 — 칸을 주면 그
/// 갈래가 아예 안 돌아간다.
///
/// 🔴 **이미 칸이 있는 등재는 한 글자도 안 건드린다.** 건드리면 그것이 곧
/// 「내가 안 옮겼는데 움직였다」가 된다.
///
/// ⚠️ **판을 여는 것만으로 부르지 않는다** — 주장이 실제로 뭔가 옮길 때만
/// 부른다([seatsFromSquad] 2단계 주석의 「여기서 저장하지는 않는다」와 같은
/// 까닭이다). 그 규칙을 지키면서도 버그는 첫 이동 한 번으로 사라진다.
Squad squadWithShownCellsPinned(
  Squad squad,
  SquadSize size, {
  required String? mySlug,
}) {
  final seats = seatsFromSquad(squad, size, mySlug: mySlug);

  // 등재 id → 지금 보이는 칸.
  final cell = <String, SquadSlot>{};
  for (final s in seats.slots) {
    final id = seats.memberIds[s.area];
    if (id != null) cell[id] = s;
  }

  return _replacing(squad, (m) {
    if (m.hasSeat) return m;
    final s = cell[m.id];
    // 어느 자리에도 못 앉은 등재는 그대로 둔다 — 박을 칸이 없다.
    if (s == null) return m;
    return SquadMember(
      id: m.id,
      playerCardId: m.playerCardId,
      cardPublicSlug: m.cardPublicSlug,
      nickname: m.nickname,
      positionCode: m.positionCode,
      positionLabel: m.positionLabel,
      gridCol: s.col,
      gridRow: s.row,
      accepted: m.accepted,
    );
  });
}

/// 부른 사람을 **수락 전 상태로** 그 칸에 앉힌 판.
///
/// 🔴 **부른 즉시 판에 세운다**(웹 `SquadPanel` 과 같다). 수락을 기다렸다
/// 그리면 방금 고른 사람이 **아무 데도 안 보이는** 몇 초가 생기고, 사용자는
/// 자기가 뭘 잘못 눌렀는지부터 의심한다.
///
/// 🔴 **[invitationId] 를 등재 id 자리에 둔다.** 아직 스쿼드 등재가 아니라
/// 서버가 준 `squad_member.id` 가 없다 — ⊗ 로 뺄 때 이 id 로 되찾는다.
/// 수락이 실제로 오면 서버 스쿼드가 통째로 덮으므로 진짜 id 로 바뀐다.
///
/// ⚠️ **앱을 껐다 켜면 사라진다.** 계약의 초대 응답에 `grid_col`·`grid_row`
/// 가 없어서 어느 칸이었는지 되살릴 데가 없다(웹은 그래서 `localStorage` 에
/// 따로 적어 둔다 — `inviteSeats.ts`). 그 한 벌은 아직 안 옮겼다.
Squad squadWithSeatInvited(
  Squad squad, {
  required String invitationId,
  required String nickname,
  required String positionCode,
  required int gridCol,
  required int gridRow,
  String? cardPublicSlug,
}) =>
    Squad(
      id: squad.id,
      teamId: squad.teamId,
      publicSlug: squad.publicSlug,
      formation: squad.formation,
      members: [
        ...squad.members,
        SquadMember(
          id: invitationId,
          /* 🔴 카드 id 는 **모른다** — 후보 목록도 지인 목록도 그것을 안 준다.
             판은 카드를 `cardPublicSlug` 로 받아 그리므로 여기서는 안 쓰인다. */
          playerCardId: '',
          cardPublicSlug: cardPublicSlug,
          nickname: nickname,
          positionCode: positionCode,
          positionLabel: positionCode,
          gridCol: gridCol,
          gridRow: gridRow,
          // 🔴 아직 수락 전이다 — 판이 이 값으로 「수락 대기중」을 그린다.
          accepted: false,
        ),
      ],
    );

/// 그 자리를 **수락함**으로 바꾼 판.
///
/// 🔴 **시연용 자동 수락이 부르는 자리다**(아래 홈 화면의 `_demoAccept`).
/// 진짜 수락은 서버 스쿼드를 다시 읽어 덮는 쪽이고, 이것은 그 전까지
/// 화면만 앞서 가게 하는 것이다.
///
/// 🔴 **없는 자리는 되살리지 않는다** — 시연 중에 ⊗ 로 빼 놓은 사람이
/// 1.5초 뒤 되살아나면 그게 더 이상하다.
Squad squadWithSeatAccepted(Squad squad, {required String memberId}) =>
    _replacing(squad, (m) {
      if (m.id != memberId) return m;
      return SquadMember(
        id: m.id,
        playerCardId: m.playerCardId,
        cardPublicSlug: m.cardPublicSlug,
        nickname: m.nickname,
        positionCode: m.positionCode,
        positionLabel: m.positionLabel,
        gridCol: m.gridCol,
        gridRow: m.gridRow,
        accepted: true,
      );
    });

/// 두 등재의 **칸을 서로 바꾼** 판.
///
/// 🔴 **이미 사람이 있는 칸에 대면 맞바꾼다**(2026-09-25 사용자: 「둘이 서로
/// 바뀌는건 당연한 거고」). 전에는 막고 제자리로 돌려보냈다 — 「계약에 둘을
/// 한 번에 고치는 경로가 없다」는 이유였는데, **셋으로 나눠 보내면 된다**:
/// 한쪽을 칸에서 비우고 → 다른 쪽을 그 칸으로 → 비워 둔 쪽을 남은 칸으로.
/// 중간에 같은 칸에 둘이 서지 않으므로 서버가 막지 않는다.
///
/// 🔴 **포지션도 따라간다** — 행이 곧 포지션 라인이라, 칸만 바꾸면 DF 줄에
/// 선 사람의 이름표가 MF 로 남는다.
///
/// 🔴 **둘 말고는 아무도 안 움직인다.**
Squad squadWithSeatsSwapped(
  Squad squad, {
  required String aId,
  required String bId,
}) {
  SquadMember? find(String id) {
    for (final m in squad.members) {
      if (m.id == id) return m;
    }
    return null;
  }

  final a = find(aId);
  final b = find(bId);
  if (a == null || b == null || !a.hasSeat || !b.hasSeat) return squad;

  SquadMember moved(SquadMember m, SquadMember to) => SquadMember(
        id: m.id,
        playerCardId: m.playerCardId,
        cardPublicSlug: m.cardPublicSlug,
        nickname: m.nickname,
        positionCode: positionOfRow(to.gridRow!),
        positionLabel: m.positionLabel,
        gridCol: to.gridCol,
        gridRow: to.gridRow,
        accepted: m.accepted,
      );

  return _replacing(squad, (m) {
    if (m.id == aId) return moved(a, b);
    if (m.id == bId) return moved(b, a);
    return m;
  });
}

/// 등재 하나를 뺀 판.
Squad squadWithSeatRemoved(Squad squad, {required String memberId}) => Squad(
      id: squad.id,
      teamId: squad.teamId,
      publicSlug: squad.publicSlug,
      formation: squad.formation,
      members: [
        for (final m in squad.members)
          if (m.id != memberId) m,
      ],
    );

Squad _replacing(Squad squad, SquadMember Function(SquadMember) f) => Squad(
      id: squad.id,
      teamId: squad.teamId,
      publicSlug: squad.publicSlug,
      formation: squad.formation,
      members: [for (final m in squad.members) f(m)],
    );
