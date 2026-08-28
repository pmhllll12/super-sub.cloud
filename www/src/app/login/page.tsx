'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { apiErrorMessage, apiPost } from '@/lib/api/client'
import Field from '@/components/ui/Field'
import PillButton from '@/components/ui/PillButton'
import GoogleSignInButton from '@/components/auth/GoogleSignInButton'
import AuthShell from '@/components/auth/AuthShell'

const FAINT = 'color-mix(in srgb, var(--ss-fg) 40%, transparent)'
const MUTED = 'color-mix(in srgb, var(--ss-fg) 60%, transparent)'

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
    <AuthShell
      formTitle="다시 만나서 반가워요"
      formDescription="이메일과 비밀번호를 입력해 로그인하세요."
      footer={
        <>
          <p className="max-w-sm text-xs" style={{ color: FAINT }}>
            계속 진행하면 이용약관과 개인정보처리방침에 동의하는 것으로 간주됩니다.
          </p>
          <p className="text-sm" style={{ color: MUTED }}>
            계정이 없으신가요?{' '}
            <Link href="/signup" style={{ color: 'var(--ss-accent)' }}>
              회원가입
            </Link>
          </p>
        </>
      }
    >
      <form onSubmit={onSubmit} className="flex w-full flex-col gap-4">
        <Field label="이메일" type="email" value={email} onChange={setEmail} required />
        <Field
          label="비밀번호"
          type="password"
          value={password}
          onChange={setPassword}
          required
          minLength={8}
          revealable
        />
        {error && (
          <p role="alert" className="text-sm" style={{ color: 'var(--ss-error)' }}>
            {error}
          </p>
        )}
        <PillButton type="submit" disabled={busy} className="mt-2 w-full">
          로그인
        </PillButton>
        <GoogleSignInButton onError={setError} />
      </form>
    </AuthShell>
  )
}
