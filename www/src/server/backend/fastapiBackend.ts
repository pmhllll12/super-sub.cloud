import { callFastApi } from './fastapiCall'
import type { Backend } from './gateway'
import type {
  MatchSearch,
  AdminUserDetail,
  AdminUserListResult,
  AdminVideoListResult,
  AppNotification,
  AuthToken,
  Contact,
  ContactRequest,
  UserSearchResult,
  TeamDetail,
  CardGrade,
  SquadCandidate,
  TeamMatchRequest,
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
  TeamInvitation,
  ReceivedInvitation,
  Region,
  TeamMatchPreference,
  MemberMatchPreference,
  MatchCandidate,
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

  updateMe(token, input) {
    // 🔴 **준 칸만 싣는다.** `undefined` 를 그대로 보내면 JSON 에서 사라지긴
    //    하지만, 명시적으로 골라 담아야 "안 보낸 것은 안 바뀐다"가 코드에서도
    //    읽힌다(계약이 그렇게 정했다).
    const body: Record<string, unknown> = {}
    if (input.nickname !== undefined) body.nickname = input.nickname
    if (input.is_nickname_searchable !== undefined) {
      body.is_nickname_searchable = input.is_nickname_searchable
    }
    return callFastApi<User>('/me', { method: 'PATCH', token, body })
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

  updateMyCard(token, input) {
    return callFastApi<PlayerCard>('/me/card', { method: 'PATCH', token, body: input })
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

  keepVideo(token, videoId) {
    return callFastApi<MyVideo>(`/videos/${encodeURIComponent(videoId)}/keep`, {
      method: 'POST',
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

  listRegions(token) {
    return callFastApi<Region[]>('/regions', { method: 'GET', token })
  },

  getTeamMatchPrefs(token, teamId) {
    return callFastApi<TeamMatchPreference>(
      `/teams/${encodeURIComponent(teamId)}/match-preferences`,
      { method: 'GET', token },
    )
  },

  putTeamMatchPrefs(token, teamId, input) {
    return callFastApi<TeamMatchPreference>(
      `/teams/${encodeURIComponent(teamId)}/match-preferences`,
      { method: 'PUT', token, body: input },
    )
  },

  getMyMatchPrefs(token) {
    return callFastApi<MemberMatchPreference>('/me/match-preferences', {
      method: 'GET',
      token,
    })
  },

  putMyMatchPrefs(token, input) {
    return callFastApi<MemberMatchPreference>('/me/match-preferences', {
      method: 'PUT',
      token,
      body: input,
    })
  },

  listMatchCandidates(token, teamId) {
    return callFastApi<MatchCandidate[]>(
      `/teams/${encodeURIComponent(teamId)}/match-candidates`,
      { method: 'GET', token },
    )
  },

  getSquadBySlug(publicSlug) {
    // 🔴 `token` 을 안 넘긴다 — 계약이 이 경로를 인증 없이 열어 두었다.
    return callFastApi<Squad>(`/squads/${encodeURIComponent(publicSlug)}`, { method: 'GET' })
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

  listAdminVideos(token, user) {
    const params = new URLSearchParams({ user })
    return callFastApi<AdminVideoListResult>(`/admin/videos?${params}`, {
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

  /* ── 지인 · 알림 (계약 3-12절) ─────────────────────────────────────── */

  searchUsers(token, q) {
    return callFastApi<UserSearchResult[]>(`/users/search?q=${encodeURIComponent(q)}`, {
      method: 'GET',
      token,
    })
  },

  listContacts(token) {
    return callFastApi<{ items: Contact[] }>('/me/contacts', { method: 'GET', token })
  },

  listContactRequests(token) {
    return callFastApi<ContactRequest[]>('/me/contacts/requests', { method: 'GET', token })
  },

  requestContact(token, input) {
    return callFastApi<ContactRequest>('/me/contacts', { method: 'POST', token, body: input })
  },

  acceptContact(token, contactId) {
    return callFastApi<ContactRequest>(
      `/me/contacts/${encodeURIComponent(contactId)}/accept`,
      { method: 'POST', token },
    )
  },

  listNotifications(token, unreadOnly) {
    // 🔴 안 보낼 때와 `false` 는 서버에서 같은 뜻이다 — 참일 때만 싣는다.
    const qs = unreadOnly ? '?unread_only=true' : ''
    return callFastApi<AppNotification[]>(`/me/notifications${qs}`, { method: 'GET', token })
  },

  readNotification(token, notificationId) {
    return callFastApi<AppNotification>(
      `/me/notifications/${encodeURIComponent(notificationId)}/read`,
      { method: 'PATCH', token },
    )
  },

  /* ── 팀 대 팀 경기 신청 (계약 3-15절) ──────────────────────────────── */

  requestTeamMatch(token, teamId, input) {
    return callFastApi<TeamMatchRequest>(
      `/teams/${encodeURIComponent(teamId)}/match-requests`,
      { method: 'POST', token, body: input },
    )
  },

  listTeamMatchRequests(token, teamId) {
    return callFastApi<TeamMatchRequest[]>(
      `/teams/${encodeURIComponent(teamId)}/match-requests`,
      { method: 'GET', token },
    )
  },

  acceptTeamMatch(token, teamId, requestId) {
    return callFastApi<TeamMatchRequest>(
      `/teams/${encodeURIComponent(teamId)}/match-requests/${encodeURIComponent(requestId)}/accept`,
      { method: 'POST', token },
    )
  },

  rejectTeamMatch(token, teamId, requestId) {
    return callFastApi<TeamMatchRequest>(
      `/teams/${encodeURIComponent(teamId)}/match-requests/${encodeURIComponent(requestId)}/reject`,
      { method: 'POST', token },
    )
  },

  /* ── 표시 등급 · 추천 후보 (계약 3-6·3-16절) ─────────────────────── */

  createTeam(token, input) {
    return callFastApi<TeamDetail>('/teams', { method: 'POST', token, body: input })
  },

  updateTeam(token, teamId, input) {
    return callFastApi<TeamDetail>(`/teams/${encodeURIComponent(teamId)}`, {
      method: 'PATCH',
      token,
      body: input,
    })
  },

  async leaveTeam(token, teamId, memberId) {
    await callFastApi<null>(
      `/teams/${encodeURIComponent(teamId)}/members/${encodeURIComponent(memberId)}`,
      { method: 'DELETE', token },
    )
  },

  async disbandTeam(token, teamId) {
    await callFastApi<null>(`/teams/${encodeURIComponent(teamId)}`, {
      method: 'DELETE',
      token,
    })
  },

  async cancelMatch(token, matchId) {
    await callFastApi<null>(`/matches/${encodeURIComponent(matchId)}`, {
      method: 'DELETE',
      token,
    })
  },

  /* ── 팀 초대 (계약 3-3절, CCC 49·53번) ───────────────────────────── */

  inviteToTeam(token, teamId, input) {
    return callFastApi<TeamInvitation>(
      `/teams/${encodeURIComponent(teamId)}/invitations`,
      { method: 'POST', token, body: input },
    )
  },

  listTeamInvitations(token, teamId) {
    return callFastApi<TeamInvitation[]>(
      `/teams/${encodeURIComponent(teamId)}/invitations`,
      { method: 'GET', token },
    )
  },

  cancelTeamInvitation(token, teamId, invitationId) {
    // 🔴 `204` 가 아니라 무른 초대를 돌려준다 — 같은 파서를 쓴다.
    return callFastApi<TeamInvitation>(
      `/teams/${encodeURIComponent(teamId)}/invitations/${encodeURIComponent(invitationId)}`,
      { method: 'DELETE', token },
    )
  },

  listMyInvitations(token) {
    return callFastApi<ReceivedInvitation[]>('/me/invitations', {
      method: 'GET',
      token,
    })
  },

  acceptInvitation(token, invitationId) {
    return callFastApi<TeamInvitation>(
      `/me/invitations/${encodeURIComponent(invitationId)}/accept`,
      { method: 'POST', token },
    )
  },

  rejectInvitation(token, invitationId) {
    return callFastApi<TeamInvitation>(
      `/me/invitations/${encodeURIComponent(invitationId)}/reject`,
      { method: 'POST', token },
    )
  },

  getCardGrade(token, cardPublicSlug) {
    return callFastApi<CardGrade>(
      `/cards/${encodeURIComponent(cardPublicSlug)}/grade`,
      { method: 'GET', token },
    )
  },

  listSquadCandidates(token, teamId, { position_code, grade }) {
    const q = new URLSearchParams({ position_code })
    // 🔴 「상관없음」은 **안 실어 보낸다** — 계약이 생략과 `"any"` 를 같게 보지만,
    //    빈 값(`grade=`)은 없는 등급이라 422 다(`searchMatches` 와 같은 함정).
    if (grade) q.set('grade', grade)
    return callFastApi<SquadCandidate[]>(
      `/teams/${encodeURIComponent(teamId)}/squad/candidates?${q}`,
      { method: 'GET', token },
    )
  },

  cancelTeamMatch(token, teamId, requestId) {
    // 🔴 204 가 아니라 **취소된 신청을 그대로** 돌려준다(계약) — 다른 응답과
    // 같은 모양이라 부르는 쪽이 갈래를 안 만들어도 된다.
    return callFastApi<TeamMatchRequest>(
      `/teams/${encodeURIComponent(teamId)}/match-requests/${encodeURIComponent(requestId)}`,
      { method: 'DELETE', token },
    )
  },
}
