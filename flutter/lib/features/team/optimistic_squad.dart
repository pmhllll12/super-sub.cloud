import 'data/models/squad.dart';

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
