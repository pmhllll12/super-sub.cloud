'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { apiErrorMessage, apiPost } from '@/lib/api/client'
import { useRateLimitLock } from '@/lib/api/rateLimit'
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
  /* 🔴 **429 뒤에는 다시 안 보낸다**(계약 1번). 기다릴 시간은 서버가 준
     `Retry-After` 다 — 자체 타이머를 두지 않는다. */
  const limit = useRateLimitLock()

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    // 잠긴 동안 눌러도 나가지 않는다 — 단추를 막아 두지만 Enter 로도 들어온다.
    if (limit.locked) return
    setError(null)
    setBusy(true)
    try {
      await apiPost('/api/auth/login', { email, password })
      router.push('/home')
      router.refresh()
    } catch (err) {
      // 429 는 잠금이 제 문구(남은 초)를 내므로 에러 줄을 겹쳐 쓰지 않는다.
      if (!limit.lockFrom(err)) setError(apiErrorMessage(err))
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
        {(error || limit.note) && (
          <p role="alert" className="text-sm" style={{ color: 'var(--ss-error)' }}>
            {limit.note ?? error}
          </p>
        )}
        <PillButton type="submit" disabled={busy || limit.locked} className="mt-2 w-full">
          로그인
        </PillButton>
        {/* 🔴 구글 버튼은 **감추거나 덮지 않는다**(§6 — 가리면 구글이 클릭을
            통째로 무시한다). 잠금은 버튼이 아니라 **보내는 쪽**에서 건다. */}
        <GoogleSignInButton onError={setError} limit={limit} />
      </form>
    </AuthShell>
  )
}
