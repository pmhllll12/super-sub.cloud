import 'data/models/squad.dart';
import 'seats_from_squad.dart';

/// 자동 착석이 고른 자리. `null` 이면 **앉히지 않는다.**
class AutoSeatChoice {
  const AutoSeatChoice({
    required this.col,
    required this.row,
    required this.positionCode,
  });

  final int col;
  final int row;
  final String positionCode;
}

/// 카드를 만든 사람을 **판에 먼저 앉힌다** — 웹 `SquadPanel.tsx` 의 자동 착석
/// (2026-09-17 사용자 판단)을 옮긴 것이다.
///
/// 🔴 **왜 있나.** 배치 함수([seatsFromSquad])는 등재를 **그릴** 뿐 만들지
/// 않는다. 이것이 없으면 앱에서 내 카드가 판에 설 방법이 아예 없다.
/// 웹 주석이 그 판단의 근거다:
///
/// > 하루 전에는 「빈 자리를 눌러 뜨는 **「나」 표식**을 눌러야 내 카드가 선다」
/// > 였다. 그 표식을 **없앴다** — 팀을 만든 사람은 **뛴다고 보고 FW 에 먼저
/// > 앉힌다.** 옮기든 빼든 그건 그다음 일이고, **일단 앉혀 놓고** 시작하는 것이
/// > 판을 처음 여는 사람에게 자연스럽다.
///
/// 🔴 **FW 가 먼저, 차 있으면 빈 자리 아무 데나.** 「무조건 뛴다」가 전제라
/// 남이 이미 앉아 있어도 나는 판에 선다 — 다만 **남을 밀어내지는 않는다.**
/// 빈 자리가 하나도 없으면 `null` 이다(그때는 판이 이미 다 찼다).
///
/// 부르는 쪽이 지켜야 하는 것 둘은 여기 없다 — 이 함수는 순수하다:
/// - 🔴 **주장만** 부른다(등재는 주장 전용이라 팀원이 부르면 403 이고, 판에만
///   섰다가 새로고침에 사라진다)
/// - 🔴 **세션 안 한 번만** 부른다(판이 비는 다른 길에서 다시 돌면 같은 등재가
///   서버로 두 번 나간다)
AutoSeatChoice? pickAutoSeat({
  required Squad? squad,
  required String? myCardSlug,
  required SquadSize size,
}) {
  if (squad == null || myCardSlug == null) return null;

  final seats = seatsFromSquad(squad, size, mySlug: myCardSlug);
  // 이미 판에 서 있으면 아무것도 안 한다.
  if (seats.slots.any((s) => s.mine)) return null;

  bool free(SquadSlot s) => !s.mine && !seats.mates.containsKey(s.area);

  // 🔴 FW(`fw1`) 가 먼저다.
  SquadSlot? seat;
  for (final s in seats.slots) {
    if (s.area == 'fw1' && free(s)) {
      seat = s;
      break;
    }
  }
  // 차 있으면 빈 자리 아무 데나.
  if (seat == null) {
    for (final s in seats.slots) {
      if (free(s)) {
        seat = s;
        break;
      }
    }
  }
  if (seat == null) return null;

  return AutoSeatChoice(
    col: seat.col,
    row: seat.row,
    // 포지션은 그 자리가 뜻하는 것이다(행이 포지션 라인이다).
    positionCode: seat.position,
  );
}
