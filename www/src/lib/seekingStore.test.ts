import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  __resetSeeking,
  isMatchDone,
  markMatchDone,
  markSeen,
  readSeeking,
  startSeeking,
  stopSeeking,
  subscribe,
} from './seekingStore'

describe('seekingStore — 「팀 찾는 중」을 브라우저에 남긴다', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it('안 시작했으면 null 이다', () => {
    expect(readSeeking()).toBeNull()
  })

  it('시작하면 그 팀으로 남고, 그만두면 사라진다', () => {
    startSeeking('t1')
    expect(readSeeking()?.teamId).toBe('t1')
    stopSeeking()
    expect(readSeeking()).toBeNull()
  })

  it('🔴 같은 팀으로 다시 시작해도 「본 후보」를 안 지운다', () => {
    /* 조건만 고치고 다시 「팀 찾기」를 누른 경우다. 여기서 비우면 이미 본
       팀들이 전부 「새로 생긴 팀」으로 다시 알려진다. */
    startSeeking('t1')
    markSeen(['a', 'b'])
    startSeeking('t1')
    expect(readSeeking()?.seen).toEqual(['a', 'b'])
  })

  it('🔴 다른 팀으로 시작하면 「본 후보」를 비운다', () => {
    /* 팀이 바뀌면 후보 집합 자체가 다른 것이라, 들고 가면 새 팀의 후보가
       이미 본 것으로 잘못 묻힌다. */
    startSeeking('t1')
    markSeen(['a'])
    startSeeking('t2')
    expect(readSeeking()?.seen).toEqual([])
  })

  it('본 후보는 겹치지 않게 쌓인다', () => {
    startSeeking('t1')
    markSeen(['a', 'b'])
    markSeen(['b', 'c'])
    expect(readSeeking()?.seen).toEqual(['a', 'b', 'c'])
  })

  it('안 찾는 중이면 markSeen 이 아무것도 안 만든다', () => {
    markSeen(['a'])
    expect(readSeeking()).toBeNull()
  })

  it('🔴 같은 탭에서 바뀌어도 알려 준다 — storage 이벤트는 다른 탭에만 온다', () => {
    const run = vi.fn()
    const off = subscribe(run)
    startSeeking('t1')
    expect(run).toHaveBeenCalled()
    off()
    const before = run.mock.calls.length
    stopSeeking()
    expect(run.mock.calls.length).toBe(before)
  })

  it('저장된 값이 깨져 있으면 안 찾는 중으로 읽는다', () => {
    window.localStorage.setItem('ss-team-seeking-v1', '{{{')
    expect(readSeeking()).toBeNull()
    window.localStorage.setItem('ss-team-seeking-v1', JSON.stringify({ teamId: '' }))
    expect(readSeeking()).toBeNull()
  })

  it('🔴 끝낸 경기를 기억한다 — 머리칸 표시에서 빼려는 것', () => {
    expect(isMatchDone('m1')).toBe(false)
    markMatchDone('m1')
    expect(isMatchDone('m1')).toBe(true)
    /* 다른 경기는 그대로다 — 하나 끝냈다고 전부 감추면 안 된다. */
    expect(isMatchDone('m2')).toBe(false)
  })

  it('같은 경기를 두 번 적어도 한 번만 쌓인다', () => {
    markMatchDone('m1')
    markMatchDone('m1')
    const raw = JSON.parse(window.localStorage.getItem('ss-finished-matches-v1') ?? '[]')
    expect(raw).toEqual(['m1'])
  })

  it('빈 id 는 안 적는다 — 없는 경기를 끝냈다고 하지 않는다', () => {
    markMatchDone('')
    expect(window.localStorage.getItem('ss-finished-matches-v1')).toBeNull()
  })

  it('__resetSeeking 이 칸을 비운다', () => {
    startSeeking('t1')
    __resetSeeking()
    expect(readSeeking()).toBeNull()
  })
})
