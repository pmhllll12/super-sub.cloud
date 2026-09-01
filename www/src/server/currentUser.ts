import { cache } from 'react'
import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import { BackendError, getBackend, type PlayerCard, type User } from '@/server/backend'
import { SESSION_COOKIE } from '@/server/session'

/**
 * 🔴 `cache()` 로 감싼다 — 같은 요청 안에서 몇 번을 불러도 백엔드에는 한 번만
 * 간다. 헤더(레이아웃)와 페이지가 **둘 다** 로그인을 확인하는데, 감싸지 않으면
 * 화면 한 장에 `GET /me` 가 두 번 나간다.
 */
export const requireUser = cache(async (): Promise<User> => {
  const token = (await cookies()).get(SESSION_COOKIE)?.value
  if (!token) redirect('/login')

  try {
    return await getBackend().getMe(token)
  } catch (e) {
    // INVALID_TOKEN 이면 쿠키가 썩은 것이다. 로그인으로 보낸다.
    if (e instanceof BackendError && e.status === 401) redirect('/login')
    throw e
  }
})

/**
 * 내 선수 카드. **없는 것이 정상**이라 404 는 null 로 삼킨다 — 카드가 아직
 * 없는 사람에게 화면이 깨지면 안 된다.
 *
 * 헤더의 프로필 자리와 홈의 스쿼드 판이 같은 카드를 쓴다. `cache()` 가 그
 * 둘을 한 번의 호출로 묶는다.
 */
export const getMyCardOrNull = cache(async (): Promise<PlayerCard | null> => {
  const token = (await cookies()).get(SESSION_COOKIE)?.value
  if (!token) return null

  try {
    return await getBackend().getMyCard(token)
  } catch (e) {
    if (e instanceof BackendError && e.status === 401) redirect('/login')
    if (e instanceof BackendError && e.code === 'CARD_NOT_FOUND') return null
    throw e
  }
})
