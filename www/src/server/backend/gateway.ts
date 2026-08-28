import type { AuthToken, PlayerCard, PublicPlayerCard, SignupResult, User } from './types'

/**
 * FastAPI 와의 유일한 접점. Route Handler 만 이걸 쓴다.
 * 화면 코드는 이 타입을 보지 않는다 — 같은 오리진 /api/* 만 부른다.
 */
export interface Backend {
  signup(input: { email: string; password: string; nickname: string }): Promise<SignupResult>
  login(input: { email: string; password: string }): Promise<AuthToken>
  loginWithGoogle(input: { id_token: string }): Promise<AuthToken>
  getMe(token: string): Promise<User>
  updateMe(token: string, input: { nickname: string }): Promise<User>
  getMyCard(token: string): Promise<PlayerCard>
  getPublicCard(slug: string): Promise<PublicPlayerCard>
}
