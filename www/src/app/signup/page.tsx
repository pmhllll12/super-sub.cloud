'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { apiErrorMessage, apiPost } from '@/lib/api/client'
import BrandMark from '@/components/ui/BrandMark'
import Field from '@/components/ui/Field'
import PillButton from '@/components/ui/PillButton'
import GoogleSignInButton from '@/components/auth/GoogleSignInButton'

const MUTED = 'color-mix(in srgb, var(--ss-fg) 60%, transparent)'
const FAINT = 'color-mix(in srgb, var(--ss-fg) 40%, transparent)'

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
    <main className="grid min-h-screen w-full grid-cols-1 lg:grid-cols-2">
      <div className="flex flex-col justify-center gap-8 px-6 py-16 sm:px-12 lg:px-16 xl:px-24">
        <BrandMark size={40} />
        <h1
          className="max-w-md text-3xl leading-tight font-semibold sm:text-4xl"
          style={{ wordBreak: 'keep-all' }}
        >
          안개 속에서도, 실력은 숨지 않습니다.
        </h1>
        <form onSubmit={onSubmit} className="flex w-full max-w-sm flex-col gap-4">
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
          <GoogleSignInButton onError={setError} />
        </form>
        <p className="max-w-sm text-xs" style={{ color: FAINT }}>
          계속 진행하면 이용약관과 개인정보처리방침에 동의하는 것으로 간주됩니다.
        </p>
        <p className="text-sm" style={{ color: MUTED }}>
          이미 계정이 있으신가요?{' '}
          <Link href="/login" style={{ color: 'var(--ss-accent)' }}>
            로그인
          </Link>
        </p>
      </div>

      {/* 아치 모양 사진 판 — 위 두 모서리만 --ss-radius-arch 로 크게 둥글린다.
          사진은 자르지 않는다(contain). 판은 화면 높이에 딱 맞춘다 —
          min-h-screen 이면 위 여백만큼 길어져 아래가 잘린다.
          좁은 화면에서는 아예 숨겨(폼이 밀려나지 않도록) lg 이상에서만 보인다. */}
      <div className="relative hidden overflow-hidden lg:flex lg:h-screen lg:items-stretch lg:pt-10 lg:pl-8">
        <div
          aria-hidden="true"
          className="w-full bg-contain bg-center bg-no-repeat"
          style={{
            backgroundImage: "url('/login_figure.jpg')",
            borderRadius: 'var(--ss-radius-arch) var(--ss-radius-arch) 0 0',
          }}
        />
      </div>
    </main>
  )
}
