import { beforeEach, describe, expect, it } from 'vitest'
import {
  JUDGE_SEATS,
  __resetJudgeSeat,
  judgeEmail,
  judgeNickname,
  judgeSeat,
  judgeSeats,
  setJudgeSeat,
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

  /**
   * 🔴 **사람이 고르면 그쪽이 이긴다** (사용자 요청, 2026-09-18: 「선택
   * 가능하게 해줘. 지금은 랜덤이네」). 무작위는 **처음 배정**에만 남는다.
   */
  it('고른 번호가 그대로 남는다', () => {
    judgeSeat() // 먼저 무작위로 하나 배정된 상태에서
    expect(setJudgeSeat(7)).toBe(7)
    expect(readJudgeSeat()).toBe(7)
    expect(judgeSeat()).toBe(7) // 이미 있으니 다시 안 고른다
  })

  it('고를 수 있는 번호가 1~10 으로 나온다', () => {
    expect(judgeSeats()).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    expect(judgeSeats()).toHaveLength(JUDGE_SEATS)
  })

  /* 🔴 없는 번호를 기억해 두면 그 계정이 없어 **로그인 단추가 가입부터**
     시도하고, 시연 자리에서 팀도 판도 없는 빈 계정이 생긴다. */
  it('🔴 범위 밖은 안 바꾸고 null 을 돌려준다', () => {
    setJudgeSeat(3)
    for (const bad of [0, -1, 11, 99, 1.5, Number.NaN]) {
      expect(setJudgeSeat(bad)).toBeNull()
      expect(readJudgeSeat()).toBe(3)
    }
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
