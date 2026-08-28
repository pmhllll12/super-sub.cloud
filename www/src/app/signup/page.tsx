'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { apiErrorMessage, apiPost } from '@/lib/api/client'
import BrandMark from '@/components/ui/BrandMark'
import Field from '@/components/ui/Field'
import GlassPanel from '@/components/ui/GlassPanel'
import PillButton from '@/components/ui/PillButton'

export default function SignupPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [nickname, setNickname] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await apiPost('/api/auth/signup', { email, password, nickname })
      // 가입은 로그인이 아니다. 세션이 없으니 로그인 화면으로 보낸다.
      router.push('/login')
    } catch (err) {
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
          <h1 className="sr-only">회원가입</h1>
          <form onSubmit={onSubmit} className="flex w-full flex-col gap-4">
            <Field label="이메일" type="email" value={email} onChange={setEmail} required />
            <Field
              label="비밀번호"
              type="password"
              value={password}
              onChange={setPassword}
              required
              minLength={8}
              hint="8자 이상"
            />
            <Field
              label="닉네임"
              value={nickname}
              onChange={setNickname}
              required
              minLength={1}
              maxLength={20}
              hint="1~20자"
            />
            {error && (
              <p role="alert" className="text-sm" style={{ color: 'var(--ss-error)' }}>
                {error}
              </p>
            )}
            <PillButton type="submit" disabled={busy} className="mt-2 w-full">
              가입하기
            </PillButton>
          </form>
        </div>
      </GlassPanel>
    </main>
  )
}
