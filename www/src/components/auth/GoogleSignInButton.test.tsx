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

/** 구글이 renderButton 호출 시 실제로 만드는 자식 노드 하나를 흉내낸다.
 * getBoundingClientRect 를 스텁해 "구글이 그려낸 실제 크기"를 지정한다 —
 * jsdom 은 레이아웃을 계산하지 않아 기본값은 전부 0이다. */
function stubRect(el: Element, rect: Partial<DOMRect>) {
  vi.spyOn(el, 'getBoundingClientRect').mockReturnValue({
    x: 0,
    y: 0,
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    width: 0,
    height: 0,
    toJSON() {},
    ...rect,
  } as DOMRect)
}

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

  it('구글 로고 없이 글자만 있는 우리 PillButton 모양 장식을 그리고, 스크린리더에는 감춘다', async () => {
    vi.stubEnv('NEXT_PUBLIC_GOOGLE_CLIENT_ID', 'test-client-id.apps.googleusercontent.com')
    window.google = { accounts: { id: { initialize: vi.fn(), renderButton: vi.fn() } } }

    const { default: GoogleSignInButton } = await import('./GoogleSignInButton')
    const { container } = render(<GoogleSignInButton onError={() => {}} text="signup_with" />)

    const decorative = container.querySelector('[aria-hidden="true"]')
    expect(decorative).not.toBeNull()
    expect(decorative?.textContent).toBe('Google 계정으로 가입')
    // 로고(이미지/아이콘)를 함께 그리지 않는다 — 글자만.
    expect(decorative?.querySelector('img, svg')).toBeNull()
  })

  it('구글이 그린 실제 버튼을 우리 버튼 자리 위에 폭·높이 모두 정확히 겹치도록 스케일을 맞춘다', async () => {
    vi.stubEnv('NEXT_PUBLIC_GOOGLE_CLIENT_ID', 'test-client-id.apps.googleusercontent.com')
    const renderButton = vi.fn((parent: HTMLElement) => {
      // 구글이 실제로 만드는 자식 노드 — 우리 버튼(예: 320×54)보다
      // 작다(예: 200×40)고 가정한다. large 사이즈의 실제 렌더 높이는
      // --ss-btn-h(54px)보다 늘 낮다. 실제 브라우저에서는 자기 크기를
      // 지정하지 않은 parent(googleContainerRef, absolute + shrink-to-fit)
      // 가 이 자식을 그대로 감싸 같은 크기로 측정된다 — jsdom 은 레이아웃을
      // 계산하지 않으므로 parent 쪽도 같은 크기로 함께 스텁해준다.
      const el = document.createElement('div')
      parent.appendChild(el)
      stubRect(el, { width: 200, height: 40, right: 200, bottom: 40 })
      stubRect(parent, { width: 200, height: 40, right: 200, bottom: 40 })
    })
    window.google = { accounts: { id: { initialize: vi.fn(), renderButton } } }

    const { default: GoogleSignInButton } = await import('./GoogleSignInButton')
    const { container } = render(<GoogleSignInButton onError={() => {}} />)

    const wrapper = container.querySelector('[data-testid="google-signin-wrapper"]') as HTMLElement
    stubRect(wrapper, { width: 320, height: 54, right: 320, bottom: 54 })

    await waitFor(() => {
      expect(renderButton).toHaveBeenCalledTimes(1)
    })

    // fitOverlay 는 wrapper 크기가 아직 0×0(jsdom 기본값)일 때 한 번 실행돼
    // 아무 것도 하지 않으므로, wrapper 크기를 스텁한 뒤 리사이즈 이벤트로
    // 다시 재계산시킨다 — 실제 화면에서도 동일한 경로(window resize →
    // renderGoogleButton → fitOverlay)로 재계산된다.
    window.dispatchEvent(new Event('resize'))

    await waitFor(() => {
      const target = container.querySelector(
        '[data-testid="google-signin-wrapper"] > div:last-child > div',
      ) as HTMLElement
      // 320/200 = 1.6, 54/40 = 1.35 — 폭·높이 각각 다른 비율로 늘어나
      // 우리 버튼 자리를 정확히 채운다.
      expect(target.style.transform).toBe('scale(1.6, 1.35)')
    })
  })
})
