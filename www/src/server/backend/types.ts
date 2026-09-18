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
  /** 🔴 **사람이 직접 적은 호칭은 `custom:` 으로 시작한다**(계약 51). */
  code: string
  label: string
  /**
   * 분류 — `강점`·`활동`·`용병` 셋 중 하나.
   *
   * 🔴 **직접 적은 호칭은 `null` 이다**(계약 51, 2026-09-16). 분류는 부여되는
   * 호칭의 것이고 자유 입력에는 매길 사람이 없다(`paik` 36번의 「분류를
   * 요구하지 말 것」을 서버가 그렇게 지켰다).
   */
  category: string | null
  granted_at: string
}

/**
 * 카드 꾸미기 — 바탕 · 로고 · 글자 색 · 글자 자리 · 붓자국(미결 `paik` 3번
 * 나머지, CCC 35). 가운데 큰 글자 **내용**은 여기 없다 — `PlayerCard.tagline`
 * 이 그 값이다.
 *
 * 🔴 **정정 (2026-09-18): 사진이 들어왔다.** 앞서 여기에 "사진도 없다 —
 * 저장 위치가 아직 없어서 브라우저에만 남는다"고 적어 두었는데, 자리를 정했다:
 * **바이트는 S3, 여기에는 키만**(`photo_key`). data URL 로 담으면 카드를 읽는
 * 모든 응답에 사진이 실린다 — 스쿼드 판 하나가 자리마다 카드를 부른다.
 *
 * 🔴 **다섯 칸은 서버에서 기본값이 있다** — 안 보내도 응답에는 늘 실려 온다.
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
  /* 🔴 **아래 다섯은 선택이다** — 서버에는 기본값이 있어 응답에 늘 실리지만,
     **배포 전 실서버는 아직 안 보낸다.** 필수로 두면 그 사이 옛 응답을
     받은 화면이 타입상 거짓말을 하게 된다(`accepted_at` 과 같은 판단). */
  /** S3 키. `null` 이면 사진을 안 쓴다 — 읽을 주소는 `PlayerCard.photo_url`. */
  photo_key?: string | null
  photo_scale?: number
  /** 🔴 글자 자리와 달리 **음수가 된다** — 사진은 칸보다 크게 잡아 밀어 넣는다. */
  photo_x?: number
  photo_y?: number
  mode?: 'cutout' | 'full'
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
  /**
   * 사진을 읽을 주소 — **사전 서명이라 유효 시간이 있고 저장되지 않는다**
   * (부를 때마다 새로 온다). `style.photo_key` 에서 나온다.
   *
   * 🔴 **`null`·없음이 여럿이고 전부 정상**이다: 사진을 안 올렸다 ·
   * 저장소가 설정 안 됐다 · 키는 있는데 파일이 아직 없다 · **배포 전 실서버라
   * 아직 안 보낸다.** 그때 화면은 기본 장식 그림을 그린다.
   */
  photo_url?: string | null
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
  /**
   * **수락한 시각** — 비어 있으면 아직 **수락 대기중**이다(미결 `paik` 37번).
   *
   * 🔴 스쿼드가 팀 밖 사람도 받게 열리면서(사용자 결정, (나)안) 「앉혔다」와
   * 「그 사람이 오기로 했다」가 갈렸다. 팀원은 앉는 즉시 채워지고, 추천·지인
   * 으로 부른 사람은 **그 사람이 수락해야** 채워진다.
   *
   * ⚠️ **옵션이다** — 백엔드가 아직 안 낸다. 안 오면 화면은 「대기중」으로
   * 본다(앉혔다는 것만 아는 상태라 그편이 맞다).
   */
  accepted_at?: string | null
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
  /**
   * 🔴 **다른 도메인이 포지션을 지목할 때 쓰는 값**(2026-09-17에 실렸다).
   * 내 경기 조건이 포지션을 `position_ids` 로 받는데(계약 3-13절), 약칭은
   * **종목 안에서만** 유일해서 `code` 로는 한 줄을 못 가리킨다 — 지역이
   * 이름 대신 `id` 로 오가는 것과 같은 이유다.
   */
  id: string
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
/**
 * **등록 응답** — `MyVideo` 에 「같은 영상을 다시 올렸다」는 사실이 더 붙는다
 * (CCC 48, 미결 `ho` 41번).
 *
 * 🔴 **세 필드는 등록 응답에만 산다.** 나중에 `GET /videos` 로 같은 영상을
 * 다시 읽으면 전부 `null` 이고 그 영상 자신은 작업이 없어 `analysis_status`
 * 까지 `null` 이다 — **받는 즉시 화면에 반영해야** 다시 볼 방법이 있다.
 *
 * 🔴 **「이 사람으로 분석」·「집중해서 볼 항목」을 지정한 업로드는 대상이
 * 아니다**(늘 새로 분석한다). 그런 등록에서 안 와도 버그가 아니다.
 */
export type RegisteredVideo = MyVideo & {
  /** 앞서 올린 같은 영상의 id. 없으면 중복이 아니다. */
  duplicate_of_video_id?: string | null
  duplicate_status?: 'queued' | 'running' | 'succeeded' | 'failed' | null
  /** 그때 떨어진 사유(에이전트 문구). `failed` 일 때만 값이 있다. */
  duplicate_failure_reason?: string | null
}

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
 * 🔴 **정정 (CCC 46, 2026-09-16)**: 앞서 "화면 비율이 없다"고 적었던 것은 이제
 * 틀렸다 — 미결 `paik` 15번의 답으로 `width`·`height` 가 실려 온다.
 */
export type PublicVideo = {
  id: string
  sport_code: string
  duration_ms: number
  created_at: string
  title: string | null
  description: string | null
  /**
   * 원본 화면 크기(px) — 등록할 때 받은 값 그대로다.
   *
   * 🔴 **둘 다 `null` 일 수 있다** — 이 컬럼이 생기기 전 등록분이다. **에러가
   * 아니다**(계약 3-6절). 그때는 화면이 16:9 로 가정한다(그전까지의 동작).
   *
   * 🔴 미리 알아야 하는 값이다. 영상을 읽어서 알아내면 그때 칸 크기가 바뀌어
   * 화면이 한 번 덜컥한다 — 목록 응답만으로 아는 것이 이 필드의 목적이다.
   */
  width: number | null
  height: number | null
  /**
   * **올린 사람의 닉네임** — 늘 온다(CCC 39, 2026-09-15).
   *
   * 🔴 **이게 없어서 남의 공개 영상도 보는 사람 이름으로 그려졌다**(미결
   * `paik` 16번). 목록에 남의 것이 섞이는데 화면이 「나」 하나만 알고 있었다.
   */
  uploader_nickname: string
  /**
   * 그 사람 카드의 공개 슬러그 — **카드를 만든 사람만** 있고 없으면 `null`.
   *
   * 🔴 `null` 이면 **링크를 안 걸면 그만**이다. 「카드 없음」이라고 따로 알릴
   * 필요 없다(계약의 「하지 말 것」). raw `user_id` 나 저장 키는 **안 온다** —
   * 링크는 이 값으로만 건다.
   */
  uploader_card_slug: string | null
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
  /**
   * 🔴 **모든 등급에 있다** — 0등급도 「무너지는 축」 같은 문구를 받는다.
   * 이 값의 유무로 「받은 호칭」을 가르면 못한 항목에 호칭을 달게 된다.
   * 가르는 것은 아래 `title_earned` 다.
   */
  title: string | null
  /**
   * 그 `title` 이 **실제로 받은 호칭인지**(CCC 47, 미결 `ho` 40번 · `paik` 23번).
   *
   * 🔴 `null` 이면 `skipped` 거나 이 필드가 생기기 전 적재분이다 — **거짓으로
   * 지어내지 않는다.** 흐린 칭호·자물쇠·「미달」은 전부 미달 표식이라,
   * 아무것도 안 그리는 것이 맞다. `grade === 2` 로 대신 긋지도 않는다
   * (조건에 "루브릭이 그 등급의 문구를 실제로 적었을 것"이 함께 걸려 있어
   * 칭호를 안 쓴 루브릭이 들어오면 갈린다).
   */
  title_earned: boolean | null
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
    // 팀 초대(CCC 49·53) — 보낼 때 받는 사람에게, 답할 때 그 팀 주장에게.
    // 🔴 **무르기는 알림이 없다** — 보낸 쪽이 스스로 하는 것이라 알릴 상대가 없다.
    | 'team_invitation_sent'
    | 'team_invitation_accepted'
    | 'team_invitation_rejected'
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
  /**
   * 두 팀의 **이름·지역** (CCC 55, 미결 `paik` 31번).
   *
   * 🔴 **알림 줄이 이 값을 쓴다** — 전에는 화면의 붙박이 목록에서 찾고 못
   * 찾으면 「상대 팀」이라 적었다. 이름을 지어내지 않으려고 걷었다.
   *
   * 🔴 **캐시하지 않는다.** 서버가 매번 `team` 에서 읽어서, 팀 이름이 바뀌면
   * (`PATCH /teams/{id}`) 다음 조회에 바로 반영된다.
   *
   * 🔴 **id 칸은 그대로다** — 이름은 표시용이고 팀을 가리키는 것은 id 다.
   */
  requester_team_name: string | null
  requester_team_region: string | null
  target_team_name: string | null
  target_team_region: string | null
  /**
   * 두 팀 **스쿼드의 공개 슬러그** (2026-09-17, `paik` 22번 후속).
   *
   * 🔴 **대기 화면이 상대 판을 그리는 값이다.** 전에는 화면이 붙박이 목록
   * (`teamMatch.ts` 의 `TEAMS`)에서 상대 팀 이름·판을 찾았고, 그 목록에 없는
   * 진짜 팀이 수락하면 이름이 「상대 팀」으로 나오고 판이 비었다.
   *
   * ⚠️ **스쿼드를 아직 안 만든 팀이면 `null` 이고 그게 정상이다** — 생성이
   * 멱등이라 늦게 생긴다. 그때는 판 없이 이름·지역만 그린다.
   */
  requester_squad_public_slug: string | null
  target_squad_public_slug: string | null
}

/**
 * **팀 초대 한 건** (계약 3-3절 「팀 초대」, CCC 49·53번).
 *
 * 🔴 **동의 없이 꽂지 않는다**(2026-09-10 박민호 결정). 주장이 초대를 보내고
 * 받은 사람이 수락해야 팀원이 된다 — `POST /teams/{id}/members` 로 바로 넣는
 * 길은 **본인이 스스로 가입할 때만** 쓴다.
 *
 * 🔴 **판에 앉힌 자리가 여기 남는다**(`position_code`). 그래서 새로고침해도
 * 그 자리가 살아 있고, **사라지는 것은 상대가 거절하거나 주장이 무를 때뿐**
 * 이다(사용자 설계, 2026-09-17).
 */
export type TeamInvitation = {
  id: string
  team_id: string
  invited_user_id: string
  status: 'pending' | 'accepted' | 'rejected' | 'cancelled'
  created_at: string
  responded_at: string | null
  /**
   * 부르는 자리 — 🔴 **둘 다 `null` 일 수 있다.** 자리를 안 정한 초대
   * (「우리 팀에 오세요」)가 정상이다. 약칭과 이름을 함께 주는 이유는 구성원
   * 카드와 같다 — 하나만 주면 화면이 나머지를 얻을 경로가 없다.
   */
  position_code: string | null
  position_label: string | null
  /**
   * 초대받은 **사람** — 보낸 초대 목록에만 실린다(2026-09-17).
   *
   * 🔴 **판을 되살리는 값이다.** id 만으로는 새로고침 뒤에 누구인지도 무슨
   * 카드인지도 그릴 수 없었다. 카드를 안 만든 사람은 슬러그가 `null` 이고,
   * 그때는 이름표로 남는다.
   */
  invited_user_nickname: string | null
  invited_user_card_slug: string | null
}

/**
 * **내가 받은 초대** — 위에 넉 칸이 더 붙는다(CCC 53).
 *
 * 🔴 받는 사람은 **아직 그 팀 소속이 아니다.** 팀 id 하나로는 이름도 모르는
 * 팀의 초대를 판단할 수가 없어서 서버가 실어 준다(감싸지 않고 덧붙였다).
 *
 * 🔴 **경기 시각·구장은 없다** — 초대는 경기에 묶이지 않는다. 「우리 팀에
 * 오세요」이지 「이 경기에 와 달라」가 아니다.
 */
export type ReceivedInvitation = TeamInvitation & {
  team_name: string
  team_region: string
  team_sport_code: string
  /** 그 팀 판을 보여 줄 값. 스쿼드를 아직 안 만든 팀이면 `null` 이다. */
  squad_public_slug: string | null
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
  /**
   * 분석이 낸 불릿 — **후보 목록의 것과 같은 값**이다(CCC 56). 슬러그만 아는
   * 자리를 위해 여기에도 실린다. 🔴 한 줄·`null` 둘 다 정상이다.
   */
  notes: string[] | null
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
  /**
   * **분석이 낸 불릿 한두 줄** (CCC 56, 미결 `paik` 33·38번 · `ho` 50번).
   *
   * 🔴 **셋 다 정상값이다** — 두 줄 · **한 줄** · `null`. 두 줄을 채우려고
   * 지어내지 않는 것이 에이전트 쪽 규칙이고, `null` 은 옛 봉투(1.4 이하)거나
   * 분석 전이다. **실패로 보지 않는다.**
   *
   * 🔴 **후보마다 `/grade` 를 다시 부르지 않는다** — 목록 응답에 이미 있다.
   *
   * 🔴 **이름 아래 한 줄로 쓰지 않는다.** 그 자리는 **사람이 적는 호칭**이고
   * (CCC 51 · `paik` 36번), 이건 그 아래 불릿이다 — 섞으면 팀장이 사람이
   * 적은 글을 AI 판정으로 읽는다.
   */
  notes: string[] | null
}

/**
 * 팀 하나와 **현재 구성원** — `GET /teams/{id}` · `POST /teams` (계약 3-3절).
 *
 * ⚠️ `Team`(사용자의 소속 한 줄)과 다르다. 저쪽은 `GET /me` 가 주는 요약이고
 * 이쪽은 팀 자신이다 — 나간 사람은 `members` 에 안 담긴다.
 */
export type TeamDetail = {
  id: string
  name: string
  region: string
  sport_code: string
  members: {
    user_id: string
    nickname: string
    role: string
    joined_at: string
    player_card_id: string | null
    card_public_slug: string | null
  }[]
}

/**
 * **지역 한 줄** (계약 3-13절, CCC 40번).
 *
 * 🔴 `label` 이 화면에 그대로 보이는 글자이고(`서울 강남구`), 저장·조회에
 * 쓰는 것은 `id` 다 — 이름으로 보내면 「강남구」·「서울 강남」이 다 다른
 * 값이 되어 대조가 안 된다(`lib/regions.ts` 머리말이 그래서 목록을 뒀다).
 */
export type Region = {
  id: string
  city: string
  district: string
  label: string
}

/**
 * 경기 조건의 시간대 한 칸 (계약 3-13절).
 *
 * 🔴 **`weekday` 는 0(월)~6(일)** 이다 — 화면의 `TimeSlot.day` 는
 * `Date.getDay()` 와 같은 **0(일)~6(토)** 라 **기준이 서로 다르다.**
 * 그냥 넘기면 하루씩 밀린다(`lib/matchPrefs.ts` 의 변환을 거친다).
 * 🔴 시각은 `HH:MM:SS` 다 — 화면은 `HH:MM` 를 쓴다.
 */
export type MatchSlot = {
  weekday: number
  start_time: string
  end_time: string
}

/** 팀 경기 조건 (계약 3-13절). `PUT` 은 **통째로 교체**다. */
export type TeamMatchPreference = {
  team_id: string
  region_ids: string[]
  slots: MatchSlot[]
}

/**
 * **내 경기 조건** (계약 3-13절). `PUT` 은 팀 조건과 마찬가지로 **통째로 교체**다.
 *
 * 🔴 **팀 조건과 저장소가 다르다** — 같은 사람이 팀장이면서 팀원일 수 있어
 * 계약이 둘을 절대 안 섞는다. 「우리 팀이 찾는 경기」와 「내가 뛸 수 있는 때」는
 * 다른 값이다.
 * 🔴 **`position_ids` 가 팀 조건에는 없는 칸**이고, 이게 곧 **내가 남의 AI
 * 추천 후보로 뜨는 조건**이다(서버의 첫 하드 필터). 약칭이 아니라 id 다 —
 * `Position.id` 머리말 참조.
 */
export type MemberMatchPreference = {
  user_id: string
  region_ids: string[]
  slots: MatchSlot[]
  position_ids: string[]
}

/**
 * **「맞는 상대」 후보 한 팀** (계약 3-13절, CCC 40번).
 *
 * 🔴 **유사도 점수가 없다.** 순서는 **서버가 이미 정렬**했고 `reasons` 가
 * 사실값 근거다(「토요일 11:00~12:00 겹침」처럼 이미 문장이다).
 * 🔴 **화면이 겹침을 다시 계산하지 않는다**(계약의 「하지 말 것」) — 다시
 * 계산하면 서버와 다른 답이 나온다.
 * ⚠️ `reasons` 가 빈 배열인 것도 정상이다 — 소프트 근거가 0개라는 뜻이고,
 * 하드 필터는 통과했으므로 목록에는 남는다.
 */
export type MatchCandidate = {
  team_id: string
  team_name: string
  region_label: string
  formation: string
  reasons: { kind: string; detail: string }[]
}
