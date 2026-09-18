import { beforeEach, describe, expect, it } from 'vitest'
import {
  JUDGE_SEATS,
  __resetJudgeSeat,
  judgeEmail,
  judgeNickname,
  judgeSeat,
  nextJudgeSeat,
  readJudgeSeat,
} from './judgeSeat'

/**
 * 🔴 **심사위원이 한 계정을 나눠 쓰던 것**을 푼 자리(사용자 요청, 2026-09-18).
 * 동시 접속이 막히지는 않지만 판·알림·초대를 공유해서 서로의 화면을 건드렸다.
 */
describe('심사위원 자리 배정', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('이메일·별명이 번호에서 나온다 — 운영에 만들어 둔 규칙과 같아야 한다', () => {
    expect(judgeEmail(1)).toBe('judge-01@super-sub.example')
    expect(judgeEmail(10)).toBe('judge-10@super-sub.example')
    expect(judgeNickname(3)).toBe('심사위원 3')
  })

  it('🔴 열어 보기만 하면 자리를 안 차지한다', () => {
    expect(readJudgeSeat()).toBeNull()
    expect(window.localStorage.getItem('ss-judge-seat-v1')).toBeNull()
  })

  it('처음 쓸 때 하나를 골라 기억한다', () => {
    const n = judgeSeat()
    expect(n).toBeGreaterThanOrEqual(1)
    expect(n).toBeLessThanOrEqual(JUDGE_SEATS)
    expect(readJudgeSeat()).toBe(n)
  })

  it('🔴 한 번 고른 것을 계속 쓴다 — 새로고침마다 바뀌면 짜 둔 판이 사라진다', () => {
    const first = judgeSeat()
    for (let i = 0; i < 20; i += 1) expect(judgeSeat()).toBe(first)
  })

  it('🔴 「바꾸기」는 **지금 것을 뺀** 나머지에서 고른다', () => {
    const first = judgeSeat()
    for (let i = 0; i < 20; i += 1) {
      const before = readJudgeSeat()
      const next = nextJudgeSeat()
      expect(next).not.toBe(before)
      expect(next).toBeGreaterThanOrEqual(1)
      expect(next).toBeLessThanOrEqual(JUDGE_SEATS)
    }
    expect(first).toBeGreaterThanOrEqual(1)
  })

  it('저장된 값이 범위 밖이면 없는 것으로 읽는다', () => {
    window.localStorage.setItem('ss-judge-seat-v1', '99')
    expect(readJudgeSeat()).toBeNull()
    window.localStorage.setItem('ss-judge-seat-v1', 'abc')
    expect(readJudgeSeat()).toBeNull()
  })

  it('__resetJudgeSeat 이 칸을 비운다', () => {
    judgeSeat()
    __resetJudgeSeat()
    expect(readJudgeSeat()).toBeNull()
  })
})
