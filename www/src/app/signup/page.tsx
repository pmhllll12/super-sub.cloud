'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { apiErrorMessage, apiPost } from '@/lib/api/client'
import BrandMark from '@/components/ui/BrandMark'
import Field from '@/components/ui/Field'
import GlassPanel from '@/components/ui/GlassPanel'
import PillButton from '@/components/ui/PillButton'

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
    <main className="relative flex min-h-screen items-center justify-center px-6 py-16">
      {/* 사진을 화면 폭 전체로 늘리면(초광폭 데스크톱) 세로로 극단적으로 잘려 무엇을
          찍었는지 알아볼 수 없다. 원본에 가까운 폭의 판으로 가운데 제한하고 위쪽
          (얼굴·상반신 쪽)을 기준으로 앉힌다. */}
      <div
        aria-hidden="true"
        className="fixed inset-y-0 left-1/2 w-full max-w-2xl -translate-x-1/2 overflow-hidden bg-cover bg-top -z-10"
        style={{ backgroundImage: "url('/player_mono.jpg')" }}
      >
        <div className="absolute inset-0" style={{ background: 'var(--ss-scrim-strong)' }} />
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
          <p className="text-sm" style={{ color: MUTED }}>
            이미 계정이 있으신가요?{' '}
            <Link href="/login" style={{ color: 'var(--ss-accent)' }}>
              로그인
            </Link>
          </p>
        </div>
      </GlassPanel>
    </main>
  )
}
