'use client'

/**
 * **「지금 팀을 찾는 중이다」를 브라우저에 남긴다** (사용자 요청, 2026-09-18:
 * "팀매칭을 시작하면 다른페이지로 이동해도 여전히 찾고있는 상태를 유지").
 *
 * 🔴 **경기 조건은 여기 두지 않는다.** 조건(지역·시간)은 **서버**에 있고
 * (`teamPrefsStore.ts` · 계약 3-13절), 그것이 「우리 팀이 남에게 보이는」
 * 근거다. 전에 조건을 `localStorage` 에 뒀다가 **화면상으로는 설정이 끝난
 * 것처럼 보이는데 남의 후보 목록에 아예 안 뜨는** 일이 있었다 — 그 실수를
 * 되풀이하지 않는다.
 *
 * 여기 남기는 것은 **이 브라우저의 화면 상태 하나**다: 「찾기를 시작했고
 * 아직 그만두지 않았다」. 그래서 잃어도 조건은 안 잃는다 — 다시 켜면 된다.
 *
 * | | |
 * |---|---|
 * | **서버** | 경기 조건 · 후보 목록 — 남에게 보이는 것 |
 * | **여기(브라우저)** | 찾는 중인가 · 어느 후보까지 봤는가 — 나에게만 |
 */

/** 저장 칸 이름. 값 모양이 바뀌면 이름을 바꾼다(옛 값을 읽지 않게). */
const KEY = 'ss-team-seeking-v1'

/**
 * 같은 탭 안의 다른 컴포넌트에게 바뀐 것을 알리는 신호.
 *
 * 🔴 브라우저의 `storage` 이벤트는 **다른 탭**에서만 온다 — 같은 탭에서
 * 쓴 값은 안 알려 준다. 머리칸의 표시와 홈의 판이 같은 탭에 있으므로
 * 이것이 없으면 한쪽이 안 따라온다.
 */
const CHANGED = 'ss-team-seeking-changed'

export type Seeking = {
  /** 어느 팀으로 찾고 있는가 — 주장인 팀이다. */
  teamId: string
  /** 언제 시작했는가(ms). 표시용이고 판단에는 안 쓴다. */
  startedAt: number
  /**
   * **이미 본 후보 팀 id** — 새로 생긴 팀만 알리려고 들고 있다.
   *
   * 🔴 「몇 곳이었나」로 세지 않는다. 한 곳이 빠지고 다른 곳이 들어오면
   * 수는 그대로인데 **새 팀은 생긴 것**이라, 수로 세면 그것을 놓친다.
   */
  seen: string[]
}

function readRaw(): Seeking | null {
  /* 🔴 서버에서 그릴 때는 `window` 가 없다. 그리고 사생활 보호 창·저장소
     차단에서는 접근 자체가 던진다 — 둘 다 「안 찾는 중」으로 읽는다. */
  if (typeof window === 'undefined') return null
  try {
    const raw = window.localStorage.getItem(KEY)
    if (!raw) return null
    const value = JSON.parse(raw) as Partial<Seeking> | null
    if (!value || typeof value.teamId !== 'string' || !value.teamId) return null
    return {
      teamId: value.teamId,
      startedAt: typeof value.startedAt === 'number' ? value.startedAt : Date.now(),
      seen: Array.isArray(value.seen) ? value.seen.filter((x) => typeof x === 'string') : [],
    }
  } catch {
    return null
  }
}

function write(next: Seeking | null): void {
  if (typeof window === 'undefined') return
  try {
    if (next) window.localStorage.setItem(KEY, JSON.stringify(next))
    else window.localStorage.removeItem(KEY)
  } catch {
    /* 저장이 막혀도 이번 화면은 계속 돌아야 한다 — 다음 이동에서 잊힐 뿐이다. */
  }
  window.dispatchEvent(new Event(CHANGED))
}

/** 지금 찾는 중인가. 아니면 `null`. */
export function readSeeking(): Seeking | null {
  return readRaw()
}

/**
 * **찾기를 시작한다.** 이미 찾고 있던 팀이면 「본 후보」를 그대로 둔다 —
 * 조건만 고친 것인데 이미 본 팀을 새것이라고 다시 알리면 안 된다.
 */
export function startSeeking(teamId: string): void {
  const now = readRaw()
  write(
    now && now.teamId === teamId
      ? now
      : { teamId, startedAt: Date.now(), seen: [] },
  )
}

/** **그만 찾는다.** 조건은 서버에 그대로 남는다 — 지우는 것이 아니다. */
export function stopSeeking(): void {
  write(null)
}

/**
 * 지금 보이는 후보를 **봤다고 표시**한다. 다음부터 이 팀들은 「새로 생긴
 * 팀」이 아니다.
 */
export function markSeen(ids: string[]): void {
  const now = readRaw()
  if (!now) return
  const merged = Array.from(new Set([...now.seen, ...ids]))
  write({ ...now, seen: merged })
}

/** 바뀔 때마다 부른다. 같은 탭(`CHANGED`)과 다른 탭(`storage`) 둘 다 듣는다. */
export function subscribe(run: () => void): () => void {
  if (typeof window === 'undefined') return () => {}
  const onStorage = (e: StorageEvent) => {
    if (e.key === null || e.key === KEY) run()
  }
  window.addEventListener(CHANGED, run)
  window.addEventListener('storage', onStorage)
  return () => {
    window.removeEventListener(CHANGED, run)
    window.removeEventListener('storage', onStorage)
  }
}

/** 시험에서만 쓴다 — 칸을 비운다. */
export function __resetSeeking(): void {
  write(null)
}

/* ── 잡힌 경기 화면을 다시 여는 「부탁」 ─────────────────────────────────
   머리칸 표시는 **모든 화면**에 있는데 경기 화면을 그리는 것은 **홈의 판**
   하나뿐이다. 그래서 홈이 아닌 데서 누르면 「열어 달라」를 여기 적어 두고
   홈으로 보낸다 — 홈이 그것을 집어 열고 지운다. 한 번 쓰고 버리는 값이다. */

const OPEN_KEY = 'ss-open-match-v1'

/** 홈에 가면 그 경기 화면을 열어 달라고 적어 둔다. */
export function requestMatchOpen(matchId: string): void {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.setItem(OPEN_KEY, matchId)
  } catch {
    /* 못 적으면 홈으로 가기만 한다 — 표시를 한 번 더 누르면 된다. */
  }
}

/**
 * 적어 둔 부탁을 **집어 가며 지운다.**
 *
 * 🔴 지우는 것이 핵심이다 — 안 지우면 그 뒤로 홈에 들어올 때마다 경기 화면이
 * 저절로 뜬다. 「누를 때만 뜬다」가 이 기능의 규칙이다.
 *
 * 🔴 `sessionStorage` 다 — 탭을 닫으면 사라지는 **한 번 쓰는 부탁**이라
 * 브라우저에 오래 남을 이유가 없다(찾는 중 표시와 다르다).
 */
export function takeMatchOpen(): string | null {
  if (typeof window === 'undefined') return null
  try {
    const id = window.sessionStorage.getItem(OPEN_KEY)
    if (id) window.sessionStorage.removeItem(OPEN_KEY)
    return id
  } catch {
    return null
  }
}
