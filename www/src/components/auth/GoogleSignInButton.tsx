'use client'

import Script from 'next/script'
import { useRouter } from 'next/navigation'
import { useEffect, useRef } from 'react'
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

/**
 * Google Identity Services 의 `renderButton`(팝업 방식)으로 id_token 을 받아
 * /api/auth/google 로 넘긴다. 응답 형태가 비밀번호 로그인과 같으므로 성공
 * 후 이동 경로도 같다(/home).
 *
 * One Tap(`prompt()`) 은 FedCM 의 통제를 받아 클릭에 반응하는 용도로
 * 부적합하다 — 한 번 닫으면 쿨다운이 걸리고 브라우저의 "타사 로그인"
 * 설정에 막히면 이유 없이 AbortError 로 중단된다. `renderButton` 은 구글이
 * 그리는 버튼을 클릭하면 팝업 창이 뜨는 방식이라 이 문제가 없다.
 *
 * 구글이 버튼 마크업을 직접 그리므로 완전한 커스텀 스타일은 불가능하다.
 * 대신 우리 카드가 검정 배경(`--ss-bg`)이라 `filled_black` 테마가 잘
 * 어울려 이 옵션을 그대로 쓴다(구글 브랜드 마크/문구는 임의 변경 금지).
 */
export default function GoogleSignInButton({
  onError,
}: {
  onError: (message: string) => void
}) {
  const router = useRouter()
  const containerRef = useRef<HTMLDivElement>(null)
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

  function renderGoogleButton() {
    if (!window.google || !containerRef.current) return
    const measuredWidth = containerRef.current.offsetWidth
    const width = String(measuredWidth > 0 ? Math.min(measuredWidth, MAX_BUTTON_WIDTH) : MAX_BUTTON_WIDTH)
    window.google.accounts.id.renderButton(containerRef.current, {
      theme: 'filled_black',
      shape: 'pill',
      size: 'large',
      text: 'continue_with',
      locale: 'ko',
      width,
    })
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

  // 카드 폭은 반응형(max-w-sm)이라, 구글 버튼의 고정 픽셀 폭도 뷰포트가
  // 바뀔 때마다 다시 맞춰준다.
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
      <div ref={containerRef} className="flex w-full justify-center" />
    </>
  )
}
