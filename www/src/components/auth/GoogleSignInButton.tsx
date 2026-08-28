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
        className="w-full"
      >
        Google로 계속하기
      </PillButton>
    </>
  )
}
