import Link from 'next/link'
import { requireUser } from '@/server/currentUser'
import NicknameForm from './NicknameForm'

export default async function MePage() {
  const user = await requireUser()

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-10 px-6 py-16">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold">{user.nickname}</h1>
        <p className="text-sm text-neutral-500">{user.email}</p>
      </header>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">프로필</h2>
        <NicknameForm nickname={user.nickname} />
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">소속 팀</h2>
        {user.teams.length === 0 ? (
          <p className="text-sm text-neutral-500">아직 소속된 팀이 없습니다.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {user.teams.map((t) => (
              <li key={t.team_id} className="rounded-lg border px-4 py-3">
                <p className="font-medium">{t.name}</p>
                <p className="text-sm text-neutral-500">
                  {t.region} · {t.sport_code}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <Link href="/me/card" className="text-sm underline">
        내 선수 카드 보기 →
      </Link>
    </main>
  )
}
