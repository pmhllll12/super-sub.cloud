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
