'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { apiErrorMessage, apiPost } from '@/lib/api/client'
import BrandMark from '@/components/ui/BrandMark'
import Field from '@/components/ui/Field'
import GlassPanel from '@/components/ui/GlassPanel'
import PillButton from '@/components/ui/PillButton'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await apiPost('/api/auth/login', { email, password })
      router.push('/home')
      router.refresh()
    } catch (err) {
      // message 가 아니라 code 로 분기해야 할 곳이 생기면 여기서 나눈다.
      setError(apiErrorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center px-6 py-16">
      <div
        aria-hidden="true"
        className="fixed inset-0 -z-10 bg-cover bg-center"
        style={{ backgroundImage: "url('/player_mono.jpg')" }}
      >
        <div className="absolute inset-0" style={{ background: 'var(--ss-scrim)' }} />
      </div>

      <GlassPanel className="w-full max-w-[420px] px-8 py-10">
        <div className="flex flex-col items-center gap-8">
          <BrandMark size={40} />
          <h1 className="sr-only">로그인</h1>
          <form onSubmit={onSubmit} className="flex w-full flex-col gap-4">
            <Field label="이메일" type="email" value={email} onChange={setEmail} required />
            <Field
              label="비밀번호"
              type="password"
              value={password}
              onChange={setPassword}
              required
              minLength={8}
            />
            {error && (
              <p role="alert" className="text-sm" style={{ color: 'var(--ss-error)' }}>
                {error}
              </p>
            )}
            <PillButton type="submit" disabled={busy} className="mt-2 w-full">
              로그인
            </PillButton>
          </form>
        </div>
      </GlassPanel>
    </main>
  )
}
