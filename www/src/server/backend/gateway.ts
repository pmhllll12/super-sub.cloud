import type {
  AdminUserDetail,
  AdminUserListResult,
  AuthToken,
  CreateMatchInput,
  PlayerCard,
  PublicPlayerCard,
  Match,
  MyVideo,
  Squad,
  SignupResult,
  User,
} from './types'

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
  /** 🔴 성공하면 **기존 토큰이 전부 무효가 된다**(SEC-004) — 다시 로그인시켜야 한다. */
  changePassword(
    token: string,
    input: { current_password: string; new_password: string },
  ): Promise<void>
  /** 탈퇴. 비밀번호가 없는 계정(구글 전용)은 `password` 를 보내지 않는다. */
  deleteMe(token: string, input: { password?: string }): Promise<void>
  getMyCard(token: string): Promise<PlayerCard>
  /**
   * 카드를 만든다. **멱등** — 이미 있으면 그것을 그대로 돌려준다(슬러그가
   * 바뀌면 이미 공유한 주소가 죽는다).
   * 🔴 `GET` 이 아니라 `POST` 인 이유는 **공개 링크가 생기는 것이 사용자의
   * 행위**여야 하기 때문이다 — 프리페치나 봇이 카드를 만들면 안 된다.
   */
  createMyCard(token: string): Promise<PlayerCard>
  getPublicCard(slug: string): Promise<PublicPlayerCard>
  /** 내가 올린 클립 목록. **최근 것이 앞에 온다.** */
  listMyVideos(token: string): Promise<MyVideo[]>
  /** 그 팀의 **다가오는** 경기. 이른 것이 앞에 온다. */
  listTeamMatches(token: string, teamId: string): Promise<Match[]>
  /** 경기를 새로 연다. 주장만 — 아니면 403 `FORBIDDEN`. */
  createTeamMatch(token: string, teamId: string, input: CreateMatchInput): Promise<Match>
  /** 팀의 스쿼드. 소속이면 본다. **아직 없으면 404 SQUAD_NOT_FOUND** 다. */
  getSquad(token: string, teamId: string): Promise<Squad>
  /** 스쿼드를 연다. **멱등** — 이미 있으면 그것을 그대로 돌려준다. 주장만. */
  createSquad(token: string, teamId: string): Promise<Squad>
  /** 카드를 자리에 등재한다. 주장만. **바뀐 스쿼드 전체**를 돌려준다. */
  addSquadMember(
    token: string,
    teamId: string,
    input: { player_card_id: string; position_code: string },
  ): Promise<Squad>
  /** 등재를 뺀다(카드는 지워지지 않는다). 주장만. */
  removeSquadMember(token: string, teamId: string, memberId: string): Promise<Squad>
  /** 관리자 전용. 관리자가 아니면 403 FORBIDDEN 이 던져진다. */
  listUsers(
    token: string,
    params: { q?: string; page?: number; size?: number },
  ): Promise<AdminUserListResult>
  getUserDetail(token: string, userId: string): Promise<AdminUserDetail>
  forceDeleteUser(token: string, userId: string): Promise<void>
}
