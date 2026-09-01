import Link from 'next/link'
import { cookies } from 'next/headers'
import { notFound, redirect } from 'next/navigation'
import { BackendError, getBackend } from '@/server/backend'
import { SESSION_COOKIE } from '@/server/session'
import GlassPanel from '@/components/ui/GlassPanel'
import ForceDeleteButton from './ForceDeleteButton'

const MUTED = 'color-mix(in srgb, var(--ss-fg) 60%, transparent)'

export default async function AdminUserDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const token = (await cookies()).get(SESSION_COOKIE)?.value
  if (!token) redirect('/login')
  const { id } = await params

  let user
  try {
    user = await getBackend().getUserDetail(token, id)
  } catch (e) {
    if (e instanceof BackendError && e.status === 401) redirect('/login')
    if (e instanceof BackendError && e.status === 403) redirect('/')
    if (e instanceof BackendError && e.status === 404) notFound()
    throw e
  }

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 px-6 py-12">
      <Link href="/admin/users" className="text-sm underline" style={{ color: MUTED }}>
        ← 회원 목록으로
      </Link>

      <GlassPanel className="flex flex-col gap-6 px-8 py-10">
        <header className="space-y-1">
          <h1 className="text-2xl font-bold">{user.nickname}</h1>
          <p className="text-sm" style={{ color: MUTED }}>
            {user.email}
          </p>
          <p className="text-xs" style={{ color: MUTED }}>
            가입일 {user.created_at.slice(0, 10)} · 선수 카드 {user.has_card ? '있음' : '없음'}
          </p>
        </header>

        <section className="flex flex-col gap-3">
          <h2 className="text-lg font-semibold">소속 이력</h2>
          {user.teams.length === 0 ? (
            <p className="text-sm" style={{ color: MUTED }}>
              소속된 적 없음
            </p>
          ) : (
            <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {user.teams.map((t) => (
                <li
                  key={`${t.team_id}-${t.joined_at}`}
                  className="rounded-2xl px-4 py-3"
                  style={{ border: '1px solid var(--ss-glass-border)' }}
                >
                  <p className="font-medium">
                    {t.name}
                    {t.left_at && <span style={{ color: MUTED }}> (탈퇴)</span>}
                  </p>
                  <p className="text-sm" style={{ color: MUTED }}>
                    {t.region} · {t.sport_code} · {t.role}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>

        <ForceDeleteButton userId={user.id} nickname={user.nickname} />
      </GlassPanel>
    </main>
  )
}
