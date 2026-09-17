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

/** 판 크기 — 풋살 5인이 기본이다. */
export type SquadSize = '3' | '5' | '7'

/** 포메이션의 자리 하나. `area` 는 역할+번호(크기를 바꿔도 같은 사람이 제자리). */
export type SlotSpec = { area: string; col: number; row: number }

/**
 * 🔴 **크기마다 설 수 있는 자리는 정해져 있다**(사용자 지적, 2026-09-17 —
 * 「위치가 몇 개로 정해져 있는데」). 판은 3×4 격자지만 **아무 칸이나 쓰는
 * 것이 아니다** — 5:5 는 1-2-1 이라 MF 는 왼쪽·오른쪽 둘뿐이고 가운데는
 * MF 자리가 아니다.
 *
 * 🔴 **`SquadPanel` 의 `FORMATIONS` 가 이 표를 쓴다** — 좌표를 두 벌로
 * 베끼면 한쪽만 고쳐져 판마다 자리가 갈린다(이 파일이 있는 이유다).
 */
export const FORMATION_SLOTS: Record<SquadSize, SlotSpec[]> = {
  // 1-1-1 — 셋이면 공격 · 중원 · 골키퍼 하나씩이다.
  '3': [
    { area: 'fw1', col: 1, row: 0 },
    { area: 'mf1', col: 1, row: 1 },
    { area: 'gk', col: 1, row: 3 },
  ],
  // 1-2-1 — 풋살 5인. 이 판이 원래 그리던 것이다.
  '5': [
    { area: 'fw1', col: 1, row: 0 },
    { area: 'mf1', col: 0, row: 1 },
    { area: 'mf2', col: 2, row: 1 },
    { area: 'df1', col: 1, row: 2 },
    { area: 'gk', col: 1, row: 3 },
  ],
  // 2-3-1 — 7인제에서 가장 흔한 형태다.
  '7': [
    { area: 'fw1', col: 1, row: 0 },
    { area: 'mf1', col: 0, row: 1 },
    { area: 'mf2', col: 1, row: 1 },
    { area: 'mf3', col: 2, row: 1 },
    { area: 'df1', col: 0, row: 2 },
    { area: 'df2', col: 2, row: 2 },
    { area: 'gk', col: 1, row: 3 },
  ],
}

/** 처음 여는 크기 — 풋살 5인(사용자 요청). */
export const DEFAULT_SIZE: SquadSize = '5'

/**
 * 서버가 준 `formation`(`"5:5"`)을 판 크기로 읽는다.
 *
 * 🔴 **아직 안 정했으면 `null` 이고 그게 정상이다**(계약 3-7절) — 그때는
 * 기본 크기로 본다. 모르는 값도 마찬가지다.
 */
export function sizeOfFormation(formation: string | null | undefined): SquadSize {
  const head = (formation ?? '').split(':')[0]
  return head === '3' || head === '5' || head === '7' ? head : DEFAULT_SIZE
}
