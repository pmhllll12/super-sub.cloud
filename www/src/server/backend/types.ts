export type AuthToken = {
  access_token: string
  token_type: 'bearer'
  expires_in: number
}

export type Team = {
  team_id: string
  name: string
  region: string
  sport_code: string
  role: string
  joined_at: string
}

export type User = {
  id: string
  email: string
  nickname: string
  created_at: string
  teams: Team[]
}

/** POST /auth/signup 의 201 응답. teams 가 없다. */
export type SignupResult = Omit<User, 'teams'>

export type Title = {
  code: string
  label: string
  category: string
  granted_at: string
}

export type PlayerCard = {
  id: string
  public_slug: string
  og_image_key: string
  user: { id: string; nickname: string }
  titles: Title[]
}

/** GET /cards/{slug} — 공개용. id 가 없다. */
export type PublicPlayerCard = Omit<PlayerCard, 'id'>

/** GET /admin/users 목록 항목. */
export type AdminUser = {
  id: string
  email: string
  nickname: string
  created_at: string
}

export type AdminUserListResult = {
  items: AdminUser[]
  total: number
  page: number
  size: number
}

/**
 * 스쿼드에 등재된 한 명 — `GET /teams/{id}/squad` (api-contract.md 3-7절).
 *
 * 🔴 `card_public_slug` 로 그 사람의 공개 카드로 간다. 내부 id 를 밖에
 * 내보내지 않는 것이 카드와 같은 원칙이다.
 */
export type SquadMember = {
  id: string
  player_card_id: string
  card_public_slug: string
  nickname: string
  position_code: string
  position_label: string
}

/**
 * 팀 단위 카드 묶음. **팀당 하나로 다룬다** — 경로가 단수이고 만들기가
 * 멱등이라, 두 번 불러도 슬러그가 바뀌지 않는다.
 *
 * ⚠️ 아직 만들지 않았으면 `GET` 이 404 `SQUAD_NOT_FOUND` 다. 빈 스쿼드를
 * 돌려주지 않는 이유는 "만들지 않은 것"과 "비어 있는 것"이 같아 보이면
 * 안 되기 때문이다(계약 3-7절).
 */
export type Squad = {
  id: string
  team_id: string
  public_slug: string
  members: SquadMember[]
}

/** 경기가 채우려는 자리 하나 — `GET /matches/{id}` 의 `needs[]`. */
export type MatchNeed = {
  position_code: string
  position_label: string
  head_count: number
}

/**
 * 경기 한 건 — `GET /teams/{id}/matches` (api-contract.md 3-4절).
 *
 * 🔴 그 목록은 **다가오는 경기만** 준다. 지난 경기는 빠지므로 "내 경기"를
 * 지난 기록으로 읽으면 안 된다(개별 조회로는 여전히 읽힌다).
 */
export type Match = {
  id: string
  team_id: string
  played_at: string
  place: string
  needs: MatchNeed[]
}

/**
 * 내가 올린 클립 한 줄 — `GET /videos` (api-contract.md 3-6절).
 * `POST /videos` 의 응답과 **같은 모양**이다.
 *
 * 🔴 **재생 · 썸네일 주소가 없다.** 계약이 주는 것은 저장 키뿐이고, 그걸로
 * 브라우저가 S3 를 직접 부를 수는 없다(조회용 사전 서명 URL 경로가 아직
 * 없다). 그래서 목록은 그림 없이 메타로만 그린다.
 */
export type MyVideo = {
  id: string
  sport_code: string
  storage_key: string
  duration_ms: number
  side: string | null
  created_at: string
  /** 규격 검사를 통과했는가. false 면 **분석하지 않는다.** */
  passed: boolean
  reject_reason: string | null
  analysis_job_id: string | null
  /** 가장 최근 분석 작업의 상태. 반려된 클립은 작업이 없어 null 이다. */
  analysis_status: 'queued' | 'running' | 'succeeded' | 'failed' | null
}

/** `Team` 과 달리 나간 소속도 포함하므로 `left_at` 을 갖는다. */
export type AdminMembership = Team & { left_at: string | null }

export type AdminUserDetail = {
  id: string
  email: string
  nickname: string
  created_at: string
  teams: AdminMembership[]
  has_card: boolean
}
