'use client'

/**
 * **심사위원 계정을 브라우저마다 하나씩 배정한다** (사용자 요청, 2026-09-18).
 *
 * 전에는 심사위원이 **한 계정을 나눠 썼다.** 동시 접속이 막히지는 않지만
 * 판·알림·초대를 통째로 공유해서, 한 사람이 카드를 옮기면 다른 사람 화면에도
 * 그대로 갔다. 심사 자리에서 서로의 화면을 건드리는 셈이다.
 *
 * 🔴 **서버는 안 건드린다.** 「사용 중」을 서버에 적으려면 테이블과
 * 마이그레이션이 필요한데, 시연 하루 쓰자고 스키마를 늘릴 일이 아니다.
 * 대신 **계정을 여러 개 미리 만들어 두고** 브라우저가 하나를 골라 기억한다.
 *
 * 🔴 **한 번 고른 것을 계속 쓴다.** 매번 새로 고르면 새로고침할 때마다 다른
 * 팀이 떠서 「내가 짜 둔 판이 사라졌다」가 된다.
 *
 * ⚠️ **완전한 배타는 아니다** — 둘이 같은 번호를 뽑을 수 있다(10개면 드물다).
 * 그래서 화면에 **번호를 보여 준다**: 같은 번호를 든 사람이 보이면 한쪽이
 * 「다른 계정으로」를 눌러 옮기면 된다.
 */

/** 미리 만들어 둔 심사위원 계정 수. 운영 데이터와 **같아야 한다**. */
export const JUDGE_SEATS = 10

const KEY = 'ss-judge-seat-v1'

/** `3` → `judge-03@super-sub.example`. 운영에 만들어 둔 것과 같은 규칙이다. */
export function judgeEmail(seat: number): string {
  return `judge-${String(seat).padStart(2, '0')}@super-sub.example`
}

export function judgeNickname(seat: number): string {
  return `심사위원 ${seat}`
}

function read(): number | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.localStorage.getItem(KEY)
    const n = raw ? Number(raw) : NaN
    return Number.isInteger(n) && n >= 1 && n <= JUDGE_SEATS ? n : null
  } catch {
    return null
  }
}

function write(seat: number): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(KEY, String(seat))
  } catch {
    /* 저장이 막혀도 이번 로그인은 된다 — 다음에 다른 번호가 될 뿐이다. */
  }
}

/**
 * 이미 배정된 번호만 읽는다 — 🔴 **고르지는 않는다.** 로그인 화면을 열어
 * 보기만 한 사람에게 번호를 물리면, 실제로 쓰는 사람보다 먼저 자리를 차지한다.
 */
export function readJudgeSeat(): number | null {
  return read()
}

/**
 * 이 브라우저의 심사위원 번호. 없으면 **무작위로 하나 골라 기억한다.**
 *
 * 🔴 무작위인 이유: 순서대로 주면 **모두가 1번부터** 집어 곧바로 부딪힌다.
 */
export function judgeSeat(): number {
  const now = read()
  if (now !== null) return now
  const picked = Math.floor(Math.random() * JUDGE_SEATS) + 1
  write(picked)
  return picked
}

/**
 * **다른 번호로 옮긴다** — 지금 것을 빼고 그중에서 고른다.
 *
 * 같은 번호를 든 사람을 만났을 때 쓴다. 🔴 지금 번호는 후보에서 뺀다 —
 * 안 빼면 「눌렀는데 그대로」가 나온다.
 */
export function nextJudgeSeat(): number {
  const now = read()
  const others = Array.from({ length: JUDGE_SEATS }, (_, i) => i + 1).filter(
    (n) => n !== now,
  )
  const picked = others[Math.floor(Math.random() * others.length)] ?? 1
  write(picked)
  return picked
}

/** 시험에서만 쓴다. */
export function __resetJudgeSeat(): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.removeItem(KEY)
  } catch {
    /* 비우지 못해도 시험은 각자 칸을 지운다. */
  }
}
