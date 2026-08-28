'use client'

import Script from 'next/script'
import { useRouter } from 'next/navigation'
import { useRef, useState } from 'react'
import { apiErrorMessage, apiPost } from '@/lib/api/client'
import PillButton from '@/components/ui/PillButton'

/**
 * 구글 클라이언트 ID 는 원래 공개되는 값이라 NEXT_PUBLIC_ 이 맞다 (백엔드
 * 주소·비밀에 대한 "NEXT_PUBLIC_ 금지" 규칙과는 다른 이야기).
 *
 * 값이 없으면 버튼을 아예 그리지 않는다 — 눌러도 안 되는 버튼을 보여주는
 * 것보다 없는 편이 낫다. (api-contract.md 2절 — 실제 클라이언트 ID는 아직
 * 이 저장소에 없다.)
 */
const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID

/**
 * 공식 구글 "G" 마크(4색). 외부 이미지 대신 인라인 SVG 로 넣는다 — 요청이
 * 늘지 않고, 로드 실패로 빈칸이 될 일도 없다. 브랜드 가이드가 정한 4색
 * 조합이라 색을 바꾸거나 단색화하지 않는다. 장식이므로 버튼의 접근 가능한
 * 이름(텍스트)에 안 섞이도록 aria-hidden.
 */
function GoogleGlyph() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true" className="shrink-0">
      <path
        fill="#4285F4"
        d="M17.64 9.2045c0-.6381-.0573-1.2518-.1636-1.8409H9v3.4814h4.8436c-.2086 1.125-.8427 2.0782-1.7959 2.7164v2.2581h2.9087c1.7018-1.5668 2.6836-3.874 2.6836-6.615z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.4673-.8059 5.9564-2.1805l-2.9087-2.2581c-.8059.54-1.8368.8591-3.0477.8591-2.3436 0-4.3282-1.5831-5.036-3.7104H.9573v2.3318C2.4382 15.9832 5.4818 18 9 18z"
      />
      <path
        fill="#FBBC05"
        d="M3.964 10.71c-.18-.54-.2822-1.1168-.2822-1.71s.1023-1.17.2823-1.71V4.9582H.9573C.3477 6.1732 0 7.5477 0 9s.3477 2.8268.9573 4.0418L3.964 10.71z"
      />
      <path
        fill="#EA4335"
        d="M9 3.5795c1.3214 0 2.5077.4541 3.4405 1.346l2.5813-2.5813C13.4632.8918 11.4259 0 9 0 5.4818 0 2.4382 2.0168.9573 4.9582L3.964 7.29C4.6718 5.1627 6.6564 3.5795 9 3.5795z"
      />
    </svg>
  )
}

type GoogleCredentialResponse = { credential: string }

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string
            callback: (resp: GoogleCredentialResponse) => void
          }) => void
          prompt: () => void
        }
      }
    }
  }
}

/**
 * Google Identity Services 로 id_token 을 받아 /api/auth/google 로 넘긴다.
 * 응답 형태가 비밀번호 로그인과 같으므로 성공 후 이동 경로도 같다(/home).
 */
export default function GoogleSignInButton({
  onError,
}: {
  onError: (message: string) => void
}) {
  const router = useRouter()
  const [ready, setReady] = useState(false)
  const [busy, setBusy] = useState(false)
  const initialized = useRef(false)

  if (!CLIENT_ID) return null

  function initialize() {
    if (initialized.current || !window.google) return
    initialized.current = true
    window.google.accounts.id.initialize({
      client_id: CLIENT_ID as string,
      callback: (resp) => {
        void handleCredential(resp.credential)
      },
    })
    setReady(true)
  }

  async function handleCredential(idToken: string) {
    setBusy(true)
    try {
      await apiPost('/api/auth/google', { id_token: idToken })
      router.push('/home')
      router.refresh()
    } catch (err) {
      // 503 GOOGLE_LOGIN_NOT_CONFIGURED 도 서버가 준 message 를 그대로 보여준다.
      onError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  function onClick() {
    window.google?.accounts.id.prompt()
  }

  return (
    <>
      <Script
        id="google-identity-services"
        src="https://accounts.google.com/gsi/client"
        strategy="afterInteractive"
        onLoad={initialize}
      />
      <PillButton
        type="button"
        variant="ghost"
        disabled={!ready || busy}
        onClick={onClick}
        className="w-full gap-2"
      >
        <GoogleGlyph />
        Google로 계속하기
      </PillButton>
    </>
  )
}
