'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { apiErrorMessage, apiPatch } from '@/lib/api/client'
import Field from '@/components/ui/Field'
import PillButton from '@/components/ui/PillButton'

export default function NicknameForm({ nickname }: { nickname: string }) {
  const router = useRouter()
  const [value, setValue] = useState(nickname)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSaved(false)
    setBusy(true)
    try {
      await apiPatch('/api/me', { nickname: value })
      setSaved(true)
      router.refresh()
    } catch (err) {
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-4">
      <Field label="닉네임" value={value} onChange={setValue} minLength={1} maxLength={20} />
      {error && (
        <p role="alert" className="text-sm" style={{ color: 'var(--ss-error)' }}>
          {error}
        </p>
      )}
      {saved && (
        <p role="status" className="text-sm" style={{ color: 'var(--ss-accent)' }}>
          저장했습니다.
        </p>
      )}
      <PillButton type="submit" disabled={busy} className="self-start">
        저장
      </PillButton>
    </form>
  )
}
