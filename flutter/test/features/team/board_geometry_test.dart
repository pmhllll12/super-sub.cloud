import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:super_sub/features/team/board_geometry.dart';

// 판 안 여백은 SquadBoard 의 값과 같다.
const _padTop = 44.0;
const _padSide = 12.0;
const _padBottom = 6.0;
const _size = Size(360, 700);

({int col, int row})? _cell(double x, double y) => cellAt(
      Offset(x, y),
      _size,
      padTop: _padTop,
      padSide: _padSide,
      padBottom: _padBottom,
    );

void main() {
  test('격자는 3열 × 4행이다', () {
    // 🔴 계약 3-7절이 이 값의 정본이다 — 바꾸면 저장된 값의 뜻이 바뀐다.
    expect(kBoardCols, 3);
    expect(kBoardRows, 4);
  });

  test('왼쪽 위 첫 칸은 (0, 0)', () {
    expect(_cell(_padSide + 1, _padTop + 1), (col: 0, row: 0));
  });

  test('가운데 칸을 짚는다', () {
    final gridW = _size.width - _padSide * 2;
    final gridH = _size.height - _padTop - _padBottom;
    final x = _padSide + gridW / 2;
    final y = _padTop + gridH / 2;

    expect(_cell(x, y), (col: 1, row: 2));
  });

  test('오른쪽 아래 끝은 마지막 칸이다', () {
    // 🔴 끝에 정확히 닿으면 한 칸 넘어간다 — 묶어야 한다.
    expect(
      _cell(_size.width - _padSide - 0.01, _size.height - _padBottom - 0.01),
      (col: 2, row: 3),
    );
  });

  group('판 밖이면 null — 놓을 자리가 없다', () {
    test('위 여백(머리글 자리)', () {
      expect(_cell(100, _padTop - 1), isNull);
    });

    test('왼쪽 여백', () {
      expect(_cell(_padSide - 1, 100), isNull);
    });

    test('아래 여백', () {
      expect(_cell(100, _size.height - _padBottom + 1), isNull);
    });

    test('오른쪽 밖', () {
      expect(_cell(_size.width + 5, 100), isNull);
    });
  });

  test('판이 찌그러져 있으면 null 이다', () {
    // 키보드가 올라오거나 창이 아주 낮으면 격자가 음수가 된다.
    expect(
      cellAt(
        const Offset(10, 10),
        const Size(360, 20),
        padTop: _padTop,
        padSide: _padSide,
        padBottom: _padBottom,
      ),
      isNull,
    );
  });

  test('칸의 왼쪽 위 모서리를 돌려준다', () {
    final origin = cellOrigin(
      0,
      0,
      _size,
      padTop: _padTop,
      padSide: _padSide,
      padBottom: _padBottom,
    );

    expect(origin.dx, _padSide);
    expect(origin.dy, _padTop);
  });

  test('cellAt 과 cellOrigin 이 서로 맞는다', () {
    for (var col = 0; col < kBoardCols; col += 1) {
      for (var row = 0; row < kBoardRows; row += 1) {
        final o = cellOrigin(
          col,
          row,
          _size,
          padTop: _padTop,
          padSide: _padSide,
          padBottom: _padBottom,
        );
        expect(_cell(o.dx + 1, o.dy + 1), (col: col, row: row),
            reason: '($col, $row)');
      }
    }
  });

  test('행이 포지션 라인이다', () {
    expect(positionOfRow(0), 'FW');
    expect(positionOfRow(1), 'MF');
    expect(positionOfRow(2), 'DF');
    expect(positionOfRow(3), 'GK');
  });
}
