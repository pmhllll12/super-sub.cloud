import type {
  AdminUserDetail,
  AdminUserListResult,
  AuthToken,
  CreateMatchInput,
  PlayerCard,
  PublicPlayerCard,
  Match,
  MatchSearch,
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
  /**
   * 그 클립을 **재생할 수 있는 주소**(사전 서명 GET URL) — 계약 3-6절.
   *
   * 🔴 **캐시하지 않는다.** `expires_in`(기본 900초) 뒤 만료되므로 재생 직전에
   * 받는다. 저장 키를 그대로 `<video src>` 에 넣으면 403 이다.
   * 🔴 공개 클립이면 남의 것도, 내 것이면 비공개여도 받는다. 아니면 404.
   */
  getPlaybackUrl(token: string, videoId: string): Promise<{ url: string; expires_in: number }>
  /**
   * 내가 올린 클립을 **지운다** — 저장소의 영상 파일과 그 분석 리포트까지.
   *
   * 🔴 되돌릴 수 없다. 화면이 먼저 한 번 더 묻는다(`MyVideos`).
   * 🔴 남의 클립은 404 `VIDEO_NOT_FOUND` 다 — "있는데 남의 것"과 "없는 것"을
   *    가르면 남의 클립 id 를 훑어 존재를 알아낼 수 있다.
   *
   * ⚠️ **아직 계약에 없다**(미결 paik 13번). 진짜 백엔드에서는 404 가 온다 —
   * 지금 도는 것은 mock 뿐이다.
   */
  deleteMyVideo(token: string, videoId: string): Promise<void>
  /** 그 팀의 **다가오는** 경기. 이른 것이 앞에 온다. */
  listTeamMatches(token: string, teamId: string): Promise<Match[]>
  /**
   * 모집 중인 경기를 훑는다 — **팀 id 를 몰라도 되는 유일한 경로다.**
   * 「팀원」 판이 쓴다: 아직 사람을 못 채운 팀들의 명단이다.
   *
   * 🔴 **다가오는 것만** 오고 이른 것이 앞이다. 종목 코드가 틀리면 빈 배열이
   * 아니라 422 `UNKNOWN_SPORT` 다 — 오타와 "그런 경기가 없다"가 같아 보이면
   * 사용자가 없는 것을 계속 기다린다.
   */
  searchMatches(
    token: string,
    params?: { sport_code?: string; region?: string; page?: number; size?: number },
  ): Promise<MatchSearch>
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
