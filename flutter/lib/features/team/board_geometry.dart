import 'dart:ui' show Offset, Size;

/// 판의 격자 — **3열 × 4행**이고 **행이 포지션 라인**이다
/// (0 FW · 1 MF · 2 DF · 3 GK).
///
/// 🔴 **격자 크기·행 의미가 바뀌면 저장된 값의 뜻도 바뀐다** — 그때는 서버에
/// 리매핑 마이그레이션이 필요하다(계약 3-7절 「홈 판 격자」가 그 값의 정본이다).
const int kBoardCols = 3;
const int kBoardRows = 4;

/// 판 안의 어느 점이 **어느 칸**인가.
///
/// 🔴 **칸 번호로 다룬다 — 화면 픽셀이 아니다.** 카드 크기가 바뀌어도 배치가
/// 안 어긋나야 해서 계약이 그렇게 정했다.
///
/// [padTop]·[padSide]·[padBottom] 은 판 안 여백이고, [size] 는 판 전체 크기다.
/// 판 **밖**이면 `null` — 끌다가 판을 벗어나면 놓을 자리가 없다.
({int col, int row})? cellAt(
  Offset point,
  Size size, {
  required double padTop,
  required double padSide,
  required double padBottom,
}) {
  final gridW = size.width - padSide * 2;
  final gridH = size.height - padTop - padBottom;
  if (gridW <= 0 || gridH <= 0) return null;

  final x = point.dx - padSide;
  final y = point.dy - padTop;
  if (x < 0 || y < 0 || x >= gridW || y >= gridH) return null;

  final col = (x / (gridW / kBoardCols)).floor();
  final row = (y / (gridH / kBoardRows)).floor();
  // 오른쪽·아래 끝에 정확히 닿으면 한 칸 넘어간다 — 묶는다.
  return (
    col: col.clamp(0, kBoardCols - 1),
    row: row.clamp(0, kBoardRows - 1),
  );
}

/// 그 칸의 **왼쪽 위 모서리**(카드를 그릴 자리를 정하는 데 쓴다).
Offset cellOrigin(
  int col,
  int row,
  Size size, {
  required double padTop,
  required double padSide,
  required double padBottom,
}) {
  final cellW = (size.width - padSide * 2) / kBoardCols;
  final cellH = (size.height - padTop - padBottom) / kBoardRows;
  return Offset(padSide + col * cellW, padTop + row * cellH);
}

/// 손끝에서 **가장 가까운 자리**. 판 밖이면 `null`.
///
/// 🔴 **왜 「가장 가까운」인가** (2026-09-21, 사용자 지적 「아예 못 옮기게
/// 만들면 어떡해」). 처음엔 「그 칸에 자리가 있을 때만」으로 했는데, 격자는
/// 12칸이고 자리는 다섯뿐이라 **손끝이 칸 경계를 조금만 벗어나면 안 놓였다** —
/// 사실상 못 옮긴다. 자리로 **붙여** 주면 대충 끌어도 들어가고, 자리 밖
/// 좌표가 서버에 저장되는 일도 없다.
///
/// [slotCenters] 는 자리마다 (칸 가운데) 좌표다.
int? nearestSlotIndex(Offset point, List<Offset> slotCenters) {
  if (slotCenters.isEmpty) return null;
  var best = 0;
  var bestD = double.infinity;
  for (var i = 0; i < slotCenters.length; i += 1) {
    final d = (slotCenters[i] - point).distanceSquared;
    if (d < bestD) {
      bestD = d;
      best = i;
    }
  }
  return best;
}

/// 그 칸의 **가운데**(자리에 붙일 때 기준이 되는 점).
Offset cellCenter(
  int col,
  int row,
  Size size, {
  required double padTop,
  required double padSide,
  required double padBottom,
}) {
  final cellW = (size.width - padSide * 2) / kBoardCols;
  final cellH = (size.height - padTop - padBottom) / kBoardRows;
  return Offset(
    padSide + col * cellW + cellW / 2,
    padTop + row * cellH + cellH / 2,
  );
}

/// 그 칸에 카드를 놓을 수 있는가.
///
/// 🔴 **격자 12칸 중 골키퍼 줄은 가운데 하나뿐이다**(사용자 규칙, 2026-09-21).
/// 나머지 세 줄(FW·MF·DF)은 **세 칸 다** 쓸 수 있다 — 자리 다섯은 포메이션이
/// 처음 배치일 뿐이고 격자 위를 돌아다닌다.
///
/// 골키퍼 줄 양옆을 막는 이유: 골키퍼는 한 명이고, 양옆에 세우면 판이 무엇을
/// 뜻하는지 읽히지 않는다.
bool canDropAt(int col, int row) => row != kBoardRows - 1 || col == 1;

/// 그 행이 뜻하는 포지션. 🔴 **자리를 옮기면 포지션도 함께 바뀐다** —
/// 계약이 `position_code` 를 늘 요구하므로 옮길 때 이 값을 실어 보낸다.
String positionOfRow(int row) => const ['FW', 'MF', 'DF', 'GK'][row];
