import 'data/models/squad.dart';

/// 판의 크기 — 3:3 · 5:5 · 7:7.
enum SquadSize {
  three('3 : 3'),
  five('5 : 5'),
  seven('7 : 7');

  const SquadSize(this.label);

  final String label;
}

/// 판 위의 자리. [col]·[row] 는 3열 × 4행 격자 칸이고, **행이 포지션 라인**이다
/// (0 FW · 1 MF · 2 DF · 3 GK — 웹 `lib/pitchGrid.ts` 의 `ROW_POS`).
///
/// 🔴 **[col]·[row]·[mine]·[positionCode] 가 가변인 이유**: [seatsFromSquad] 가
/// 서버 등재에 맞춰 자리를 옮긴다. 그래서 상수 배열을 그대로 쓰면 안 되고
/// 반드시 [copy] 로 복사해서 만진다.
class SquadSlot {
  SquadSlot(this.area, this.col, this.row, {this.mine = false, this.positionCode});

  /// 역할+번호(`fw1` · `mf2` …). 🔴 크기를 바꿔도 같은 이름이 같은 자리를
  /// 가리켜야 한다.
  final String area;

  int col;
  int row;

  /// 내 카드가 서는 자리.
  ///
  /// 🔴 **포메이션에 박아 두지 않는다**(2026-09-16 웹이 뒤집었다). 전에는 FW
  /// 한 칸에 박혀 있어 **처음 들어온 사람도 판에 이미 서 있었다.** 이제는
  /// 등재했을 때만, 그것도 내가 앉힌 칸에 선다.
  bool mine;

  /// 서버에 저장된 포지션. 🔴 **손으로 정했을 수 있어 행에서 역산하면 안 된다.**
  String? positionCode;

  SquadSlot copy() =>
      SquadSlot(area, col, row, mine: mine, positionCode: positionCode);

  /// 저장된 값이 있으면 그것, 없으면 행이 뜻하는 라인.
  String get position => positionCode ?? const ['FW', 'MF', 'DF', 'GK'][row];
}

/// 크기마다의 포메이션 — 웹 `SquadPanel.tsx` 의 `FORMATIONS` 를 그대로 옮겼다.
/// 위가 공격, 아래가 골키퍼다.
///
/// 🔴 **모듈 상수다.** 여기 들어 있는 자리를 제자리에서 고치면 다음 호출이
/// 남의 배치를 물려받는다 — [seatsFromSquad] 가 반드시 [SquadSlot.copy] 로
/// 복사해서 만지는 이유다.
final Map<SquadSize, List<SquadSlot>> kFormations = {
  // 1-1-1
  SquadSize.three: [
    SquadSlot('fw1', 1, 0),
    SquadSlot('mf1', 1, 1),
    SquadSlot('gk', 1, 3),
  ],
  // 1-2-1 — 풋살 5인.
  SquadSize.five: [
    SquadSlot('fw1', 1, 0),
    SquadSlot('mf1', 0, 1),
    SquadSlot('mf2', 2, 1),
    SquadSlot('df1', 1, 2),
    SquadSlot('gk', 1, 3),
  ],
  // 2-3-1
  SquadSize.seven: [
    SquadSlot('fw1', 1, 0),
    SquadSlot('mf1', 0, 1),
    SquadSlot('mf2', 1, 1),
    SquadSlot('mf3', 2, 1),
    SquadSlot('df1', 0, 2),
    SquadSlot('df2', 2, 2),
    SquadSlot('gk', 1, 3),
  ],
};

/// 자리 배치 결과. 모든 맵의 키는 [SquadSlot.area](`fw1`·`mf2` …)다.
class SeatAssignment {
  const SeatAssignment({
    required this.slots,
    required this.mates,
    required this.slugs,
    required this.memberIds,
    required this.ready,
  });

  final List<SquadSlot> slots;

  /// 그 자리에 앉은 **남**의 이름. 🔴 내 자리는 여기 없다 — 거기는 내 카드가
  /// 그린다.
  final Map<String, String> mates;

  /// 그 자리 사람의 **카드 공개 슬러그** — 진짜 카드를 그리려면 필요하다.
  final Map<String, String?> slugs;

  /// 그 자리 등재의 id(빼기·옮기기가 쓸 값).
  final Map<String, String> memberIds;

  /// 그 자리의 사람이 **오기로 했는가**.
  final Map<String, bool> ready;
}

/// 서버 `formation` → 판 크기. 🔴 **모르는 값이면 기본 판**이다.
SquadSize squadSizeOf(String? formation) => switch (formation) {
      '3:3' => SquadSize.three,
      '7:7' => SquadSize.seven,
      _ => SquadSize.five,
    };

/// 서버 스쿼드를 판 위의 자리로 — 웹 `SquadPanel.tsx` 의 `seatsFromSquad` 를
/// 그대로 옮긴 것이다.
///
/// 🔴 **세 단계의 순서가 곧 규칙이고, 각 단계가 실제 사고에서 나왔다.**
/// 줄이거나 합치면 그 사고가 돌아온다(설계 문서 2-2절).
///
/// 0. 내 등재를 먼저 집는다 — 칸이 있으면 그 칸에.
/// 1. 칸이 저장된 등재 — 그 칸이 곧 자리다.
/// 2. 칸이 없는 등재 — 포지션이 맞는 빈 자리에.
SeatAssignment seatsFromSquad(
  Squad? squad,
  SquadSize size, {
  /// 내 카드의 공개 슬러그 — **어느 등재가 나인지** 가리는 열쇠다.
  String? mySlug,
}) {
  // 🔴 자리는 **복사해서** 만진다(위 kFormations 주석).
  final slots = kFormations[size]!.map((s) => s.copy()).toList();
  final mates = <String, String>{};
  final slugs = <String, String?>{};
  final memberIds = <String, String>{};
  final ready = <String, bool>{};

  // 맵들을 그대로 참조하므로 아래에서 채우면 이 객체에 반영된다.
  final result = SeatAssignment(
    slots: slots,
    mates: mates,
    slugs: slugs,
    memberIds: memberIds,
    ready: ready,
  );
  if (squad == null) return result;

  /// 그 자리가 **이미 차 있는가.**
  ///
  /// 🔴 **내 자리(`mine`)도 찬 것으로 센다.** 거기는 내 카드가 그리므로
  /// `mates` 에는 안 들어가는데, 그것만 보고 판단하면 **내 카드 위로 남의
  /// 카드를 옮겨 놓는다** — 실제로 그래서 내 카드가 안 보였다(2026-09-10).
  bool taken(SquadSlot s) => s.mine || mates.containsKey(s.area);

  SquadSlot? firstWhere(bool Function(SquadSlot) test) {
    for (final s in slots) {
      if (test(s)) return s;
    }
    return null;
  }

  /* 0) **내 자리도 등재와 잇는다.** 전에는 「내 자리는 카드가 그린다」는 이유로
        등재와 안 이어 놓았는데, 그러면 내 카드만 포지션과 칸이 안 남았다 —
        옮길 수는 있는데 새로 고치면 제자리로 돌아갔다. */
  SquadMember? me;
  if (mySlug != null) {
    for (final m in squad.members) {
      if (m.cardPublicSlug == mySlug) {
        me = m;
        break;
      }
    }
  }
  if (me != null && me.hasSeat) {
    final seat = firstWhere((s) => s.col == me!.gridCol && s.row == me.gridRow);
    if (seat != null) {
      seat.mine = true;
      memberIds[seat.area] = me.id;
      // 포지션도 저장된 값을 쓴다(행과 같으면 「자동」인 셈이다).
      seat.positionCode = me.positionCode;
    }
  }

  // 1) **칸이 저장된 등재 — 그 칸이 곧 자리다.**
  for (final m in squad.members) {
    if (identical(m, me) || !m.hasSeat) continue;
    /* 🔴 그 칸이 이미 찼으면 **건너뛴다.** 내 자리와 겹치는 것이 이 갈래로
       들어온다 — 서버 목록에 내가 들어 있어도 같은 사람이 두 번 나오지
       않게 하는 것이 원래 규칙이고, 그 규칙을 여기서도 지킨다. */
    if (slots.any((s) => taken(s) && s.col == m.gridCol && s.row == m.gridRow)) {
      continue;
    }
    /* 🔴 **그 칸에 있는 자리를 먼저 쓴다.** 아무 빈 자리나 끌어다 옮기면
       자리들이 통째로 뒤엉켜, 원래 그 칸에 있던 자리가 밀려나며 카드가
       겹쳐 사라진다. 그 칸에 자리가 없을 때만(골키퍼 줄 양옆처럼 아예 없는
       칸, 또는 판이 작아진 경우) 남는 자리를 옮겨 온다. */
    final seat =
        firstWhere((s) => !taken(s) && s.col == m.gridCol && s.row == m.gridRow) ??
            firstWhere((s) => !taken(s));
    if (seat == null) continue;
    seat.col = m.gridCol!;
    seat.row = m.gridRow!;
    seat.positionCode = m.positionCode;
    mates[seat.area] = m.nickname;
    slugs[seat.area] = m.cardPublicSlug;
    memberIds[seat.area] = m.id;
    ready[seat.area] = m.accepted;
  }

  /* 2) **칸이 아직 없는 등재**는 포메이션의 기본 자리에 포지션으로 맞춰 앉힌다.
        ⚠️ 계약대로면 「판에 안 올린 등재」라 안 그리는 것이 맞지만, 그러면
        서버의 **기존 행이 전부 null 이라** 판이 통째로 비어 보인다 — 등재된
        사람이 화면에서 사라지는 쪽이 더 나쁘다. 앉혀서 보여 주되 🔴 **여기서
        저장하지는 않는다**(판을 여는 것만으로 서버가 바뀌면 안 된다). */
  for (final m in squad.members) {
    if (m.hasSeat) continue;
    final seat = firstWhere((s) => !taken(s) && s.position == m.positionCode);
    if (seat == null) continue;
    /* 🔴 **여기서 `me` 를 빼면 안 된다**(2026-09-18, 사용자 지적 — 실제
       도메인에서 「수락했는데 내 카드가 안 보인다」). 0단계는 **칸이 있는**
       내 등재만 잡고 1단계는 `me` 를 건너뛰므로, 여기서까지 건너뛰면
       **칸 없는 내 등재는 세 단계 어디에도 안 걸려 판에서 사라진다.**
       계약 60이 「수락하면 칸은 `null` 로 등재」를 만든 뒤로는 **수락해서
       들어온 사람 전부가** 자기 판에서 자기를 못 보게 됐다. */
    if (identical(m, me)) {
      seat.mine = true;
      memberIds[seat.area] = m.id;
      seat.positionCode = m.positionCode;
      continue;
    }
    mates[seat.area] = m.nickname;
    slugs[seat.area] = m.cardPublicSlug;
    memberIds[seat.area] = m.id;
    ready[seat.area] = m.accepted;
  }

  return result;
}
