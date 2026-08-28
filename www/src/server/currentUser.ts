import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import { BackendError, getBackend, type User } from '@/server/backend'
import { SESSION_COOKIE } from '@/server/session'

export async function requireUser(): Promise<User> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value
  if (!token) redirect('/login')

  try {
    return await getBackend().getMe(token)
  } catch (e) {
    // INVALID_TOKEN 이면 쿠키가 썩은 것이다. 로그인으로 보낸다.
    if (e instanceof BackendError && e.status === 401) redirect('/login')
    throw e
  }
}
