import { render, waitFor } from '@testing-library/react'
import { useEffect } from 'react'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}))

// next/script 는 실제 브라우저에서만 <script> 로드 이벤트를 쏘므로, jsdom
// 에서는 커밋(마운트) 후 onLoad 를 호출하는 걸로 대체한다 — 렌더 도중에
// 부르면 형제 요소의 ref 가 아직 안 붙어 있어(GoogleSignInButton 의
// wrapperRef/googleContainerRef) 실제 순서와 달라진다. 우리가 검증할 대상은
// "스크립트가 로드된 뒤 초기화/렌더가 일어나는가"이지 next/script 자체의
// 로딩 동작이 아니다.
vi.mock('next/script', () => ({
  default: function MockScript({ onLoad }: { onLoad?: () => void }) {
    useEffect(() => {
      onLoad?.()
      // eslint-disable-next-line react-hooks/exhaustive-deps -- 마운트 시 1회만
    }, [])
    return null
  },
}))

describe('GoogleSignInButton', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.resetModules()
    delete (window as unknown as { google?: unknown }).google
  })

  it('NEXT_PUBLIC_GOOGLE_CLIENT_ID 가 없으면 아무것도 그리지 않는다', async () => {
    vi.stubEnv('NEXT_PUBLIC_GOOGLE_CLIENT_ID', '')
    const { default: GoogleSignInButton } = await import('./GoogleSignInButton')
    const { container } = render(<GoogleSignInButton onError={() => {}} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('NEXT_PUBLIC_GOOGLE_CLIENT_ID 가 있으면 구글 identity services 를 초기화하고 renderButton(팝업 방식)을 호출한다', async () => {
    vi.stubEnv('NEXT_PUBLIC_GOOGLE_CLIENT_ID', 'test-client-id.apps.googleusercontent.com')
    const initialize = vi.fn()
    const renderButton = vi.fn()
    window.google = { accounts: { id: { initialize, renderButton } } }

    const { default: GoogleSignInButton } = await import('./GoogleSignInButton')
    render(<GoogleSignInButton onError={() => {}} />)

    await waitFor(() => {
      expect(initialize).toHaveBeenCalledWith(
        expect.objectContaining({ client_id: 'test-client-id.apps.googleusercontent.com' }),
      )
    })
    expect(renderButton).toHaveBeenCalledTimes(1)
    const [, options] = renderButton.mock.calls[0]
    // One Tap(prompt) 이 아니라 팝업 방식이어야 하고, access_token 이 아니라
    // id_token 을 주는 accounts.id 계열이어야 한다. 구글 브랜드 마크/문구는
    // 우리가 임의로 바꾸지 않는다 — 표준 옵션만 넘기는지 확인한다.
    expect(options).toEqual(
      expect.objectContaining({
        theme: 'outline',
        shape: 'pill',
        size: 'large',
        text: 'signin_with',
        locale: 'ko',
      }),
    )
  })

  it('text prop 으로 문구를 바꿀 수 있다(회원가입 화면의 signup_with)', async () => {
    vi.stubEnv('NEXT_PUBLIC_GOOGLE_CLIENT_ID', 'test-client-id.apps.googleusercontent.com')
    const initialize = vi.fn()
    const renderButton = vi.fn()
    window.google = { accounts: { id: { initialize, renderButton } } }

    const { default: GoogleSignInButton } = await import('./GoogleSignInButton')
    render(<GoogleSignInButton onError={() => {}} text="signup_with" />)

    await waitFor(() => {
      expect(renderButton).toHaveBeenCalledTimes(1)
    })
    const [, options] = renderButton.mock.calls[0]
    expect(options).toEqual(expect.objectContaining({ text: 'signup_with' }))
  })

  // 🔴 회귀 방지 — 2026-08-28.
  // 한때 우리 PillButton 모양 장식을 그리고 구글 버튼을 opacity:0 으로 그 위에
  // 겹쳤다. 구글은 버튼이 실제로 보이지 않으면 클릭을 무시한다(클릭재킹 방지).
  // 콘솔에 에러 한 줄도 안 남고 그냥 무반응이라 원인 찾기가 아주 어렵다.
  it('구글 버튼을 감추거나 덮지 않는다 — 투명 오버레이/장식 버튼을 두지 않는다', async () => {
    vi.stubEnv('NEXT_PUBLIC_GOOGLE_CLIENT_ID', 'test-client-id.apps.googleusercontent.com')
    const renderButton = vi.fn((parent: HTMLElement) => {
      parent.appendChild(document.createElement('div'))
    })
    window.google = { accounts: { id: { initialize: vi.fn(), renderButton } } }

    const { default: GoogleSignInButton } = await import('./GoogleSignInButton')
    const { container } = render(<GoogleSignInButton onError={() => {}} />)

    await waitFor(() => {
      expect(renderButton).toHaveBeenCalledTimes(1)
    })

    // 투명하게 만드는 어떤 장치도 없어야 한다.
    expect(container.querySelector('[class*="opacity-0"]')).toBeNull()
    expect(container.querySelector('[style*="opacity"]')).toBeNull()
    // 구글 버튼을 가릴 형제(장식 버튼)도 두지 않는다 — 구글이 그린 것 하나뿐이다.
    expect(container.querySelector('[aria-hidden="true"]')).toBeNull()
    const wrapper = container.querySelector('[data-testid="google-signin-wrapper"]') as HTMLElement
    expect(wrapper.children).toHaveLength(1)
  })

  it('카드 폭에 맞춰 구글 버튼 폭을 픽셀로 넘기고, 리사이즈되면 다시 그린다', async () => {
    vi.stubEnv('NEXT_PUBLIC_GOOGLE_CLIENT_ID', 'test-client-id.apps.googleusercontent.com')
    const renderButton = vi.fn()
    window.google = { accounts: { id: { initialize: vi.fn(), renderButton } } }

    const { default: GoogleSignInButton } = await import('./GoogleSignInButton')
    const { container } = render(<GoogleSignInButton onError={() => {}} />)

    const wrapper = container.querySelector('[data-testid="google-signin-wrapper"]') as HTMLElement
    // jsdom 은 레이아웃을 계산하지 않아 offsetWidth 가 늘 0이다 — 실제 폭을 흉내낸다.
    Object.defineProperty(wrapper, 'offsetWidth', { value: 320, configurable: true })

    await waitFor(() => {
      expect(renderButton).toHaveBeenCalledTimes(1)
    })

    window.dispatchEvent(new Event('resize'))

    await waitFor(() => {
      expect(renderButton).toHaveBeenCalledTimes(2)
    })
    const [, options] = renderButton.mock.calls[1]
    expect(options).toEqual(expect.objectContaining({ width: '320' }))
  })
})
