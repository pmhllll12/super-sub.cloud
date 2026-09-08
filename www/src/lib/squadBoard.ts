/**
 * 스쿼드 판을 **그 브라우저에 남긴다** — 판 크기 · 카드가 선 자리 · 손으로 정한
 * 포지션 · 앉은 사람.
 *
 * 🔴 **`SquadPanel` 의 "브라우저 저장은 일부러 안 넣었다"를 이번에 뒤집는다**
 * (사용자 요청, 2026-09-08). 그때 적어 둔 이유는 *"서버가 진짜가 되는 순간
 * 상태가 두 곳에 생겨 어느 쪽이 맞는지 헷갈린다"* 였는데, 그 사이에 판이
 * **서버가 모르는 것들**을 갖게 됐다:
 *
 *   - 판 크기(3:3 · 5:5 · 7:7) — 계약에 없다
 *   - 카드가 선 **칸** — 계약에 없다(`squad_member` 는 `position_code` 뿐이다)
 *   - 손으로 정한 포지션 — 자리에서 역산되지 않는다
 *
 * 그리고 넣기 · 빼기가 아직 서버로 안 간다. 저장이 없으면 다른 화면에 갔다
 * 오기만 해도 판이 통째로 처음으로 돌아가, 기능이 성립하지 않는다.
 * (`me/cardStyleStore.ts` 가 같은 판단을 같은 이유로 했다.)
 *
 * ⚠️ **그 브라우저에만 남는다.** 다른 기기에서는 안 보인다 — 화면에도 그렇게
 * 적어 둔다(숨기면 고장으로 읽힌다).
 *
 * 🔴 서버에 자리가 생기면 **이 파일만 갈아 끼운다.** 부르는 쪽은 아래 두
 * 함수만 안다.
 */

export type SavedSlot = {
  /** 자리 이름(`fw1` · `mf2` …). 사람과 손으로 정한 포지션을 붙들고 있는 값이다. */
  area: string
  col: number
  row: number
  /** 손으로 정한 포지션. 없으면 자리(행)가 정한다. */
  pos: string | null
  mine?: boolean
}

export type SavedBoard = {
  size: string
  slots: SavedSlot[]
  /** 자리 이름 → 앉은 사람의 닉네임. */
  mates: Record<string, string | null>
}

const KEY = 'supersub.squad.v1'

/**
 * 🔴 **읽기는 언제나 실패할 수 있다** — 사생활 보호 창 · 저장 공간 꽉 참 ·
 * 남이 넣어 둔 깨진 값. 어느 쪽이든 판이 안 그려지면 안 된다.
 * ⚠️ 이 jsdom 조합은 `localStorage` 를 안 깔아 준다(`vitest.setup.ts` 참고).
 */
export function loadBoard(): SavedBoard | null {
  try {
    const raw = globalThis.localStorage?.getItem(KEY)
    if (!raw) return null
    const v: unknown = JSON.parse(raw)
    if (!v || typeof v !== 'object') return null
    const b = v as Partial<SavedBoard>
    // 모양이 어긋나면 없는 것으로 친다 — 반쪽짜리로 그리면 더 헷갈린다.
    if (typeof b.size !== 'string' || !Array.isArray(b.slots) || !b.slots.length) return null
    if (!b.slots.every((s) => s && typeof s.area === 'string' && Number.isFinite(s.col))) {
      return null
    }
    return { size: b.size, slots: b.slots, mates: b.mates ?? {} }
  } catch {
    return null
  }
}

export function saveBoard(board: SavedBoard): void {
  try {
    globalThis.localStorage?.setItem(KEY, JSON.stringify(board))
  } catch {
    // 못 써도 판은 계속 돈다 — 저장이 이 화면의 본업이 아니다.
  }
}
