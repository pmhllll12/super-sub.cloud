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
 * 것보다 없는 편이 낫다. (api-contract.md 2절)
 *
 * ⚠️ NEXT_PUBLIC_ 은 **빌드 시점에 번들에 구워진다.** Vercel 에 변수를
 * 추가하는 것만으로는 이미 배포된 빌드가 바뀌지 않는다 — 반드시 재배포까지
 * 해야 한다. (2026-08-28 에 이걸로 프로덕션에서 버튼이 아예 안 떴다.)
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
 * 그래서 계속 `google.accounts.id`(+ `renderButton`)를 쓴다.
 *
 * 🔴 **구글이 그린 버튼을 그대로 보여준다. 감싸거나 덮지 않는다.**
 *
 * 한때 "우리 PillButton 모양의 장식을 그리고 그 위에 구글 버튼을
 * `opacity: 0` 으로 겹쳐서, 겉모습은 우리 것 · 클릭은 구글 것"으로 만들었다.
 * **구글이 이걸 막는다.** 버튼이 실제로 눈에 보이지 않으면 클릭을 통째로
 * 무시한다 — 클릭재킹 방지 장치다(가시성·가림 감지). 콘솔에 에러 한 줄도
 * 남지 않고 그냥 아무 일도 안 일어나서 원인을 찾기가 아주 어렵다.
 *
 * 2026-08-28 에 배포본에서 실측으로 확인했다. 같은 좌표를 클릭했을 때
 * `opacity-0` 이면 무반응, 그 클래스 하나만 지우면 정상적으로 팝업이 뜬다.
 * 다른 조건(스케일·좌표·origin 등록·클라이언트 ID)은 전부 무죄였다.
 *
 * 그래서 지금은 반대로 간다 — 구글 버튼을 그대로 보이게 두고, **우리 쪽
 * 버튼 높이를 구글에 맞춘다**(`--ss-google-btn-h`, AuthShell 에서
 * `--ss-btn-h` 를 이 값으로 덮는다). 구글 버튼의 높이 44px 은 우리가 정할
 * 수 있는 값이 아니다.
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

  // 구글 버튼은 폭을 픽셀로만 받는다(% 불가). 카드 폭이 반응형(max-w-sm)이라
  // 실제 렌더된 폭을 재서 넘기고, 뷰포트가 바뀌면 다시 그린다.
  const renderGoogleButton = useCallback(() => {
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
  }, [text])

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

  useEffect(() => {
    function onResize() {
      renderGoogleButton()
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [renderGoogleButton])

  if (!CLIENT_ID) return null

  return (
    <>
      {/* 🔴 onLoad 가 아니라 onReady 다. onLoad 는 스크립트를 실제로 내려받는
          첫 번째 마운트에서만 온다 — next/script 의 loadScript 가 이미 실은
          스크립트(LoadCache)면 그대로 return 하기 때문이다. 로그아웃은
          router.refresh() 뿐이고 requireUser() 의 redirect('/login') 도
          클라이언트 사이드 이동이라 페이지가 새로 뜨지 않아서, onLoad 로는
          로그아웃하고 돌아온 로그인 화면에 버튼이 아예 안 그려졌다.
          onReady 는 첫 로드 때도, 그 뒤 재마운트마다도 온다(공식 문서가
          구글 지도 재초기화를 같은 이유로 이 방식으로 안내한다). */}
      <Script
        id="google-identity-services"
        src="https://accounts.google.com/gsi/client"
        strategy="afterInteractive"
        onReady={initialize}
      />
      {/* 스크립트가 붙기 전에도 자리를 잡아 둔다 — 버튼이 뒤늦게 나타나며
          아래 문구를 밀어내리지 않게 한다. */}
      <div
        ref={wrapperRef}
        data-testid="google-signin-wrapper"
        className="flex w-full justify-center"
        style={{ minHeight: 'var(--ss-google-btn-h)' }}
      >
        <div ref={googleContainerRef} />
      </div>
    </>
  )
}
