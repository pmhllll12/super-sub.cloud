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
    <AuthShell
      formTitle="계정을 만들어요"
      formDescription="이메일과 비밀번호로 몇 초 만에 가입하세요."
      footer={
        <>
          <p className="max-w-sm text-xs" style={{ color: FAINT }}>
            계속 진행하면 이용약관과 개인정보처리방침에 동의하는 것으로 간주됩니다.
          </p>
          <p className="text-sm" style={{ color: MUTED }}>
            이미 계정이 있으신가요?{' '}
            <Link href="/login" style={{ color: 'var(--ss-accent)' }}>
              로그인
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
          hint="8자 이상"
          revealable
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
        <GoogleSignInButton onError={setError} />
      </form>
    </AuthShell>
  )
}
