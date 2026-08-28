'use client'

import Script from 'next/script'
import { useRouter } from 'next/navigation'
import { useCallback, useEffect, useRef } from 'react'
import { apiErrorMessage, apiPost } from '@/lib/api/client'

/**
 * 구글 클라이언트 ID 는 원래 공개되는 값이라 NEXT_PUBLIC_ 이 맞다 (백엔드
 * 주소·비밀에 대한 "NEXT_PUBLIC_ 금지" 규칙과는 다른 이야기).
 *
 * 값이 없으면 버튼을 아예 그리지 않는다 — 눌러도 안 되는 버튼을 보여주는
 * 것보다 없는 편이 낫다. (api-contract.md 2절 — 실제 클라이언트 ID는 아직
 * 이 저장소에 없다.)
 */
const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID

type GoogleCredentialResponse = { credential: string }

type RenderButtonOptions = {
  theme?: 'outline' | 'filled_blue' | 'filled_black'
  size?: 'large' | 'medium' | 'small'
  text?: 'signin_with' | 'signup_with' | 'continue_with' | 'signin'
  shape?: 'rectangular' | 'pill' | 'circle' | 'square'
  locale?: string
  width?: string
}

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string
            callback: (resp: GoogleCredentialResponse) => void
          }) => void
          renderButton: (parent: HTMLElement, options: RenderButtonOptions) => void
        }
      }
    }
  }
}

const MAX_BUTTON_WIDTH = 400

const LABEL: Record<'signin_with' | 'signup_with', string> = {
  signin_with: 'Google 계정으로 로그인',
  signup_with: 'Google 계정으로 가입',
}

/**
 * Google Identity Services 의 `renderButton`(팝업 방식)으로 id_token 을 받아
 * /api/auth/google 로 넘긴다. 응답 형태가 비밀번호 로그인과 같으므로 성공
 * 후 이동 경로도 같다(/home).
 *
 * One Tap(`prompt()`) 은 FedCM 의 통제를 받아 클릭에 반응하는 용도로
 * 부적합하다 — 한 번 닫으면 쿨다운이 걸리고 브라우저의 "타사 로그인"
 * 설정에 막히면 이유 없이 AbortError 로 중단된다. `google.accounts.oauth2`
 * 계열(implicit flow)은 대안이 되지 못한다 — 그쪽이 주는 건 access_token
 * 이고, 백엔드 계약이 필요로 하는 건 id_token 이다(api-contract.md).
 * 그래서 계속 `google.accounts.id`(+ `renderButton`)를 쓴다 — 이 경로만
 * FedCM 문제 없이, 그리고 access_token 이 아니라 id_token 을 돌려준다.
 *
 * 문제는 `renderButton` 이 버튼 마크업을 구글이 직접 그린다는 것 — 그래서
 * 완전한 커스텀 스타일(우리 PillButton 과 높이 54px·모서리 동일, 로고 없이
 * 글자만)이 불가능하다. 대신 "우리 버튼 위에 구글 버튼을 투명하게 겹치는"
 * 방식을 쓴다:
 *   1. 우리 PillButton 모양의 장식 요소를 그린다 (클릭/포커스 불가,
 *      aria-hidden — 스크린리더는 이 텍스트를 읽지 않는다).
 *   2. 구글이 그리는 실제 버튼을 `opacity: 0` 으로 그 위에 얹는다 — 클릭과
 *      키보드 포커스는 전부 이 요소가 받는다(구글이 준 접근성 라벨이
 *      그대로 스크린리더에 읽힌다).
 *   3. 구글 버튼의 자체 높이(large 여도 ~40px)가 --ss-btn-h(54px)보다
 *      낮아 그냥 겹치면 위아래 가장자리에 눌리지 않는 사각지대가 생긴다.
 *      그래서 겹친 뒤 실제 렌더된 크기를 재서 `transform: scale()` 로
 *      우리 버튼과 정확히 같은 크기로 늘린다 — CSS 트랜스폼은 히트
 *      테스트에도 적용되므로 늘어난 자리 전체가 그대로 클릭된다.
 */
export default function GoogleSignInButton({
  onError,
  text = 'signin_with',
}: {
  onError: (message: string) => void
  /** signin_with(…로 로그인) / signup_with(…로 가입) — 페이지 문맥에 맞게 지정 */
  text?: 'signin_with' | 'signup_with'
}) {
  const router = useRouter()
  const wrapperRef = useRef<HTMLDivElement>(null)
  const googleContainerRef = useRef<HTMLDivElement>(null)
  const initialized = useRef(false)

  async function handleCredential(idToken: string) {
    try {
      await apiPost('/api/auth/google', { id_token: idToken })
      router.push('/home')
      router.refresh()
    } catch (err) {
      // 503 GOOGLE_LOGIN_NOT_CONFIGURED 도 서버가 준 message 를 그대로 보여준다.
      onError(apiErrorMessage(err))
    }
  }

  // 구글이 그린 실제 버튼(googleContainerRef 의 유일한 자식)을 우리 버튼
  // 자리(wrapperRef)와 폭·높이 모두 정확히 겹치도록 늘린다. transform 은
  // 매번 초기화한 뒤 다시 재야 한다 — 이미 걸린 scale 값을 낀 채로 재면
  // (이미 늘어난 크기) / (원래 크기) 로 계산돼 계속 부풀어 오른다.
  const fitOverlay = useCallback(() => {
    const wrapper = wrapperRef.current
    const target = googleContainerRef.current
    if (!wrapper || !target || !target.firstElementChild) return
    target.style.transform = 'none'
    const wrapperRect = wrapper.getBoundingClientRect()
    const targetRect = target.getBoundingClientRect()
    if (!wrapperRect.width || !wrapperRect.height || !targetRect.width || !targetRect.height) return
    target.style.transformOrigin = 'top left'
    target.style.transform = `scale(${wrapperRect.width / targetRect.width}, ${wrapperRect.height / targetRect.height})`
  }, [])

  function renderGoogleButton() {
    if (!window.google || !wrapperRef.current || !googleContainerRef.current) return
    const measuredWidth = wrapperRef.current.offsetWidth
    const width = String(measuredWidth > 0 ? Math.min(measuredWidth, MAX_BUTTON_WIDTH) : MAX_BUTTON_WIDTH)
    // 재렌더(리사이즈) 때 이전 버튼이 남아있지 않도록 비우고 다시 그린다.
    googleContainerRef.current.innerHTML = ''
    window.google.accounts.id.renderButton(googleContainerRef.current, {
      theme: 'outline',
      shape: 'pill',
      size: 'large',
      text,
      locale: 'ko',
      width,
    })
    fitOverlay()
  }

  function initialize() {
    if (initialized.current || !window.google || !CLIENT_ID) return
    initialized.current = true
    window.google.accounts.id.initialize({
      client_id: CLIENT_ID,
      callback: (resp) => {
        void handleCredential(resp.credential)
      },
    })
    renderGoogleButton()
  }

  // 카드 폭은 반응형(max-w-sm)이라, 구글 버튼의 고정 픽셀 폭·그 위에 씌우는
  // 스케일도 뷰포트가 바뀔 때마다 다시 맞춰준다.
  useEffect(() => {
    function onResize() {
      renderGoogleButton()
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  if (!CLIENT_ID) return null

  return (
    <>
      <Script
        id="google-identity-services"
        src="https://accounts.google.com/gsi/client"
        strategy="afterInteractive"
        onLoad={initialize}
      />
      <div ref={wrapperRef} data-testid="google-signin-wrapper" className="relative w-full" style={{ height: 'var(--ss-btn-h)' }}>
        {/* 우리 PillButton 겉모습을 그대로 낸 장식 요소 — 실제 클릭/포커스는
            아래 겹쳐진 구글 버튼이 받으므로 스크린리더에는 감춘다. variant
            는 ghost 에 해당하는 값(투명 배경 + 옅은 테두리) — 민트색
            로그인 버튼(primary) 옆에서 "두 번째 선택지"로 읽히게 한다. */}
        <div
          aria-hidden="true"
          className="pointer-events-none inline-flex w-full items-center justify-center px-8 transition"
          style={{
            height: 'var(--ss-btn-h)',
            borderRadius: 'var(--ss-btn-r)',
            fontSize: 'var(--ss-btn-label)',
            background: 'transparent',
            color: 'var(--ss-fg)',
            border: '1px solid var(--ss-glass-border)',
          }}
        >
          {LABEL[text]}
        </div>
        {/* 구글이 그리는 실제 버튼 — id_token 을 받는 유일한 통로. 투명하게
            만들어 위 장식 버튼 자리 위에 정확히 겹친다(fitOverlay). */}
        <div className="absolute inset-0 overflow-hidden opacity-0" style={{ borderRadius: 'var(--ss-btn-r)' }}>
          <div ref={googleContainerRef} className="absolute top-0 left-0" />
        </div>
      </div>
    </>
  )
}
