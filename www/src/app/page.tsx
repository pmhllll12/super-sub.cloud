import Link from 'next/link'

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center gap-8 px-6">
      <div className="space-y-4">
        <h1 className="text-5xl font-bold tracking-tight">Super-Sub</h1>
        <p className="text-lg text-neutral-500">
          생활체육 경기 영상을 분석해 용병을 찾고, 실력을 검증합니다.
        </p>
      </div>
      <div className="flex gap-3">
        <Link
          href="/login"
          className="rounded-lg bg-neutral-900 px-5 py-2.5 text-white dark:bg-white dark:text-neutral-900"
        >
          로그인
        </Link>
        <Link href="/signup" className="rounded-lg border px-5 py-2.5">
          회원가입
        </Link>
      </div>
    </main>
  )
}
