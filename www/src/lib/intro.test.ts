import { shouldPlayIntro } from './intro'

describe('인트로 재생 규칙', () => {
  it('앱 진입에서는 재생한다', () => {
    expect(shouldPlayIntro('/', false)).toBe(true)
    expect(shouldPlayIntro('/login', false)).toBe(true)
  })

  it('공개 카드 링크에서는 재생하지 않는다 — 공유 링크의 목적을 깨뜨린다', () => {
    expect(shouldPlayIntro('/c/hong-gildong-4f2a', false)).toBe(false)
  })

  it('이미 본 세션에서는 재생하지 않는다', () => {
    expect(shouldPlayIntro('/', true)).toBe(false)
    expect(shouldPlayIntro('/login', true)).toBe(false)
  })

  it('로그인한 화면에서는 재생하지 않는다', () => {
    expect(shouldPlayIntro('/home', false)).toBe(false)
    expect(shouldPlayIntro('/me', false)).toBe(false)
  })
})
