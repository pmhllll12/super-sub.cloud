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
  /**
   * **지인 검색에 내 닉네임이 뜨는가** (계약 3-12절, CCC 37번). 기본은 `true`.
   *
   * 🔴 용병 매칭의 `is_searchable` 과 **다른 컬럼**이다 — 이쪽은 지인 찾기
   * 노출이고 그쪽은 용병 후보 노출이다. 이름이 닮아 섞기 쉽다.
   *
   * ⚠️ 옛 응답에는 없을 수 있어 선택이다 — 없으면 **켜진 것으로 본다**(서버
   * 기본값과 같게). 모른다고 꺼진 것으로 그리면 사실과 반대가 된다.
   */
  is_nickname_searchable?: boolean
}

/** POST /auth/signup 의 201 응답. teams 가 없다. */
export type SignupResult = Omit<User, 'teams'>

export type Title = {
  code: string
  label: string
  category: string
  granted_at: string
}

/**
 * 카드 꾸미기 — 바탕 · 로고 · 글자 색 · 글자 자리 · 붓자국(미결 `paik` 3번
 * 나머지, CCC 35). 가운데 큰 글자 **내용**은 여기 없다 — `PlayerCard.tagline`
 * 이 그 값이다. 사진도 없다 — 저장 위치가 아직 없어서(`og_image_key` 와 같은
 * 처지) `www` 쪽 `CardStyle`(`app/(app)/me/cardStyle.tsx`)의 photo 관련
 * 필드 넷은 이 타입에 없고 브라우저에만 남는다.
 */
export type CardStyleWire = {
  bg: string
  logo: string
  text_color: string
  text_x: number
  text_y: number
  brush: number
  brush_color: string
  brush_scale: number
  brush_x: number
  brush_y: number
}

export type PlayerCard = {
  id: string
  public_slug: string
  og_image_key: string
  user: { id: string; nickname: string }
  titles: Title[]
  // 사람이 정하는 한 줄. 안 정했으면 null (미결 `paik` 3번).
  tagline: string | null
  // 안 꾸몄으면 null — 화면이 기본 모습을 그린다.
  style: CardStyleWire | null
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

/**
 * `GET /admin/videos?user=` 목록 한 줄 — 한 사람의 영상 전부(저장 안 한 임시분
 * 포함). "에이전트가 제대로 돌았는지" 확인하는 자리라 `analysis_failure_reason`
 * 이 있다 — 일반 사용자 화면(`MyVideo`)엔 없는 필드다.
 */
export type AdminVideoRow = {
  id: string
  sport_code: string
  original_filename: string | null
  storage_key: string
  created_at: string
  kept: boolean
  is_public: boolean
  passed: boolean
  reject_reason: string | null
  analysis_status: 'queued' | 'running' | 'succeeded' | 'failed' | null
  analysis_failure_reason: string | null
  report_prefix: string
}

export type AdminVideoListResult = {
  user_id: string
  nickname: string
  email: string
  items: AdminVideoRow[]
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
  /**
   * 홈 스쿼드 판에서 이 사람이 선 **격자 칸** (2026-09-09, CCC 25).
   *
   * 🔴 **화면 픽셀이 아니다.** 지금 판은 3열(0~2) × 4행(0~3)이고 **행이
   * 포지션 라인**이다 — 0 FW · 1 MF · 2 DF · 3 GK. 카드 크기가 바뀌어도
   * 배치가 안 어긋나라고 칸 번호로 둔 것이다(계약 3-7절 「홈 판 격자」).
   *
   * 판에 안 올린 등재는 **둘 다 `null`** 이다. 한쪽만 채워지는 일은 없다 —
   * 서버가 422 로 막는다.
   */
  grid_col: number | null
  grid_row: number | null
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
  /**
   * 홈 스쿼드 판의 **판 크기** — `"3:3"` · `"5:5"` · `"7:7"`. 아직 안 정했으면
   * `null` (2026-09-09, CCC 25).
   *
   * ⚠️ **서버가 값 집합을 강제하지 않는다**(길이 1~8만 본다) — 판 크기가 늘
   * 때 마이그레이션이 필요 없게 한 판단이다. 그래서 **모르는 값이 올 수 있고**,
   * 화면은 아는 값이 아니면 기본 판으로 연다.
   */
  formation: string | null
  members: SquadMember[]
}

/**
 * 종목 하나의 포지션 — `GET /positions` (api-contract.md 3-3절, 2026-09-09).
 *
 * 🔴 **`code` 는 종목 안에서만 유일하다.** 야구 `C`(포수)와 농구 `C`(센터)는
 * 다른 것이라 전 종목을 받으면 둘 다 실려 온다 — 반드시 `sport_code` 와 짝을
 * 지어 다룬다.
 */
export type Position = {
  sport_code: string
  code: string
  label: string
}

/**
 * 남의 **대표 영상** — `GET /cards/{slug}/featured-video` (3-6절, 2026-09-09).
 *
 * 🔴 `url` 은 저장 키가 아니라 **사전 서명 GET URL** 이고 `expires_in` 초 뒤
 * 만료된다. 캐시하지 말고 재생 직전에 받는다(`playback-url` 과 같은 원칙).
 */
export type FeaturedVideo = {
  video_id: string
  url: string
  expires_in: number
  sport_code: string
  duration_ms: number
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
 * 경기 탐색 한 줄 — `GET /matches` (api-contract.md 3-4절 끝).
 *
 * 🔴 **팀 id 를 몰라도 되는 유일한 경로다.** 그래서 「팀원」 판이 이걸 쓴다 —
 * 아직 사람을 못 채운 팀이 올린 모집 글이 곧 이 목록이다.
 *
 * `Match` 와 달리 **팀 이름 · 지역 · 종목이 함께 온다.** 고르는 기준이 그
 * 셋이라, 없으면 화면이 팀을 한 건씩 다시 물어야 한다(계약이 그렇게 정했다).
 */
export type OpenMatch = Match & {
  team_name: string
  region: string
  sport_code: string
}

/** `GET /matches` 의 페이지 봉투. `GET /admin/users` 와 같은 형식이다. */
export type MatchSearch = {
  items: OpenMatch[]
  total: number
  page: number
  size: number
}

/**
 * `POST /teams/{id}/matches` 의 요청 본문 (api-contract.md 3-4절).
 * `MatchNeed`와 달리 `position_label`이 없다 — 서버가 채워서 돌려준다.
 */
export type CreateMatchInput = {
  played_at: string
  place: string
  needs: { position_code: string; head_count: number }[]
}

/**
 * `POST /matching/search-candidates` — 용병 후보 검색 (api-contract.md 3-11절).
 *
 * `query_text`만 자연어로 보낸다 — **벡터는 여기서 만들지 않는다.** 서버가
 * Gemini로 임베딩을 계산해 pgvector 코사인 유사도로 검색한다.
 */
export type SearchMercenaryCandidatesInput = {
  sport_code: string
  position_code: string
  query_text: string
  limit?: number
}

export type MercenaryCandidate = {
  user_id: string
  nickname: string
  location: string | null
  skill_summary: string | null
  /** 코사인 유사도, 1에 가까울수록 조건에 가깝다. */
  similarity: number
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
  /**
   * **나를 보여주는 대표 영상**인가 (2026-09-09, CCC 27).
   *
   * 🔴 **사람당 하나다** — 새로 세우면 서버가 옛 대표를 자동으로 내린다(DB
   * 부분 유일 인덱스). 그래서 화면은 "지금 어느 것이 대표인가"를 따로 안
   * 들고 있어도 되고, **이 줄이 정본**이다.
   */
  is_featured: boolean
  /**
   * **공개했는가** — 영상 모음(`/home`)에 남에게도 보이는가 (2026-09-08, CCC 20).
   *
   * 🔴 **기본은 비공개다.** 등록(`POST /videos`)으로는 못 정하고 늘 `false` 로
   * 저장된다 — 이미 올라간 클립도 전부 비공개다.
   */
  is_public: boolean
  /** 영상 모음이 큰 글자로 얹는 제목. 100자. 없으면 `null`. */
  title: string | null
  /** 한 줄 설명. 280자. 없으면 `null`. */
  description: string | null
}

/**
 * **남의 것까지 포함한 공개 클립** 한 줄 — `GET /videos/public` (3-6절, CCC 20).
 *
 * 🔴 **저장 키도 업로더도 안 온다.** 저장 키에 업로더의 `user_id` 가 들어
 * 있어서 계약이 일부러 뺐다 — 재생은 `playback-url` 로 따로 받는다.
 *
 * ⚠️ **화면 비율(가로/세로)이 없다.** 미리 알아야 칸이 안 덜컥이는 값인데
 * (`lib/feed.ts` 참고) 계약에 자리가 없어, 화면은 가로(16:9)로 가정하고 그린다 —
 * 세로 영상은 좌우가 남는다. 미결 `paik` 15번으로 올렸다.
 */
export type PublicVideo = {
  id: string
  sport_code: string
  duration_ms: number
  created_at: string
  title: string | null
  description: string | null
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

/**
 * 리포트 항목 하나 — 계약 3-1 `GET /videos/{id}/report` (CCC 31).
 *
 * 🔴 **`grade` 는 점수가 아니라 0~2 등급이고, `null` 은 0 이 아니다** —
 * `skipped: true` 와 짝이라 「평가 대상이 아니었다」는 뜻이다. 0 으로 그리면
 * 못한 것으로 읽힌다.
 * 🔴 `band`·`stat`·가중치는 **응답에 없다**(허용목록) — 기대하지 않는다.
 */
export type ReportCriterion = {
  criterion_id: string
  name: string
  grade: number | null
  title: string | null
  evidence: string | null
  metric_ref: string | null
  skipped: boolean
  /** 레이더 축 값 0~100(CCC 32). `skipped`거나 못 재면 `null` — 0이 아니다. */
  stat: number | null
}

/** 판단의 근거가 된 장면. `at_seconds` 로 그 시각을 찾아간다. */
export type ReportScene = {
  metric_code: string
  label: string
  at_seconds: number
}

/**
 * 적재된 분석 리포트 — 미결 `paik` 7번 · `jin` 27번, CCC 31 · 32.
 *
 * 🔴 **정정 (CCC 32)**: 이 타입이 앞서 "총점·별점 숫자가 없다"고 적었던 것은
 * 틀렸다. 계약 3장 4 가 막은 것은 `summary` 문장 **안에** 숫자를 넣는 것이지
 * `total_score`·`overall_grade`·`breakdown[].stat` 자체가 아니다 — 이 셋은
 * 리포트 경로로 나가는 것이 계약이다. `total_score`·`overall_grade` 는
 * **영상 하나(=분석 1회)** 의 값 — 선수 단위로 합친 오버롤이 아니다. 옛
 * 리포트(이 필드가 생기기 전 적재분)는 둘 다 `null`.
 */
export type VideoReport = {
  video_id: string
  analyzed_at: string
  summary: string
  provisional: boolean | null
  total_score: number | null
  overall_grade: string | null
  breakdown: ReportCriterion[]
  scenes: ReportScene[]
  previews: Record<string, string> | null
  keypoint_quality: Record<string, unknown> | null
}

/**
 * 지인 검색 결과 한 사람 (계약 3-12절, 2026-09-16).
 *
 * 🔴 **닉네임과 id 뿐이다.** 서버가 프로필·카드를 함께 주지 않는다 —
 * 화면에서 더 보여 주고 싶으면 별도 경로로 따로 읽어야 한다.
 */
export type UserSearchResult = {
  id: string
  nickname: string
}

/**
 * 수락된 지인 하나 (계약 3-12절).
 *
 * 🔴 `note` 는 **내가 신청자일 때만** 온다 — 상대 시점에서는 늘 `null` 이다.
 * 버그가 아니다(계약이 그렇게 정했다). 화면이 `note` 없음을 오류로 다루면 안 된다.
 */
export type Contact = {
  contact_id: string
  user_id: string
  nickname: string
  note: string | null
  accepted_at: string
}

/** 나에게 온 **대기중** 지인 신청 (계약 3-12절). 수락 전이라 `accepted_at` 은 늘 null 이다. */
export type ContactRequest = {
  id: string
  requester_user_id: string
  target_user_id: string
  note: string | null
  accepted_at: string | null
  created_at: string
}

/**
 * 알림 하나 (계약 3-12절).
 *
 * 🔴 **문구가 없다.** `type` · `actor_user_id` 만 오므로 문장은 화면이 조립한다 —
 * 서버가 문장을 보낼 것이라고 가정하지 않는다.
 */
export type AppNotification = {
  id: string
  /**
   * 🔴 **닫힌 목록으로 두지 않는다.** 계약이 "지금 나오는 것은 둘뿐"이라고
   * 했지만 3-15절이 팀 경기 쪽 넷을 더 낸다 — 서버가 종류를 더 낼 때
   * 화면이 파싱에서 죽으면 안 되므로 `string` 도 받는다(모르는 종류는
   * 그리지 않고 넘긴다).
   */
  type:
    | 'contact_request'
    | 'contact_accepted'
    | 'team_match_requested'
    | 'team_match_accepted'
    | 'team_match_rejected'
    | 'team_match_cancelled'
    | 'team_match_request_cancelled'
    | (string & {})
  actor_user_id: string
  subject_type: string
  subject_id: string
  read_at: string | null
  created_at: string
}

/**
 * 팀이 팀에게 건 경기 신청 하나 (계약 3-15절, CCC 42번).
 *
 * 🔴 **개인이 모집 경기에 지원하는 것(3-5절)과 다른 개념이다.** 그쪽은 사람이
 * 경기에 들어가는 것이고, 이쪽은 **스쿼드가 다 찬 두 팀이 맞붙는** 것이다 —
 * 같은 화면에 섞으면 무엇을 수락하는 것인지가 흐려진다.
 *
 * `status` 가 `accepted` 가 되면 `match_id` 가 찬다. `cancelled` 는 **내가
 * 무른 것이 아니라** 서버가 정리한 것일 수도 있다 — 한쪽이 다른 경기를
 * 수락하면 그 팀의 남은 `pending` 이 전부 정리된다(이중 예약 방지).
 */
export type TeamMatchRequest = {
  id: string
  requester_team_id: string
  target_team_id: string
  proposed_played_at: string
  proposed_place: string
  status: 'pending' | 'accepted' | 'rejected' | 'cancelled'
  created_at: string
  responded_at: string | null
  /** 수락됐을 때만 찬다 — 확정된 경기 id. */
  match_id: string | null
}

/**
 * 남의 **표시 등급** (계약 3-6절 `GET /cards/{slug}/grade`, CCC 43번).
 *
 * 🔴 **경계는 서버가 긋는다.** 분석 등급(`A`~`D`) 위에 재매칭 의사의 Wilson
 * 95% 신뢰구간을 얹어 `S`~`F` 여섯을 서버가 계산한다 — 화면은 받기만 한다.
 *
 * 🔴 `provisional` 이 `true` 면 **검수 전 루브릭으로 낸 값**이다. 등급 문자만
 * 떼어 쓰면 받는 쪽에서 잠정인지 알 방법이 없어진다 — 남의 화면에 박힌 등급은
 * 회수가 안 된다(정상호 조건, 2026-09-14).
 *
 * `grade` 가 `null` 이면 대표 영상이 없거나 아직 분석 전이다. **`F` 로 치지
 * 않는다** — 「없다」와 「낮다」는 다르다.
 */
export type CardGrade = {
  grade: string | null
  provisional: boolean | null
}

/**
 * 빈 자리에 넣을 **추천 후보** 한 사람 (계약 3-16절, CCC 44번).
 *
 * 🔴 **순서가 곧 추천이다.** 서버가 이미 「이미 앉은 사람들의 등급 평균과
 * 가까운 순」으로 정렬해서 준다 — 화면에서 다시 줄 세우지 않는다. 거리·유사도
 * 점수는 응답에 없다(일부러 안 싣는다).
 *
 * ⚠️ `card_public_slug` 는 **아직 카드를 안 만든 사람이면 `null`** 이다.
 * 대표 영상도 이 슬러그로만 읽으므로 그때는 영상이 없다.
 */
export type SquadCandidate = {
  user_id: string
  nickname: string
  card_public_slug: string | null
  grade: string | null
  provisional: boolean | null
}
