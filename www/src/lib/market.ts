/**
 * 레슨 · 상점의 **자리 표시 데이터**.
 *
 * 🔴 전부 mock 이다. 계약(`fastapi/docs/api-contract.md`)에 코치 조회도 브랜드
 * 카탈로그도 아직 없다 — 부록 D.8 이 "브랜드 제휴는 본 개발 기간 범위 밖이므로
 * 테이블을 두지 않는다"고 적어 둔 자리다. **화면이 먼저 가고 그것이 규격의
 * 근거가 된다**(영상 분석 화면이 리포트 조회 규격의 근거가 된 것과 같다).
 *
 * API 가 생기면 이 파일의 상수만 지우고 응답을 흘려 넣으면 된다.
 *
 * 🔴 한 곳에 모아 둔 이유 — 코치도 상품도 **여러 화면이 같이 본다**(목록 ·
 * 상세 · 공개 영상 · 수익). 화면마다 흩어 두면 나중에 API 를 붙일 때 같은
 * 변환을 여러 번 쓰게 된다.
 *
 * 설계 근거는 `www/docs/2026-09-01-레슨-상점-설계.md` 에 있다.
 */

/** 영상 분석과 **같은 종목 코드**를 쓴다 — 두 화면이 갈리면 안 된다. */
export type SportCode = 'soccer' | 'baseball' | 'basketball'

export const SPORT_LABEL: Record<SportCode, string> = {
  soccer: '축구',
  baseball: '야구',
  basketball: '농구',
}

/** 코치가 받는 수강생의 수준. 필터에 쓴다. */
export type Level = 'beginner' | 'intermediate' | 'advanced'

export const LEVEL_LABEL: Record<Level, string> = {
  beginner: '입문',
  intermediate: '중급',
  advanced: '선수 지망',
}

/**
 * 코치 하나.
 *
 * 🔴 `report` 가 이 서비스의 간판이다 — **코치도 우리 분석을 받는다.** 다른
 * 곳은 코치가 자기 실력을 자기소개로 쓰지만, 우리는 수강생과 **같은 잣대로 잰
 * 리포트**를 보여준다. 그래서 모양이 `AnalysisStage` 의 REPORT 와 같다.
 *
 * 🔴 **수치가 없다.** 카드에 능력치 컬럼을 두지 않는 원칙(부록 D.5)이 코치에게도
 * 그대로 적용된다 — 호칭 · 문장 · 장면뿐이다.
 */
export type Coach = {
  id: string
  name: string
  sport: SportCode
  region: string
  /** 목록 카드에 한 줄로 들어간다. */
  tagline: string
  /** 회당 가격(원). 나중에 B(예약·결제)로 갈 때 그대로 쓴다. */
  pricePerSession: number
  levels: Level[]
  /** 우리 분석에서 받은 호칭. 선수 카드에 그대로 실린다. */
  titles: string[]
  /** 코치 본인의 분석 리포트 — 수강생이 받는 것과 같은 형식이다. */
  report: {
    summary: string
    scenes: { at: string; what: string }[]
    /** 이 리포트가 나온 영상. `/v/[slug]` 로 간다. */
    videoSlug: string
    /**
     * 목록 카드 옆에서 **소리 없이 도는 대표 장면**.
     *
     * ⚠️ 지금은 셋 다 **저장소에 넣어 둔 자리 표시 클립**이다(사용자 제공,
     * `public/coach-c00N.mp4`). 계약에 영상 조회가 아직 없어서다(5장 ASM-003,
     * 객체 저장소 미정) — 그쪽이 정해지면 여기 값이 그 주소로 바뀐다.
     * 🔴 영상은 저장소를 무겁게 한다(지금 셋이 16MB). 코치가 늘 때마다 파일을
     * 더 넣지 말고 객체 저장소 이야기를 먼저 꺼낼 것.
     * 값이 없으면 카드는 `poster` 만 보여 준다(`CoachList`).
     */
    clipUrl?: string
    /** 그 장면의 멈춘 그림. 영상이 오기 전까지 카드에 보이는 것이다. */
    clipPoster?: string
  }
  /** 우리가 확인한 것. 코치가 적는 것이 아니라 **우리가 확인한 것**만 적는다. */
  verified: string[]
  reviews: { by: string; text: string; at: string }[]
  lesson: { places: string[]; hours: string; note: string }
}

export const COACHES: Coach[] = [
  {
    id: 'c-001',
    name: '김도현',
    sport: 'soccer',
    region: '서울 강남',
    tagline: '디딤발부터 다시 잡습니다',
    pricePerSession: 60000,
    levels: ['beginner', 'intermediate'],
    titles: ['임팩트 안정', '10경기 연속'],
    report: {
      summary:
        '디딤발이 공보다 앞서지 않습니다. 임팩트에서 무릎이 충분히 덮여 방향이 일정합니다.',
      scenes: [
        { at: '0:04', what: '디딤발 착지' },
        { at: '0:07', what: '임팩트' },
        { at: '0:11', what: '팔로스루' },
      ],
      videoSlug: 'coach-kim-01',
      clipUrl: '/coach-c001.mp4',
    },
    verified: ['신원 확인', '생활체육지도사 2급', '선수 이력 5년'],
    reviews: [
      { by: '이OO', text: '첫 레슨에 제 리포트를 보고 시작해서 헛도는 시간이 없었습니다.', at: '2026-08-20' },
      { by: '박OO', text: '무릎 각도만 두 번 잡아 줬는데 다음 분석에서 바로 달라졌습니다.', at: '2026-08-12' },
    ],
    lesson: { places: ['강남 풋살파크', '역삼 실내구장'], hours: '평일 저녁 · 주말 오전', note: '1회 90분' },
  },
  {
    id: 'c-002',
    name: '정하늘',
    sport: 'basketball',
    region: '서울 마포',
    tagline: '슛 폼은 손보다 발에서 갈립니다',
    pricePerSession: 70000,
    levels: ['intermediate', 'advanced'],
    titles: ['첫 리포트'],
    report: {
      summary: '릴리스 직전 어깨가 먼저 열리지 않습니다. 두 번째 동작으로 이어지는 속도가 빠릅니다.',
      scenes: [
        { at: '0:03', what: '스텝 정지' },
        { at: '0:06', what: '릴리스' },
      ],
      videoSlug: 'coach-jung-01',
      clipUrl: '/coach-c002.mp4',
    },
    verified: ['신원 확인', '대학 선수 이력 4년'],
    reviews: [{ by: '최OO', text: '영상으로 먼저 보고 만나서 설명이 짧았습니다.', at: '2026-08-25' }],
    lesson: { places: ['마포 실내체육관'], hours: '주말 오후', note: '1회 60분 · 2인까지' },
  },
  {
    id: 'c-003',
    name: '오세진',
    sport: 'baseball',
    region: '경기 성남',
    tagline: '스윙 궤도를 눈이 아니라 데이터로',
    pricePerSession: 80000,
    levels: ['beginner', 'intermediate', 'advanced'],
    titles: ['임팩트 안정'],
    report: {
      summary: '히팅 포인트가 몸 앞에서 일정하게 잡힙니다. 팔로스루에서 축이 흔들리지 않습니다.',
      scenes: [
        { at: '0:05', what: '로드' },
        { at: '0:08', what: '임팩트' },
      ],
      videoSlug: 'coach-oh-01',
      clipUrl: '/coach-c003.mp4',
    },
    verified: ['신원 확인', '생활체육지도사 2급', '실업팀 이력 3년'],
    reviews: [],
    lesson: { places: ['성남 실내 배팅장'], hours: '평일 오전 · 저녁', note: '1회 60분' },
  },
]

export function findCoach(id: string): Coach | undefined {
  return COACHES.find((c) => c.id === id)
}

/**
 * 제휴 브랜드의 상품 하나.
 *
 * 🔴 `href` 는 **브랜드 사이트로 나가는 링크**다. 우리는 결제를 받지 않는다 —
 * 나중에 여기에 추적 파라미터(우리 ID + 영상 주인 ID)가 붙는다.
 */
export type Product = {
  id: string
  brand: string
  name: string
  price: number
  sport: SportCode
  category: '신발' | '의류' | '장비'
  /** 브랜드 사이트. 지금은 자리 표시다. */
  href: string
  /** 이 상품이 태그된 영상 수 — 상품 ↔ 영상 양방향이 우리만 가진 것이다. */
  videoCount: number
}

export const PRODUCTS: Product[] = [
  { id: 'p-001', brand: 'NIKE', name: '팬텀 GX', price: 189000, sport: 'soccer', category: '신발', href: 'https://www.nike.com', videoCount: 12 },
  { id: 'p-002', brand: 'ADIDAS', name: '프레데터 24', price: 219000, sport: 'soccer', category: '신발', href: 'https://www.adidas.co.kr', videoCount: 5 },
  { id: 'p-003', brand: 'MIZUNO', name: '프로 글로브', price: 145000, sport: 'baseball', category: '장비', href: 'https://www.mizuno.co.kr', videoCount: 3 },
  { id: 'p-004', brand: 'UNDER ARMOUR', name: '커리 플로우', price: 179000, sport: 'basketball', category: '신발', href: 'https://www.underarmour.co.kr', videoCount: 8 },
  { id: 'p-005', brand: 'NIKE', name: '드라이핏 트레이닝 탑', price: 59000, sport: 'basketball', category: '의류', href: 'https://www.nike.com', videoCount: 2 },
  { id: 'p-006', brand: 'ADIDAS', name: '팀 트랙탑', price: 89000, sport: 'soccer', category: '의류', href: 'https://www.adidas.co.kr', videoCount: 4 },
]

export function findProduct(id: string): Product | undefined {
  return PRODUCTS.find((p) => p.id === id)
}

/** 12,345원 꼴. 금액이 여러 화면에 나오므로 한 곳에서 만든다. */
export function won(n: number): string {
  return `${n.toLocaleString('ko-KR')}원`
}
