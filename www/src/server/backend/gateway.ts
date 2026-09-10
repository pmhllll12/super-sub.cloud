import type {
  AdminUserDetail,
  AdminUserListResult,
  AuthToken,
  CreateMatchInput,
  FeaturedVideo,
  MercenaryCandidate,
  PlayerCard,
  Position,
  PublicPlayerCard,
  Match,
  MatchSearch,
  MyVideo,
  PublicVideo,
  SearchMercenaryCandidatesInput,
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
  /**
   * 내 클립을 **부분 수정**한다 — 보낸 것만 바뀐다(계약 3-6절 `PATCH /videos`).
   *
   * 🔴 `is_featured: true` 는 「나를 보여주는 대표 영상」으로 세우는 것이고
   * **사람당 하나**라, 세우면 옛 대표가 서버에서 자동으로 내려간다. 화면이
   * 옛 것을 먼저 내리는 두 번 호출을 하지 않는다 — 그 사이에 끊기면 대표가
   * 하나도 없는 상태로 남는다.
   * 🔴 **반려된 클립(`passed: false`)은 대표가 될 수 없다** — 422 `CANNOT_FEATURE`.
   * 🔴 남의 클립은 404 `VIDEO_NOT_FOUND` 다.
   *
   * 🔴 **셋 중 보낸 것만 바뀐다.** 공개 여부만 토글할 때 제목이 지워지지
   * 않는다 — 그래서 화면이 "안 바꾸는 값"을 다시 실어 보낼 필요가 없다.
   * 🔴 `title`·`description` 에 **`null` 이나 공백을 보내면 지운다**
   * (`PATCH /me/card` 의 `tagline` 과 같은 규칙). 길이는 100 · 280 자다.
   */
  updateVideo(
    token: string,
    videoId: string,
    input: {
      is_featured?: boolean
      is_public?: boolean
      title?: string | null
      description?: string | null
    },
  ): Promise<MyVideo>
  /**
   * **공개된 클립 전부** — 남의 것까지. 최근 것이 앞, 최대 100건(계약 3-6절).
   *
   * 🔴 **로그인이 필요하다.** 익명 홈에서 부를 자리가 생기면 계약을 다시
   * 봐야 한다(정어진 님이 그렇게 적어 두셨다).
   */
  listPublicVideos(token: string): Promise<PublicVideo[]>
  /**
   * 그 사람의 **대표 영상** — 카드 슬러그로 읽는다(계약 3-6절).
   *
   * 🔴 **내부 `user_id` 가 아니라 카드 슬러그다** — 내부 id 를 밖에 내보내지
   * 않는 것이 카드와 같은 원칙이다.
   * 🔴 대표가 없든 슬러그가 없든 그 대표가 반려됐든 **밖에서는 다 404
   * `NO_FEATURED_VIDEO`** 다 — 갈라 주면 남의 상태를 훑을 수 있다.
   */
  getFeaturedVideo(token: string, cardSlug: string): Promise<FeaturedVideo>
  /**
   * 종목별 포지션 목록 — 로그인하면 누구나(계약 3-3절).
   *
   * 🔴 없는 `sport_code` 는 **빈 배열이 아니라 422 `UNKNOWN_SPORT`** 다
   * (`searchMatches` 와 같은 판단) — 오타와 "그 종목 포지션이 아직 없다"가
   * 같아 보이면 안 된다. 그래서 **빈 값을 실어 보내지 않는다.**
   */
  listPositions(token: string, params?: { sport_code?: string }): Promise<Position[]>
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
  /**
   * 용병 후보 검색(api-contract.md 3-11절, min 16·17번) — **SFR-006·007과
   * 별개**다(그쪽은 지원 후 채점·추천, 이건 지원 전 검색). `is_searchable`인
   * 사람만, 유사도 내림차순. 없으면 빈 배열(에러 아님).
   *
   * ⚠️ 아직 `fastapi/app/main.py`에 라우터가 배선되지 않아 지금은 404다
   * (min 17번) — 정어진의 배선을 기다린다.
   */
  searchMercenaryCandidates(
    token: string,
    input: SearchMercenaryCandidatesInput,
  ): Promise<MercenaryCandidate[]>
  /** 팀의 스쿼드. 소속이면 본다. **아직 없으면 404 SQUAD_NOT_FOUND** 다. */
  getSquad(token: string, teamId: string): Promise<Squad>
  /** 스쿼드를 연다. **멱등** — 이미 있으면 그것을 그대로 돌려준다. 주장만. */
  createSquad(token: string, teamId: string): Promise<Squad>
  /**
   * 카드를 자리에 등재한다. 주장만. **바뀐 스쿼드 전체**를 돌려준다.
   *
   * `grid_col`·`grid_row` 는 선택이다 — 등재하면서 홈 판 칸에 바로 올릴 때
   * 준다. 🔴 **함께 주거나 함께 비운다**(한쪽만 = 422).
   */
  addSquadMember(
    token: string,
    teamId: string,
    input: {
      player_card_id: string
      position_code: string
      grid_col?: number | null
      grid_row?: number | null
    },
  ): Promise<Squad>
  /** 등재를 뺀다(카드는 지워지지 않는다). 주장만. */
  removeSquadMember(token: string, teamId: string, memberId: string): Promise<Squad>
  /**
   * 홈 스쿼드 판의 **판 크기**를 저장한다. 주장만. 바뀐 스쿼드 전체를 돌려준다
   * (계약 3-7절 `PATCH /teams/{id}/squad`, 2026-09-09).
   */
  setSquadFormation(token: string, teamId: string, formation: string): Promise<Squad>
  /**
   * 등재 하나의 **포지션 · 판 배치**를 바꾼다. 주장만. 바뀐 스쿼드 전체를
   * 돌려준다 (계약 3-7절, 2026-09-09).
   *
   * 🔴 `position_code` 는 **항상 준다** — 등재는 포지션 없이 존재하지 않는다.
   * 칸만 옮길 때는 지금 코드를 그대로 실어 보낸다.
   * 🔴 `grid_col`·`grid_row` 는 **함께 주거나 함께 비운다.** 둘 다 `null` 이면
   * 등재는 남기고 **판에서만** 뺀다.
   * 🔴 **포지션을 칸에서 역산하지 않는다** — 손으로 정한 값이라 자리와 다를 수 있다.
   */
  updateSquadMember(
    token: string,
    teamId: string,
    memberId: string,
    input: { position_code: string; grid_col: number | null; grid_row: number | null },
  ): Promise<Squad>
  /** 관리자 전용. 관리자가 아니면 403 FORBIDDEN 이 던져진다. */
  listUsers(
    token: string,
    params: { q?: string; page?: number; size?: number },
  ): Promise<AdminUserListResult>
  getUserDetail(token: string, userId: string): Promise<AdminUserDetail>
  forceDeleteUser(token: string, userId: string): Promise<void>
}
