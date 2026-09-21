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

/// 그 행이 뜻하는 포지션. 🔴 **자리를 옮기면 포지션도 함께 바뀐다** —
/// 계약이 `position_code` 를 늘 요구하므로 옮길 때 이 값을 실어 보낸다.
String positionOfRow(int row) => const ['FW', 'MF', 'DF', 'GK'][row];
