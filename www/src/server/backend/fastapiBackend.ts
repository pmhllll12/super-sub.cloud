import { callFastApi } from './fastapiCall'
import type { Backend } from './gateway'
import type {
  AdminUserDetail,
  AdminUserListResult,
  AuthToken,
  PlayerCard,
  PublicPlayerCard,
  SignupResult,
  User,
} from './types'

/**
 * 진짜 FastAPI를 부르는 게이트웨이 — `getBackend()`가 `USE_MOCK`이 아닐 때
 * 이걸 돌려준다(jin-10). `fastapi/docs/api-contract.md` 1~3-2절 그대로다.
 *
 * 라우트 핸들러는 이 파일의 존재를 모른다 — `getBackend()`가 `mockBackend`
 * 대신 이걸 돌려줄 뿐, 호출부(`www/src/app/api/**`)는 한 줄도 안 바뀐다.
 */
export const fastapiBackend: Backend = {
  signup({ email, password, nickname }) {
    return callFastApi<SignupResult>('/auth/signup', {
      method: 'POST',
      body: { email, password, nickname },
    })
  },

  login({ email, password }) {
    return callFastApi<AuthToken>('/auth/login', { method: 'POST', body: { email, password } })
  },

  loginWithGoogle({ id_token }) {
    return callFastApi<AuthToken>('/auth/google', { method: 'POST', body: { id_token } })
  },

  getMe(token) {
    return callFastApi<User>('/me', { method: 'GET', token })
  },

  updateMe(token, { nickname }) {
    return callFastApi<User>('/me', { method: 'PATCH', token, body: { nickname } })
  },

  getMyCard(token) {
    return callFastApi<PlayerCard>('/me/card', { method: 'GET', token })
  },

  getPublicCard(slug) {
    return callFastApi<PublicPlayerCard>(`/cards/${encodeURIComponent(slug)}`, { method: 'GET' })
  },

  listUsers(token, { q, page = 1, size = 20 }) {
    const params = new URLSearchParams({ page: String(page), size: String(size) })
    if (q) params.set('q', q)
    return callFastApi<AdminUserListResult>(`/admin/users?${params}`, { method: 'GET', token })
  },

  getUserDetail(token, userId) {
    return callFastApi<AdminUserDetail>(`/admin/users/${encodeURIComponent(userId)}`, {
      method: 'GET',
      token,
    })
  },

  async forceDeleteUser(token, userId) {
    await callFastApi<null>(`/admin/users/${encodeURIComponent(userId)}`, {
      method: 'DELETE',
      token,
    })
  },
}
