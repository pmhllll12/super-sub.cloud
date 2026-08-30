import Link from 'next/link'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import PlayerCardView from '@/components/PlayerCardView'
import GlassPanel from '@/components/ui/GlassPanel'
import { BackendError, getBackend, type PlayerCard, type User } from '@/server/backend'
import { requireUser } from '@/server/currentUser'
import { SESSION_COOKIE } from '@/server/session'
import NicknameForm from './NicknameForm'

const MUTED = 'color-mix(in srgb, var(--ss-fg) 60%, transparent)'

/**
 * 마크업만 따로 뺀 것 — `MePage` 가 서버 컴포넌트로 쿠키 · 백엔드를 부르게
 * 되면서 테스트가 이 함수를 직접 렌더한다(`HomeBody` 와 같은 이유 · 같은 방식).
 *
 * 선수 카드가 여기 같이 있다. 예전에는 `/me/card` 라는 별도 화면이었는데
 * 홈 목적지를 6개로 정리하면서 '내 선수 카드'를 '내 프로필'에 합쳤다 —
 * 프로필과 카드는 결국 같은 사람에 대한 한 화면이라 나눌 이유가 약했다.
 * `/me/card` 는 그 자리로 보내는 스텁으로 남겨 뒀다(옛 링크 호환).
 */
export function MeBody({ user, card }: { user: User; card: PlayerCard | null }) {
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

      {/* 선수 카드 — 프로필 · 소속 팀 아래 한 폭으로. PlayerCardView 가 스스로
          max-w-md 로 가운데를 잡으므로 여기서 폭을 다시 정하지 않는다. */}
      <section className="flex flex-col items-center gap-4">
        {card ? (
          <>
            <PlayerCardView card={card} />
            <p className="text-sm" style={{ color: MUTED }}>
              공유 링크:{' '}
              <Link
                href={`/c/${card.public_slug}`}
                className="underline"
                style={{ color: 'var(--ss-accent)' }}
              >
                /c/{card.public_slug}
              </Link>
            </p>
          </>
        ) : (
          <GlassPanel className="w-full max-w-md px-8 py-10 text-center">
            <h2 className="text-xl font-semibold">아직 선수 카드가 없습니다</h2>
            <p className="mt-2 text-sm" style={{ color: MUTED }}>
              경기 영상이 분석되면 카드가 만들어집니다.
            </p>
          </GlassPanel>
        )}
      </section>
    </main>
  )
}

export default async function MePage() {
  const user = await requireUser()

  // 카드가 아직 없는 것은 정상이다 — CARD_NOT_FOUND 는 화면 안에서
  // "아직 없습니다"로 안내한다. 401 은 requireUser() 가 이미 걸러 냈지만
  // 그 사이 토큰이 죽을 수도 있어 여기서도 로그인으로 보낸다.
  const token = (await cookies()).get(SESSION_COOKIE)?.value
  let card: PlayerCard | null = null
  if (token) {
    try {
      card = await getBackend().getMyCard(token)
    } catch (e) {
      if (e instanceof BackendError && e.status === 401) redirect('/login')
      if (!(e instanceof BackendError && e.code === 'CARD_NOT_FOUND')) throw e
    }
  }

  return <MeBody user={user} card={card} />
}
