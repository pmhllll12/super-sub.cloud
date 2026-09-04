import { BackendError } from './errors'
import type { Backend } from './gateway'
import type {
  AdminUser,
  AdminUserDetail,
  AuthToken,
  Match,
  MyVideo,
  Squad,
  PlayerCard,
  PublicPlayerCard,
  SignupResult,
  User,
} from './types'

const DEMO_EMAIL = 'demo@super-sub.example'
const DEMO_PASSWORD = 'supersub2026'
const DEMO_TOKEN = 'mock-access-token-demo'
/** 데모 계정이 속한 팀. 스쿼드 · 경기가 이 id 를 함께 읽는다. */
const DEMO_TEAM_ID = '9a2e0000-0000-4000-8000-000000000002'
const EXPIRES_IN = 604800

/**
 * 이메일 -> 비밀번호. User/SignupResult 는 계약 응답 형태라 비밀번호를 넣지 않는다 —
 * 그래서 별도로 둔다. 프로세스가 살아 있는 동안만 유지된다.
 */
const passwords = new Map<string, string>([[DEMO_EMAIL, DEMO_PASSWORD]])

/** 프로세스가 살아 있는 동안만 유지된다. mock 이므로 이걸로 충분하다. */
const users = new Map<string, User>([
  [
    DEMO_TOKEN,
    {
      id: '3f1c0000-0000-4000-8000-000000000001',
      email: DEMO_EMAIL,
      nickname: '홍길동',
      created_at: '2026-08-25T10:30:00Z',
      teams: [
        {
          team_id: '9a2e0000-0000-4000-8000-000000000002',
          name: '번개FC',
          region: '서울 강남',
          sport_code: 'futsal',
          // 🔴 'owner'다 — 데모 계정으로 주장 전용 흐름(경기 등록 등)까지
          // 확인할 수 있어야 한다. 다른 곳은 이 값을 아직 안 쓴다(2026-09-04
          // 기준 실측 — 바꿔도 기존 동작에 영향 없음).
          role: 'owner',
          joined_at: '2026-07-01T00:00:00Z',
        },
      ],
    },
  ],
])

const card: PlayerCard = {
  id: '7b4d0000-0000-4000-8000-000000000003',
  public_slug: 'hong-gildong-4f2a',
  og_image_key: 'cards/7b4d0000.png',
  user: { id: '3f1c0000-0000-4000-8000-000000000001', nickname: '홍길동' },
  titles: [
    {
      code: 'sharp_shooter',
      label: '슈팅이 매서운',
      category: '강점',
      granted_at: '2026-08-20T12:00:00Z',
    },
    {
      code: 'weekend_regular',
      label: '주말 개근',
      category: '활동',
      granted_at: '2026-08-01T09:00:00Z',
    },
  ],
}

function requireUser(token: string): User {
  const u = users.get(token)
  if (!u) throw new BackendError(401, 'INVALID_TOKEN', '다시 로그인해 주세요.')
  return u
}

/**
 * 실제 백엔드는 `ADMIN_EMAILS` 화이트리스트로 관리자를 가른다(계약 문서 3-2절).
 * mock 에는 그 목록이 없으므로 **데모 계정만 관리자로 취급한다.**
 */
function requireAdmin(token: string): User {
  const u = requireUser(token)
  if (u.email !== DEMO_EMAIL) {
    throw new BackendError(403, 'FORBIDDEN', '관리자만 접근할 수 있습니다.')
  }
  return u
}

/**
 * 데모 계정이 올린 클립들 — **최근 것이 앞에 온다**(계약 3-6절).
 *
 * 🔴 `storage_key` 에 **`public/` 의 목업 영상 경로**를 넣었다(사용자 요청:
 * "우리 목업으로 넣었던 영상 3개를 내가 업로드한 영상이라 생각하고"). 화면은
 * `/` 로 시작하는 키만 그대로 재생한다(`page.tsx` 의 `previewSrc`) — 진짜
 * 백엔드가 주는 키(`videos/<user_id>/<uuid>.mp4`)는 조회용 주소가 아직
 * 없어서(계약 3-6절 "아직 없는 것") 그림 없이 메타만 나온다.
 *
 * 🔴 세 상태를 일부러 갈라 두었다 — 화면이 구분해서 그려야 하는 것이
 * 그것이다: 분석까지 끝난 것 · 분석 중인 것 · 분석 없이 올리기만 한 것.
 */
const DEMO_VIDEOS: MyVideo[] = [
  {
    id: 'v1',
    sport_code: 'football',
    storage_key: '/coach-c002.mp4',
    duration_ms: 13000,
    side: null,
    created_at: '2026-09-03T09:00:00Z',
    passed: true,
    reject_reason: null,
    analysis_job_id: 'j1',
    analysis_status: 'succeeded',
  },
  {
    id: 'v2',
    sport_code: 'football',
    storage_key: '/coach-c001.mp4',
    duration_ms: 5000,
    side: 'right',
    created_at: '2026-09-02T14:20:00Z',
    passed: true,
    reject_reason: null,
    analysis_job_id: 'j2',
    analysis_status: 'running',
  },
  {
    id: 'v3',
    sport_code: 'futsal',
    storage_key: '/coach-c003.mp4',
    duration_ms: 15600,
    side: null,
    created_at: '2026-09-01T11:05:00Z',
    passed: true,
    reject_reason: null,
    // 분석을 걸지 않고 올리기만 한 클립.
    analysis_job_id: null,
    analysis_status: null,
  },
]

/**
 * 번개FC 의 **다가오는** 경기들. 계약대로 이른 것이 앞에 온다.
 * 🔴 지난 경기는 이 목록에 없다 — mock 도 그 성질을 지킨다.
 */
const DEMO_MATCHES: Match[] = [
  {
    id: 'm1',
    team_id: '9a2e0000-0000-4000-8000-000000000002',
    played_at: '2026-09-10T10:00:00Z',
    place: '강남 풋살장 2구장',
    needs: [
      { position_code: 'FW', position_label: '공격수', head_count: 2 },
      { position_code: 'GK', position_label: '골키퍼', head_count: 1 },
    ],
  },
  {
    id: 'm2',
    team_id: '9a2e0000-0000-4000-8000-000000000002',
    played_at: '2026-09-17T19:30:00Z',
    place: '잠실 실내구장 A',
    needs: [{ position_code: 'MF', position_label: '미드필더', head_count: 1 }],
  },
]

/**
 * 데모 팀의 스쿼드. 처음에는 **한 자리만 차 있다** — 내 카드가 FW 에 있고
 * 나머지는 빈 자리다. 화면이 "채워진 자리"와 "빈 자리"를 둘 다 그려야 하기
 * 때문이다.
 *
 * 🔴 mock 은 이걸 **바꿔 가며 들고 있는다.** 등재 · 제외가 서버 없이도
 * 돌아야 화면을 확인할 수 있고, 그래야 실물에 붙였을 때 달라지는 것이
 * 화면이 아니라 데이터뿐이다.
 */
let demoSquad: Squad | null = {
  id: 'sq1',
  team_id: DEMO_TEAM_ID,
  public_slug: 'aB3xK9mQ2pL7vN4t',
  members: [
    {
      id: 'sm1',
      player_card_id: '5e7a0000-0000-4000-8000-000000000001',
      card_public_slug: 'hong-gildong-4f2a',
      nickname: '홍길동',
      position_code: 'FW',
      position_label: '공격수',
    },
    {
      id: 'sm2',
      player_card_id: '5e7a0000-0000-4000-8000-000000000002',
      card_public_slug: 'kim-chulsoo-1a2b',
      nickname: '김철수',
      position_code: 'MF',
      position_label: '미드필더',
    },
    {
      id: 'sm3',
      player_card_id: '5e7a0000-0000-4000-8000-000000000003',
      card_public_slug: 'lee-younghee-9c8d',
      nickname: '이영희',
      position_code: 'GK',
      position_label: '골키퍼',
    },
  ],
}

/** `POST /me/card` 로 생긴 카드들. 데모 계정은 위 `card` 를 그대로 쓴다. */
const made = new Map<string, PlayerCard>()

export const mockBackend: Backend = {
  async signup({ email, password, nickname }) {
    if ([...users.values()].some((u) => u.email === email)) {
      throw new BackendError(409, 'EMAIL_ALREADY_EXISTS', '이미 가입된 이메일입니다.')
    }
    if (password.length < 8) {
      throw new BackendError(422, 'WEAK_PASSWORD', '비밀번호는 8자 이상이어야 합니다.')
    }
    const result: SignupResult = {
      id: `mock-${users.size + 1}`,
      email,
      nickname,
      created_at: '2026-08-28T00:00:00Z',
    }
    // 가입한 계정은 빈 상태로 온다 — 계약서가 강조하는 지점이다.
    users.set(`mock-access-token-${result.id}`, { ...result, teams: [] })
    passwords.set(email, password) // 로그인 때 비교할 수 있도록 기억해 둔다
    return result
  },

  async login({ email, password }) {
    // 이메일이 없는 경우와 비밀번호가 틀린 경우를 구분하지 않는다.
    const entry = [...users.entries()].find(([, u]) => u.email === email)
    const ok = entry && password === passwords.get(email)
    if (!entry || !ok || password.length < 8) {
      throw new BackendError(401, 'INVALID_CREDENTIALS', '이메일 또는 비밀번호가 올바르지 않습니다.')
    }
    return { access_token: entry[0], token_type: 'bearer', expires_in: EXPIRES_IN } as AuthToken
  },

  async loginWithGoogle() {
    return { access_token: DEMO_TOKEN, token_type: 'bearer', expires_in: EXPIRES_IN }
  },

  async getMe(token) {
    return requireUser(token)
  },

  async updateMe(token, { nickname }) {
    const u = requireUser(token)
    const trimmed = nickname.trim() // 서버가 정규화한다
    if (trimmed.length < 1 || trimmed.length > 20) {
      throw new BackendError(422, 'VALIDATION_ERROR', '요청 값이 올바르지 않습니다: nickname')
    }
    const next = { ...u, nickname: trimmed }
    users.set(token, next)
    return next
  },

  async changePassword(token, { current_password, new_password }) {
    const u = requireUser(token)
    if (passwords.get(u.email) !== current_password) {
      throw new BackendError(401, 'INVALID_CREDENTIALS', '현재 비밀번호가 올바르지 않습니다.')
    }
    if (new_password.length < 8) {
      throw new BackendError(422, 'VALIDATION_ERROR', '비밀번호는 8자 이상이어야 합니다.')
    }
    passwords.set(u.email, new_password)
    // 🔴 계약대로 **기존 토큰을 전부 무효로** 만든다(SEC-004). 이걸 빼면
    // 화면이 "다시 로그인" 을 건너뛰어도 잘 도는 것처럼 보여, 실물에서만
    // 터지는 차이가 생긴다.
    for (const [t, user] of [...users.entries()]) {
      if (user.email === u.email) users.delete(t)
    }
  },

  async deleteMe(token, { password }) {
    const u = requireUser(token)
    const known = passwords.get(u.email)
    if (known !== undefined) {
      if (password === undefined) {
        throw new BackendError(422, 'PASSWORD_REQUIRED', '비밀번호가 필요합니다.')
      }
      if (known !== password) {
        throw new BackendError(401, 'INVALID_CREDENTIALS', '비밀번호가 올바르지 않습니다.')
      }
    }
    for (const [t, user] of [...users.entries()]) {
      if (user.email === u.email) users.delete(t)
    }
    passwords.delete(u.email)
  },

  async getMyCard(token) {
    const u = requireUser(token)
    if (u.email === DEMO_EMAIL) return card
    const mine = made.get(u.id)
    // 가입만으로는 카드가 생기지 않는다 — **부탁해야** 생긴다(계약 3장).
    if (!mine) throw new BackendError(404, 'CARD_NOT_FOUND', '아직 선수 카드가 없습니다.')
    return mine
  },

  async createMyCard(token) {
    const u = requireUser(token)
    // 🔴 **멱등이다.** 이미 있으면 그대로 돌려준다 — 슬러그가 바뀌면 이미
    // 공유한 주소가 죽는다(계약 3장).
    if (u.email === DEMO_EMAIL) return card
    const has = made.get(u.id)
    if (has) return has
    const fresh: PlayerCard = {
      id: `card-${u.id}`,
      public_slug: `${u.nickname}-${u.id.slice(0, 4)}`,
      og_image_key: `cards/card-${u.id}.png`,
      user: { id: u.id, nickname: u.nickname },
      // 🔴 호칭은 **빈 배열**이다 — 분석 결과로 붙으므로 만드는 시점에 있을 수 없다.
      titles: [],
    }
    made.set(u.id, fresh)
    return fresh
  },

  async getPublicCard(slug) {
    if (slug !== card.public_slug) {
      throw new BackendError(404, 'CARD_NOT_FOUND', '카드를 찾을 수 없습니다.')
    }
    // eslint-disable-next-line @typescript-eslint/no-unused-vars -- 의도적으로 버리는 필드
    const { id: _id, ...rest } = card
    return rest as PublicPlayerCard
  },

  async listMyVideos(token) {
    requireUser(token)
    return DEMO_VIDEOS
  },

  async listTeamMatches(token, teamId) {
    requireUser(token)
    return DEMO_MATCHES.filter((m) => m.team_id === teamId)
  },

  async createTeamMatch(token, teamId, { played_at, place, needs }) {
    const u = requireUser(token)
    const team = u.teams.find((t) => t.team_id === teamId)
    if (!team) throw new BackendError(404, 'TEAM_NOT_FOUND', '그 팀을 찾을 수 없습니다.')
    if (team.role !== 'owner') {
      throw new BackendError(403, 'FORBIDDEN', '주장만 경기를 등록할 수 있습니다.')
    }
    if (new Date(played_at).getTime() <= Date.now()) {
      throw new BackendError(422, 'PAST_MATCH', '지난 시각입니다.')
    }
    if (needs.length === 0) {
      throw new BackendError(422, 'VALIDATION_ERROR', '필요 포지션이 비어 있습니다.')
    }
    const labels: Record<string, string> = { GK: '골키퍼', DF: '수비수', MF: '미드필더', FW: '공격수' }
    const seen = new Set<string>()
    for (const n of needs) {
      if (n.head_count < 1) {
        throw new BackendError(422, 'VALIDATION_ERROR', '인원은 1명 이상이어야 합니다.')
      }
      if (seen.has(n.position_code)) {
        throw new BackendError(422, 'DUPLICATE_POSITION', '같은 포지션을 두 번 적었습니다.')
      }
      seen.add(n.position_code)
      if (!labels[n.position_code]) {
        throw new BackendError(422, 'UNKNOWN_POSITION', '이 팀 종목에 없는 포지션입니다.')
      }
    }
    const match: Match = {
      id: `m${DEMO_MATCHES.length + 1}`,
      team_id: teamId,
      played_at,
      place,
      needs: needs.map((n) => ({ ...n, position_label: labels[n.position_code] })),
    }
    DEMO_MATCHES.push(match)
    return match
  },

  async getSquad(token, teamId) {
    requireUser(token)
    // 🔴 아직 안 만들었으면 404 다 — 빈 스쿼드를 돌려주면 "만들지 않은 것"과
    // "비어 있는 것"이 화면에서 같아 보인다(계약 3-7절).
    if (!demoSquad || demoSquad.team_id !== teamId) {
      throw new BackendError(404, 'SQUAD_NOT_FOUND', '스쿼드를 아직 만들지 않았습니다.')
    }
    return demoSquad
  },

  async createSquad(token, teamId) {
    requireUser(token)
    // 멱등이다 — 두 번 불러도 슬러그가 바뀌지 않는다.
    if (demoSquad && demoSquad.team_id === teamId) return demoSquad
    demoSquad = { id: 'sq1', team_id: teamId, public_slug: 'aB3xK9mQ2pL7vN4t', members: [] }
    return demoSquad
  },

  async addSquadMember(token, teamId, { player_card_id, position_code }) {
    requireUser(token)
    if (!demoSquad || demoSquad.team_id !== teamId) {
      throw new BackendError(404, 'SQUAD_NOT_FOUND', '스쿼드를 아직 만들지 않았습니다.')
    }
    if (demoSquad.members.some((m) => m.player_card_id === player_card_id)) {
      throw new BackendError(409, 'ALREADY_ENLISTED', '이미 등재된 카드입니다.')
    }
    const labels: Record<string, string> = {
      GK: '골키퍼',
      DF: '수비수',
      MF: '미드필더',
      FW: '공격수',
    }
    if (!labels[position_code]) {
      throw new BackendError(422, 'UNKNOWN_POSITION', '이 종목에 없는 포지션입니다.')
    }
    demoSquad = {
      ...demoSquad,
      members: [
        ...demoSquad.members,
        {
          id: `sm${demoSquad.members.length + 1}`,
          player_card_id,
          card_public_slug: 'hong-gildong-4f2a',
          nickname: '홍길동',
          position_code,
          position_label: labels[position_code],
        },
      ],
    }
    return demoSquad
  },

  async removeSquadMember(token, teamId, memberId) {
    requireUser(token)
    if (!demoSquad || demoSquad.team_id !== teamId) {
      throw new BackendError(404, 'SQUAD_NOT_FOUND', '스쿼드를 아직 만들지 않았습니다.')
    }
    if (!demoSquad.members.some((m) => m.id === memberId)) {
      throw new BackendError(404, 'MEMBER_NOT_FOUND', '그 등재를 찾을 수 없습니다.')
    }
    demoSquad = { ...demoSquad, members: demoSquad.members.filter((m) => m.id !== memberId) }
    return demoSquad
  },

  async listUsers(token, { q, page = 1, size = 20 }) {
    requireAdmin(token)
    let all = [...users.values()]
    if (q) {
      const needle = q.toLowerCase()
      all = all.filter(
        (u) => u.email.toLowerCase().includes(needle) || u.nickname.toLowerCase().includes(needle),
      )
    }
    const total = all.length
    const start = (page - 1) * size
    const items: AdminUser[] = all
      .slice(start, start + size)
      .map(({ id, email, nickname, created_at }) => ({ id, email, nickname, created_at }))
    return { items, total, page, size }
  },

  async getUserDetail(token, userId) {
    requireAdmin(token)
    const u = [...users.values()].find((u) => u.id === userId)
    if (!u) throw new BackendError(404, 'USER_NOT_FOUND', '회원을 찾을 수 없습니다.')
    const detail: AdminUserDetail = {
      id: u.id,
      email: u.email,
      nickname: u.nickname,
      created_at: u.created_at,
      // mock 은 나간 소속을 따로 기억하지 않는다 — 지금 소속만 left_at: null 로 보여준다.
      teams: u.teams.map((t) => ({ ...t, left_at: null })),
      has_card: u.email === DEMO_EMAIL,
    }
    return detail
  },

  async forceDeleteUser(token, userId) {
    requireAdmin(token)
    const entry = [...users.entries()].find(([, u]) => u.id === userId)
    if (!entry) throw new BackendError(404, 'USER_NOT_FOUND', '회원을 찾을 수 없습니다.')
    users.delete(entry[0])
  },
}
