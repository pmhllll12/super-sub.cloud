import { callFastApi } from './fastapiCall'
import type { Backend } from './gateway'
import type {
  MatchSearch,
  AdminUserDetail,
  AdminUserListResult,
  AuthToken,
  FeaturedVideo,
  Match,
  MercenaryCandidate,
  MyVideo,
  Position,
  VideoReport,
  PublicVideo,
  Squad,
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

  async changePassword(token, body) {
    await callFastApi<null>('/me/password', { method: 'PATCH', token, body })
  },

  async deleteMe(token, { password }) {
    await callFastApi<null>('/me', {
      method: 'DELETE',
      token,
      // 🔴 비밀번호가 없는 계정(구글 전용)은 **본문 없이** 부른다 —
      // 요구하면 그 사람은 탈퇴할 방법이 사라진다(계약 2장).
      body: password ? { password } : undefined,
    })
  },

  getMyCard(token) {
    return callFastApi<PlayerCard>('/me/card', { method: 'GET', token })
  },

  createMyCard(token) {
    return callFastApi<PlayerCard>('/me/card', { method: 'POST', token })
  },

  getPublicCard(slug) {
    return callFastApi<PublicPlayerCard>(`/cards/${encodeURIComponent(slug)}`, { method: 'GET' })
  },

  listMyVideos(token) {
    return callFastApi<MyVideo[]>('/videos', { method: 'GET', token })
  },

  getPlaybackUrl(token, videoId) {
    return callFastApi<{ url: string; expires_in: number }>(
      `/videos/${encodeURIComponent(videoId)}/playback-url`,
      { method: 'GET', token },
    )
  },

  async deleteMyVideo(token, videoId) {
    // 저장소에서 영상과 리포트를 함께 거두는 것은 **서버 몫**이다 — 화면은
    // 무엇이 어디 있는지 모른다(저장 키도 리포트 자리도 서버가 안다).
    await callFastApi<null>(`/videos/${encodeURIComponent(videoId)}`, {
      method: 'DELETE',
      token,
    })
  },

  getVideoReport(token, videoId) {
    return callFastApi<VideoReport>(`/videos/${encodeURIComponent(videoId)}/report`, {
      method: 'GET',
      token,
    })
  },

  updateVideo(token, videoId, input) {
    return callFastApi<MyVideo>(`/videos/${encodeURIComponent(videoId)}`, {
      method: 'PATCH',
      token,
      body: input,
    })
  },

  listPublicVideos(token) {
    return callFastApi<PublicVideo[]>('/videos/public', { method: 'GET', token })
  },

  getFeaturedVideo(token, cardSlug) {
    return callFastApi<FeaturedVideo>(
      `/cards/${encodeURIComponent(cardSlug)}/featured-video`,
      { method: 'GET', token },
    )
  },

  listPositions(token, params) {
    // 🔴 `searchMatches` 와 같은 이유로 **빈 값을 실어 보내지 않는다** —
    // `sport_code=` 는 "전체"가 아니라 없는 종목이라 422 로 튕긴다.
    const qs = params?.sport_code
      ? `?${new URLSearchParams({ sport_code: params.sport_code })}`
      : ''
    return callFastApi<Position[]>(`/positions${qs}`, { method: 'GET', token })
  },

  searchMatches(token, params) {
    const q = new URLSearchParams()
    // 🔴 빈 값을 실어 보내지 않는다 — `sport_code=` 는 "전체"가 아니라
    // 없는 종목이라 422 로 튕긴다.
    for (const [k, v] of Object.entries(params ?? {})) {
      if (v !== undefined && v !== null && v !== '') q.set(k, String(v))
    }
    const qs = q.toString()
    return callFastApi<MatchSearch>(`/matches${qs ? `?${qs}` : ''}`, { method: 'GET', token })
  },

  listTeamMatches(token, teamId) {
    return callFastApi<Match[]>(`/teams/${encodeURIComponent(teamId)}/matches`, {
      method: 'GET',
      token,
    })
  },

  createTeamMatch(token, teamId, input) {
    return callFastApi<Match>(`/teams/${encodeURIComponent(teamId)}/matches`, {
      method: 'POST',
      token,
      body: input,
    })
  },

  searchMercenaryCandidates(token, input) {
    return callFastApi<MercenaryCandidate[]>('/matching/search-candidates', {
      method: 'POST',
      token,
      body: input,
    })
  },

  getSquad(token, teamId) {
    return callFastApi<Squad>(`/teams/${encodeURIComponent(teamId)}/squad`, {
      method: 'GET',
      token,
    })
  },

  createSquad(token, teamId) {
    return callFastApi<Squad>(`/teams/${encodeURIComponent(teamId)}/squad`, {
      method: 'POST',
      token,
    })
  },

  addSquadMember(token, teamId, body) {
    return callFastApi<Squad>(`/teams/${encodeURIComponent(teamId)}/squad/members`, {
      method: 'POST',
      token,
      body,
    })
  },

  removeSquadMember(token, teamId, memberId) {
    return callFastApi<Squad>(
      `/teams/${encodeURIComponent(teamId)}/squad/members/${encodeURIComponent(memberId)}`,
      { method: 'DELETE', token },
    )
  },

  setSquadFormation(token, teamId, formation) {
    return callFastApi<Squad>(`/teams/${encodeURIComponent(teamId)}/squad`, {
      method: 'PATCH',
      token,
      body: { formation },
    })
  },

  updateSquadMember(token, teamId, memberId, body) {
    return callFastApi<Squad>(
      `/teams/${encodeURIComponent(teamId)}/squad/members/${encodeURIComponent(memberId)}`,
      { method: 'PATCH', token, body },
    )
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
