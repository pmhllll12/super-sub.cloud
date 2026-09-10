import { BackendError } from './errors'
import type { Backend } from './gateway'
import type {
  AdminUser,
  AdminUserDetail,
  AuthToken,
  FeaturedVideo,
  Match,
  MercenaryCandidate,
  MyVideo,
  OpenMatch,
  Position,
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
 * 종목별 포지션 — `GET /positions` 가 주는 것(계약 3-3절). 정본은 백엔드
 * 마이그레이션이고 여기 것은 그 사본이다.
 *
 * 🔴 **이 표가 mock 안에서 유일한 포지션 목록이다.** 전에는 등재 검사와 경기
 * 등록 검사가 `{ GK: '골키퍼', … }` 를 각자 들고 있었는데, 그러면 한쪽만
 * 고쳐졌을 때 어느 쪽이 맞는지 알 수 없다 — 화면에서 하드코딩을 걷어낸 것과
 * 같은 이유로 mock 안에서도 한 곳으로 모은다(CCC 28).
 *
 * 🔴 **`code` 는 종목 안에서만 유일하다** — 야구 `C`(포수)와 농구 `C`(센터)가
 * 둘 다 있다. 코드만으로 이름을 찾으면 안 된다.
 */
const POSITIONS: Position[] = [
  { sport_code: 'baseball', code: 'P', label: '투수' },
  { sport_code: 'baseball', code: 'C', label: '포수' },
  { sport_code: 'baseball', code: 'IF', label: '내야수' },
  { sport_code: 'baseball', code: 'OF', label: '외야수' },
  { sport_code: 'basketball', code: 'G', label: '가드' },
  { sport_code: 'basketball', code: 'F', label: '포워드' },
  { sport_code: 'basketball', code: 'C', label: '센터' },
  { sport_code: 'football', code: 'GK', label: '골키퍼' },
  { sport_code: 'football', code: 'DF', label: '수비수' },
  { sport_code: 'football', code: 'MF', label: '미드필더' },
  { sport_code: 'football', code: 'FW', label: '공격수' },
  { sport_code: 'futsal', code: 'GK', label: '골키퍼' },
  { sport_code: 'futsal', code: 'DF', label: '수비수' },
  { sport_code: 'futsal', code: 'MF', label: '미드필더' },
  { sport_code: 'futsal', code: 'FW', label: '공격수' },
]

/** 종목 안에서 포지션 이름을 찾는다. 없으면 `undefined` — 부르는 쪽이 422 를 낸다. */
function positionLabel(sportCode: string, code: string): string | undefined {
  return POSITIONS.find((p) => p.sport_code === sportCode && p.code === code)?.label
}

/**
 * 그 팀의 종목 — 등재 포지션이 **어느 종목의 것인지** 가르는 값이다.
 * 🔴 코드만으로 찾으면 안 되는 이유가 `POSITIONS` 주석에 있다.
 */
function teamSport(u: User, teamId: string): string | undefined {
  return u.teams.find((t) => t.team_id === teamId)?.sport_code
}

/**
 * 판 칸을 검사해 저장할 모양으로 만든다 (계약 3-7절 「홈 판 격자」).
 *
 * 🔴 **함께 주거나 함께 비운다** — 한쪽만 오면 422 다. 조용히 채우면 판에
 * 없어야 할 카드가 0번 칸에 선다.
 * 🔴 서버는 `0 ≤ 값 ≤ 15` 만 본다(화면 픽셀이 실려 오는 것을 막는 방어).
 */
function checkCell(
  col: number | null | undefined,
  row: number | null | undefined,
): { grid_col: number | null; grid_row: number | null } {
  const hasCol = col !== null && col !== undefined
  const hasRow = row !== null && row !== undefined
  if (hasCol !== hasRow) {
    throw new BackendError(422, 'VALIDATION_ERROR', 'grid_col 과 grid_row 는 함께 보냅니다.')
  }
  if (!hasCol) return { grid_col: null, grid_row: null }
  for (const v of [col, row] as number[]) {
    if (!Number.isInteger(v) || v < 0 || v > 15) {
      throw new BackendError(422, 'VALIDATION_ERROR', '판 칸은 0~15 의 격자 번호입니다.')
    }
  }
  return { grid_col: col as number, grid_row: row as number }
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
/**
 * 🔴 **지울 수 있어야 해서 `let` 이다.** 삭제가 진짜로 목록에서 빠지는 것을
 * 이 자리에서 보여 주지 않으면, 계약이 생기기 전까지 그 흐름을 아무도 못
 * 밟아 본다(미결 paik 13번).
 *
 * ⚠️ **mock 으로 지운 것은 새로고침하면 되살아난다.** 버그가 아니라 개발
 * 모드의 성질이다 — Next 는 서버 컴포넌트와 라우트 핸들러를 **다른 모듈
 * 그래프**로 컴파일해서 이 파일이 두 벌 생긴다. 지우기는 라우트 쪽에서
 * 도는데(`/api/videos/[id]`) `/me` 를 그리는 것은 다른 쪽이라, 라우트 쪽만
 * 기억한다(실측 2026-09-08: 같은 영상을 다시 DELETE 하면 404 가 온다).
 *
 * 🔴 **진짜 백엔드에서는 안 그렇다** — 거기서는 상태가 DB 와 S3 에 있다.
 * 이걸 고치겠다고 화면 쪽에 자리를 만들지 말 것.
 */
let DEMO_VIDEOS: MyVideo[] = [
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
    // 🔴 **사람당 하나다** — 셋 중 하나만 true 로 둔다(계약 3-6절).
    is_featured: true,
    /* 하나는 공개로 둔다 — 영상 모음이 서버 목록을 그리는 갈래를 실제로
       밟아 볼 수 있어야 한다(CCC 20). */
    is_public: true,
    title: '왼발 감아차기',
    description: '수비 둘 사이로 들어간 장면',
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
    is_featured: false,
    is_public: false,
    title: null,
    description: null,
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
    is_featured: false,
    is_public: false,
    title: null,
    description: null,
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
 * 용병 후보 검색(`POST /matching/search-candidates`, api-contract.md 3-11절)의
 * mock 데이터. 실제로는 서버가 `query_text`를 임베딩으로 바꿔 코사인 유사도로
 * 정렬하지만, mock은 그럴 이유가 없다 — **포지션이 맞으면 고정 순서로** 준다.
 */
const DEMO_CANDIDATES: Record<string, MercenaryCandidate[]> = {
  GK: [
    {
      user_id: 'c1',
      nickname: '이골키',
      location: '서울 강남',
      skill_summary: '공중볼 처리에 강함, 주말 저녁 위주로 가능',
      similarity: 0.86,
    },
  ],
  FW: [
    {
      user_id: 'c2',
      nickname: '박공격',
      location: '서울 송파',
      skill_summary: '스피드 좋은 윙 포워드, 평일 저녁 가능',
      similarity: 0.79,
    },
  ],
}

/**
 * 모집 중인 경기 — 「팀원」 판이 훑는 목록(`GET /matches`).
 *
 * 🔴 **내 팀 것(`DEMO_MATCHES`)과 갈라 둔다.** 그쪽은 "내 팀의 다가오는 경기"
 * 이고 이쪽은 "남의 팀이 사람을 못 채워 올린 모집 글"이다. 한 배열로 뭉치면
 * 내 팀이 내 팀에 지원하는 목록이 된다.
 *
 * 종목 · 지역이 갈리는 줄을 일부러 섞어 두었다 — 거르기가 실제로 도는지
 * 화면에서 보려면 걸러질 것이 있어야 한다.
 */
const OPEN_MATCHES: OpenMatch[] = [
  {
    id: 'om1',
    team_id: '9a2e0000-0000-4000-8000-000000000101',
    team_name: '번개FC',
    region: '서울 강남구',
    sport_code: 'football',
    played_at: '2026-09-12T10:00:00Z',
    place: '강남 풋살장 1구장',
    needs: [
      { position_code: 'GK', position_label: '골키퍼', head_count: 1 },
      { position_code: 'DF', position_label: '수비수', head_count: 2 },
    ],
  },
  {
    id: 'om2',
    team_id: '9a2e0000-0000-4000-8000-000000000102',
    team_name: '망원 유나이티드',
    region: '서울 마포구',
    sport_code: 'football',
    played_at: '2026-09-13T02:00:00Z',
    place: '망원 축구장',
    needs: [{ position_code: 'MF', position_label: '미드필더', head_count: 3 }],
  },
  {
    id: 'om3',
    team_id: '9a2e0000-0000-4000-8000-000000000103',
    team_name: '수원 슈터스',
    region: '경기 수원시',
    sport_code: 'football',
    played_at: '2026-09-14T09:00:00Z',
    place: '수원 월드컵보조구장',
    needs: [
      { position_code: 'FW', position_label: '공격수', head_count: 1 },
      { position_code: 'GK', position_label: '골키퍼', head_count: 1 },
    ],
  },
  {
    id: 'om4',
    team_id: '9a2e0000-0000-4000-8000-000000000104',
    team_name: '잠실 베어스',
    region: '서울 송파구',
    sport_code: 'baseball',
    played_at: '2026-09-15T01:00:00Z',
    place: '잠실 야구장 보조구장',
    needs: [{ position_code: 'P', position_label: '투수', head_count: 1 }],
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
  /* 아직 안 정한 상태로 둔다 — 화면이 「서버에 없으면 기본 판」 갈래를
     실제로 밟아 봐야 한다(계약 3-7절, 처음엔 null 이다). */
  formation: null,
  members: [
    {
      id: 'sm1',
      player_card_id: '5e7a0000-0000-4000-8000-000000000001',
      card_public_slug: 'hong-gildong-4f2a',
      nickname: '홍길동',
      position_code: 'FW',
      position_label: '공격수',
      grid_col: 1,
      grid_row: 0,
    },
    {
      id: 'sm2',
      player_card_id: '5e7a0000-0000-4000-8000-000000000002',
      card_public_slug: 'kim-chulsoo-1a2b',
      nickname: '김철수',
      position_code: 'MF',
      position_label: '미드필더',
      grid_col: 0,
      grid_row: 1,
    },
    {
      /* 🔴 **판에 안 올린 등재**를 하나 남겨 둔다 — 둘 다 null 인 줄이
         화면에서 어떻게 그려지는지(등재는 됐지만 판에는 없음) 확인할 수
         있어야 한다. */
      id: 'sm3',
      player_card_id: '5e7a0000-0000-4000-8000-000000000003',
      card_public_slug: 'lee-younghee-9c8d',
      nickname: '이영희',
      position_code: 'GK',
      position_label: '골키퍼',
      grid_col: null,
      grid_row: null,
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

  async getPlaybackUrl(token, videoId) {
    requireUser(token)
    const v = DEMO_VIDEOS.find((x) => x.id === videoId)
    if (!v) throw new BackendError(404, 'VIDEO_NOT_FOUND', '그 영상을 찾을 수 없습니다.')
    // mock 의 저장 키는 `public/` 안의 진짜 파일이라 그대로가 곧 재생 주소다.
    // 만료도 없지만 **화면이 그걸 알면 안 된다** — 실물과 같은 모양으로 답한다.
    return { url: v.storage_key, expires_in: 900 }
  },

  async deleteMyVideo(token, videoId) {
    requireUser(token)
    const before = DEMO_VIDEOS.length
    DEMO_VIDEOS = DEMO_VIDEOS.filter((v) => v.id !== videoId)
    // 🔴 없는 것을 지웠다고 하지 않는다 — 화면이 "지워졌다"로 읽고 목록에서
    // 빼 버리면, 실제로는 남아 있는 영상이 사라진 것처럼 보인다.
    if (DEMO_VIDEOS.length === before) {
      throw new BackendError(404, 'VIDEO_NOT_FOUND', '그 영상을 찾을 수 없습니다.')
    }
  },

  async updateVideo(token, videoId, input) {
    requireUser(token)
    const at = DEMO_VIDEOS.findIndex((v) => v.id === videoId)
    // 🔴 남의 클립도 "없음"이다 — 갈라 주면 id 를 훑어 존재를 알아낼 수 있다.
    if (at < 0) throw new BackendError(404, 'VIDEO_NOT_FOUND', '그 영상을 찾을 수 없습니다.')
    const target = DEMO_VIDEOS[at]

    // `is_featured` 는 불리언이라 `null`·생략은 **무시한다**(계약 3-6절 —
    // 보낸 것만 바뀐다). `undefined` 를 false 로 읽으면 제목만 고쳐도 대표가 풀린다.
    if (typeof input.is_featured === 'boolean') {
      if (input.is_featured && !target.passed) {
        throw new BackendError(422, 'CANNOT_FEATURE', '반려된 클립은 대표로 세울 수 없습니다.')
      }
      /* 🔴 **사람당 하나** — 세우면 옛 대표가 여기서 내려간다(진짜 백엔드는
         DB 부분 유일 인덱스가 한다). 화면이 두 번 부르지 않아도 되는 것이
         이 성질 때문이라, mock 도 같은 성질을 지켜야 화면을 확인할 수 있다. */
      DEMO_VIDEOS = DEMO_VIDEOS.map((v) =>
        v.id === videoId
          ? { ...v, is_featured: input.is_featured as boolean }
          : input.is_featured
            ? { ...v, is_featured: false }
            : v,
      )
    }
    /* 🔴 **보낸 것만 바꾼다.** `undefined` 를 값으로 읽으면 공개만 토글해도
       제목이 지워진다 — 계약이 부분 수정으로 정한 이유가 그것이다. */
    if (typeof input.is_public === 'boolean') {
      DEMO_VIDEOS = DEMO_VIDEOS.map((v) =>
        v.id === videoId ? { ...v, is_public: input.is_public as boolean } : v,
      )
    }
    for (const key of ['title', 'description'] as const) {
      if (!(key in input)) continue
      const raw = input[key]
      // `null`·공백은 **지운다**(`tagline` 과 같은 규칙).
      const next = typeof raw === 'string' && raw.trim() ? raw.trim() : null
      const cap = key === 'title' ? 100 : 280
      if (next && next.length > cap) {
        throw new BackendError(422, 'VALIDATION_ERROR', `${key} 가 상한을 넘습니다.`)
      }
      DEMO_VIDEOS = DEMO_VIDEOS.map((v) => (v.id === videoId ? { ...v, [key]: next } : v))
    }
    return DEMO_VIDEOS.find((v) => v.id === videoId) as MyVideo
  },

  async listPublicVideos(token) {
    requireUser(token)
    /* 🔴 **저장 키와 업로더를 안 싣는다** — 저장 키에 업로더의 `user_id` 가
       들어 있어 계약이 일부러 뺐다. mock 이 더 주면 화면이 실물에 없는 값에
       기대게 된다. 재생은 `playback-url` 로 따로 받는다. */
    return DEMO_VIDEOS.filter((v) => v.is_public).map((v) => ({
      id: v.id,
      sport_code: v.sport_code,
      duration_ms: v.duration_ms,
      created_at: v.created_at,
      title: v.title,
      description: v.description,
    }))
  },

  async getFeaturedVideo(token, cardSlug): Promise<FeaturedVideo> {
    requireUser(token)
    /* mock 은 카드가 한 벌뿐이라 데모 카드의 슬러그만 답한다. 🔴 슬러그가
       다르든 대표가 없든 **밖에서는 다 같은 404** 다(계약 3-6절). */
    const v = cardSlug === card.public_slug ? DEMO_VIDEOS.find((x) => x.is_featured) : undefined
    if (!v) throw new BackendError(404, 'NO_FEATURED_VIDEO', '대표 영상이 없습니다.')
    return {
      video_id: v.id,
      // mock 의 저장 키는 `public/` 안의 진짜 파일이라 그대로가 곧 재생 주소다.
      url: v.storage_key,
      expires_in: 900,
      sport_code: v.sport_code,
      duration_ms: v.duration_ms,
    }
  },

  async listPositions(token, params) {
    requireUser(token)
    const sport = params?.sport_code
    if (sport === undefined) return POSITIONS
    // 🔴 없는 종목은 **빈 배열이 아니라 422** 다 — 오타와 "그 종목 포지션이
    // 아직 없다"가 같아 보이면 사용자가 없는 것을 계속 기다린다.
    const hit = POSITIONS.filter((p) => p.sport_code === sport)
    if (!hit.length) throw new BackendError(422, 'UNKNOWN_SPORT', '그런 종목이 없습니다.')
    return hit
  },

  async searchMatches(token, params) {
    requireUser(token)
    // 🔴 오타를 조용히 넘기지 않는다 — 계약이 정한 그대로다. 빈 목록으로
    // 답하면 "그런 종목이 없다"와 "그 종목 경기가 없다"가 같아 보인다.
    const sport = params?.sport_code
    if (sport && !['football', 'baseball', 'basketball'].includes(sport)) {
      throw new BackendError(422, 'UNKNOWN_SPORT', '지원하지 않는 종목입니다.')
    }
    const region = params?.region?.trim().toLowerCase()
    const items = OPEN_MATCHES.filter(
      (m) =>
        (!sport || m.sport_code === sport) &&
        (!region || m.region.toLowerCase().includes(region)),
    )
    const size = params?.size ?? 20
    const page = params?.page ?? 1
    return { items: items.slice((page - 1) * size, page * size), total: items.length, page, size }
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
    const seen = new Set<string>()
    for (const n of needs) {
      if (n.head_count < 1) {
        throw new BackendError(422, 'VALIDATION_ERROR', '인원은 1명 이상이어야 합니다.')
      }
      if (seen.has(n.position_code)) {
        throw new BackendError(422, 'DUPLICATE_POSITION', '같은 포지션을 두 번 적었습니다.')
      }
      seen.add(n.position_code)
      // 🔴 **그 팀 종목 안에서** 찾는다 — 야구 `C`(포수)와 농구 `C`(센터)가
      // 다른 것이라 코드만으로 찾으면 남의 종목 포지션이 통과한다.
      if (!positionLabel(team.sport_code, n.position_code)) {
        throw new BackendError(422, 'UNKNOWN_POSITION', '이 팀 종목에 없는 포지션입니다.')
      }
    }
    const match: Match = {
      id: `m${DEMO_MATCHES.length + 1}`,
      team_id: teamId,
      played_at,
      place,
      needs: needs.map((n) => ({
        ...n,
        position_label: positionLabel(team.sport_code, n.position_code) ?? n.position_code,
      })),
    }
    DEMO_MATCHES.push(match)
    return match
  },

  async searchMercenaryCandidates(token, { position_code, limit }) {
    requireUser(token)
    const candidates = DEMO_CANDIDATES[position_code] ?? []
    return candidates.slice(0, limit ?? 10)
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
    demoSquad = {
      id: 'sq1',
      team_id: teamId,
      public_slug: 'aB3xK9mQ2pL7vN4t',
      formation: null,
      members: [],
    }
    return demoSquad
  },

  async addSquadMember(token, teamId, { player_card_id, position_code, grid_col, grid_row }) {
    const u = requireUser(token)
    if (!demoSquad || demoSquad.team_id !== teamId) {
      throw new BackendError(404, 'SQUAD_NOT_FOUND', '스쿼드를 아직 만들지 않았습니다.')
    }
    if (demoSquad.members.some((m) => m.player_card_id === player_card_id)) {
      throw new BackendError(409, 'ALREADY_ENLISTED', '이미 등재된 카드입니다.')
    }
    const label = positionLabel(teamSport(u, teamId) ?? '', position_code)
    if (!label) {
      throw new BackendError(422, 'UNKNOWN_POSITION', '이 종목에 없는 포지션입니다.')
    }
    const cell = checkCell(grid_col, grid_row)
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
          position_label: label,
          ...cell,
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

  async setSquadFormation(token, teamId, formation) {
    requireUser(token)
    if (!demoSquad || demoSquad.team_id !== teamId) {
      throw new BackendError(404, 'SQUAD_NOT_FOUND', '스쿼드를 아직 만들지 않았습니다.')
    }
    /* 🔴 값 집합(`3:3`·`5:5`·`7:7`)을 **강제하지 않는다** — 계약이 길이만
       본다(판 크기가 늘 때 마이그레이션이 없도록). mock 이 더 좁게 굴면
       화면이 실물에서만 되는 값을 여기서 못 밟아 본다. */
    if (!formation || formation.length > 8) {
      throw new BackendError(422, 'VALIDATION_ERROR', 'formation 은 1~8자입니다.')
    }
    demoSquad = { ...demoSquad, formation }
    return demoSquad
  },

  async updateSquadMember(token, teamId, memberId, { position_code, grid_col, grid_row }) {
    const u = requireUser(token)
    if (!demoSquad || demoSquad.team_id !== teamId) {
      throw new BackendError(404, 'SQUAD_NOT_FOUND', '스쿼드를 아직 만들지 않았습니다.')
    }
    if (!demoSquad.members.some((m) => m.id === memberId)) {
      throw new BackendError(404, 'MEMBER_NOT_FOUND', '그 등재를 찾을 수 없습니다.')
    }
    const label = positionLabel(teamSport(u, teamId) ?? '', position_code)
    if (!label) {
      throw new BackendError(422, 'UNKNOWN_POSITION', '이 종목에 없는 포지션입니다.')
    }
    const cell = checkCell(grid_col, grid_row)
    demoSquad = {
      ...demoSquad,
      members: demoSquad.members.map((m) =>
        m.id === memberId ? { ...m, position_code, position_label: label, ...cell } : m,
      ),
    }
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
