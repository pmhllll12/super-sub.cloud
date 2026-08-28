'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { apiErrorMessage, apiPatch } from '@/lib/api/client'

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
    <form onSubmit={onSubmit} className="flex flex-col gap-3">
      <label className="flex flex-col gap-1.5">
        <span className="text-sm text-neutral-500">닉네임</span>
        <input
          type="text"
          minLength={1}
          maxLength={20}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="rounded-lg border px-3 py-2"
        />
      </label>
      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}
      {saved && (
        <p role="status" className="text-sm text-green-600">
          저장했습니다.
        </p>
      )}
      <button
        type="submit"
        disabled={busy}
        className="self-start rounded-lg border px-4 py-2 disabled:opacity-50"
      >
        저장
      </button>
    </form>
  )
}
