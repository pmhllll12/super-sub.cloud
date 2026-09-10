/**
 * 스쿼드 판의 **격자 규칙** — 열·행·행이 정하는 포지션.
 *
 * 🔴 **정본은 계약 3-7절 「홈 판 격자」다.** 지금 판은 3열(0~2) × 4행(0~3)이고
 * **행이 포지션 라인**이다 — 0 FW · 1 MF · 2 DF · 3 GK. 서버에 저장되는
 * `grid_col`·`grid_row` 가 이 뜻을 갖는다.
 *
 * 🔴 **왜 `SquadPanel` 에서 뺐나** — 대기 팝업의 읽기 전용 판(`MiniPitch`)이
 * 같은 규칙을 써야 하는데, 그쪽이 `SquadPanel` 을 import 하면 **순환**이 된다
 * (`SquadPanel` → `MatchWaiting` → `MiniPitch` → `SquadPanel`). 규칙을 두 벌로
 * 베끼면 한쪽만 고쳐져 **판마다 포지션이 갈린다.**
 *
 * 🔴 **격자 크기·행 의미가 바뀌면 저장된 값의 뜻도 바뀐다** — 그때는 서버 쪽
 * 리매핑이 필요하다(계약이 그렇게 적어 두었다).
 */

/** 계약이 정한 축구 포지션 넷(3-4절). 새 코드를 만들지 않는다. */
export type PosCode = 'FW' | 'MF' | 'DF' | 'GK'

/** 🔴 **행이 포지션을 정한다** — 위가 공격이다. */
export const ROW_POS: PosCode[] = ['FW', 'MF', 'DF', 'GK']

/** 판의 격자. 열 셋 · 행 넷. */
export const COLS = 3
export const ROWS = ROW_POS.length

/**
 * 🔴 **골키퍼 줄은 가운데 한 칸뿐이다.** 축구에서 골키퍼는 하나이고 골대 앞
 * 가운데에 선다 — 양옆 칸을 두면 판이 "골키퍼가 셋일 수도 있다"고 말하는
 * 셈이 된다. 그래서 그 줄에서는 가운데만 그린다.
 */
export const GK_ROW = ROW_POS.indexOf('GK')
export const GK_COL = 1

/** 이 칸이 격자에 존재하는가 — 골키퍼 줄의 양옆은 아예 없다. */
export function cellExists(col: number, row: number): boolean {
  return row !== GK_ROW || col === GK_COL
}

/** 그 행이 정하는 포지션. */
export function rowPos(row: number): PosCode {
  return ROW_POS[Math.min(row, ROWS - 1)]
}
