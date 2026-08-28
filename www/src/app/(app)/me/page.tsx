import Link from 'next/link'
import { requireUser } from '@/server/currentUser'
import GlassPanel from '@/components/ui/GlassPanel'
import NicknameForm from './NicknameForm'

const MUTED = 'color-mix(in srgb, var(--ss-fg) 60%, transparent)'

export default async function MePage() {
  const user = await requireUser()

  return (
    <main className="mx-auto flex max-w-4xl flex-col gap-6 py-12">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[380px_1fr]">
        <GlassPanel className="flex flex-col gap-6 px-8 py-10">
          <header className="space-y-1">
            <h1 className="text-2xl font-bold">{user.nickname}</h1>
            <p className="text-sm" style={{ color: MUTED }}>
              {user.email}
            </p>
          </header>

          <NicknameForm nickname={user.nickname} />

          <Link
            href="/me/card"
            className="text-sm underline"
            style={{ color: 'var(--ss-accent)' }}
          >
            내 선수 카드 보기 →
          </Link>
        </GlassPanel>

        <GlassPanel className="flex flex-col gap-4 px-8 py-10">
          <h2 className="text-lg font-semibold">소속 팀</h2>
          {user.teams.length === 0 ? (
            <p className="text-sm" style={{ color: MUTED }}>
              아직 소속된 팀이 없습니다.
            </p>
          ) : (
            <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {user.teams.map((t) => (
                <li
                  key={t.team_id}
                  className="rounded-2xl px-4 py-3"
                  style={{ border: '1px solid var(--ss-glass-border)' }}
                >
                  <p className="font-medium">{t.name}</p>
                  <p className="text-sm" style={{ color: MUTED }}>
                    {t.region} · {t.sport_code}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </GlassPanel>
      </div>
    </main>
  )
}
