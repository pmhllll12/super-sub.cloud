'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { apiDelete, apiErrorMessage } from '@/lib/api/client'
import PillButton from '@/components/ui/PillButton'

export default function ForceDeleteButton({
  userId,
  nickname,
}: {
  userId: string
  nickname: string
}) {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onClick() {
    // 되돌릴 수 없는 동작이라(계정과 파생 데이터가 함께 지워진다) 확인을 한 번 더 받는다.
    if (!window.confirm(`${nickname} 님을 강제 탈퇴시킬까요? 되돌릴 수 없습니다.`)) return
    setError(null)
    setBusy(true)
    try {
      await apiDelete(`/api/admin/users/${userId}`)
      router.push('/admin/users')
      router.refresh()
    } catch (err) {
      setError(apiErrorMessage(err))
      setBusy(false)
    }
  }

  return (
    <div
      className="flex flex-col items-start gap-2 pt-6"
      style={{ borderTop: '1px solid var(--ss-glass-border)' }}
    >
      {error && (
        <p role="alert" className="text-sm" style={{ color: 'var(--ss-error)' }}>
          {error}
        </p>
      )}
      <PillButton variant="ghost" onClick={onClick} disabled={busy}>
        강제 탈퇴
      </PillButton>
    </div>
  )
}
