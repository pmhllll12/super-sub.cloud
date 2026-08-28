'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'
import { apiErrorMessage, apiPost } from '@/lib/api/client'

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
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-6 px-6">
      <h1 className="text-2xl font-bold">회원가입</h1>
      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-1.5">
          <span className="text-sm text-neutral-500">이메일</span>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded-lg border px-3 py-2"
          />
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-sm text-neutral-500">비밀번호</span>
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded-lg border px-3 py-2"
          />
          <span className="text-xs text-neutral-400">8자 이상</span>
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-sm text-neutral-500">닉네임</span>
          <input
            type="text"
            required
            minLength={1}
            maxLength={20}
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            className="rounded-lg border px-3 py-2"
          />
          <span className="text-xs text-neutral-400">1~20자</span>
        </label>
        {error && (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={busy}
          className="rounded-lg bg-neutral-900 px-4 py-2.5 text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
        >
          가입하기
        </button>
      </form>
    </main>
  )
}
