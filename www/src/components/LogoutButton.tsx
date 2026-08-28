'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { apiErrorMessage, apiPost } from '@/lib/api/client'
import PillButton from '@/components/ui/PillButton'

/**
 * 홈 인사말 자리, 닉네임 옆에 놓는 로그아웃. 자주 누르는 동작이 아니니
 * 로그인 버튼만큼 눈에 띌 필요는 없다 — `ghost` 로 낮춘다.
 *
 * `/api/auth/logout` 은 세션 쿠키를 지우기만 하고 어디로도 보내지 않는다.
 * `/` 가 이미 홈이라 이동할 필요가 없다 — `router.refresh()` 로 서버
 * 컴포넌트(`Home`)를 다시 그리게 해서 "로그인 함" 모습이 그 자리에서
 * "로그인 안 함"(로그인 · 회원가입 버튼) 모습으로 바뀌게 한다.
 */
export default function LogoutButton() {
  const router = useRouter()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onClick() {
    setError(null)
    setBusy(true)
    try {
      await apiPost('/api/auth/logout', {})
      router.refresh()
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col items-center gap-1">
      <PillButton variant="ghost" onClick={onClick} disabled={busy}>
        로그아웃
      </PillButton>
      {error && (
        <p role="alert" className="text-xs" style={{ color: 'var(--ss-error)' }}>
          {error}
        </p>
      )}
    </div>
  )
}
