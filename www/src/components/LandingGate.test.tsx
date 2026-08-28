import { render } from '@testing-library/react'
import LandingGate from './LandingGate'
import { INTRO_DONE_EVENT, INTRO_SEEN_KEY } from '@/lib/intro'

const replace = vi.fn()

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace }),
}))

describe('LandingGate — / 에서 로그인 후 이동 판단', () => {
  beforeEach(() => {
    replace.mockClear()
    sessionStorage.clear()
  })

  it('로그아웃 상태면 인트로가 끝나도 아무 데도 보내지 않는다 — 랜딩이 그대로 보인다', () => {
    render(<LandingGate loggedIn={false} />)
    window.dispatchEvent(new Event(INTRO_DONE_EVENT))
    expect(replace).not.toHaveBeenCalled()
  })

  it('로그인 상태로 / 에 들어가면 인트로가 재생되고(즉시 이동하지 않고) 그 뒤 /home 으로 간다', () => {
    render(<LandingGate loggedIn={true} />)
    // 인트로가 재생되는 동안(끝나기 전)에는 아직 이동하지 않는다.
    expect(replace).not.toHaveBeenCalled()

    // IntroGate가 인트로를 마치며 쏘는 신호.
    window.dispatchEvent(new Event(INTRO_DONE_EVENT))

    expect(replace).toHaveBeenCalledWith('/home')
    expect(replace).toHaveBeenCalledTimes(1)
  })

  it('이미 이번 세션에서 인트로를 본 뒤라면(재생되지 않으므로) 곧바로 /home 으로 간다', () => {
    sessionStorage.setItem(INTRO_SEEN_KEY, '1')
    render(<LandingGate loggedIn={true} />)
    expect(replace).toHaveBeenCalledWith('/home')
  })
})
