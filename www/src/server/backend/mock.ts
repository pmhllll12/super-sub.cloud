import { BackendError } from './errors'
import type { Backend } from './gateway'
import type {
  AdminUser,
  AdminUserDetail,
  AuthToken,
  PlayerCard,
  PublicPlayerCard,
  SignupResult,
  User,
} from './types'

const DEMO_EMAIL = 'demo@super-sub.example'
const DEMO_PASSWORD = 'supersub2026'
const DEMO_TOKEN = 'mock-access-token-demo'
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
          role: 'member',
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

  async getMyCard(token) {
    const u = requireUser(token)
    if (u.email !== DEMO_EMAIL) {
      // 가입만으로는 카드가 생기지 않는다.
      throw new BackendError(404, 'CARD_NOT_FOUND', '아직 선수 카드가 없습니다.')
    }
    return card
  },

  async getPublicCard(slug) {
    if (slug !== card.public_slug) {
      throw new BackendError(404, 'CARD_NOT_FOUND', '카드를 찾을 수 없습니다.')
    }
    // eslint-disable-next-line @typescript-eslint/no-unused-vars -- 의도적으로 버리는 필드
    const { id: _id, ...rest } = card
    return rest as PublicPlayerCard
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
