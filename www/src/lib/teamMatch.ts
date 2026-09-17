import type { PosCode } from '@/lib/pitchGrid'

/**
 * **팀 매칭** — 우리 팀과 조건이 맞는 팀들.
 *
 * ✅ **거의 다 진짜가 됐다.** 신청·알림·수락은 2026-09-16(계약 3-15절),
 * 후보 목록은 2026-09-17(계약 3-13절 · CCC 40번)에 붙었다 — 붙박이 7팀을
 * 크기로 거르고 근거를 `whyMatches()` 로 다시 계산하던 코드는 **걷었다**
 * (계약이 「다시 계산하지 말 것」으로 못 박았다).
 *
 * ⚠️ **아직 남은 mock 하나 — 아래 `TEAMS` · `teamById`.** 대기 팝업
 * (`MatchWaiting`)이 **상대 팀의 이름과 판**을 그리는 데 쓴다.
 * 🔴 **`USE_MOCK` 으로 안 꺼진다**(화면에 박힌 mock 이다) — 그 목록에 없는
 * 진짜 팀이 수락하면 이름이 「상대 팀」으로 나오고 판이 빈다.
 * 🔴 걷으려면 **상대 팀 스쿼드의 공개 슬러그**가 필요하다 — 경기 신청
 * 응답에는 팀 이름·지역만 오고 슬러그가 없다(초대에만 실린다, CCC 53번).
 * 정어진에게 요청할 자리다.
 */

/** 판 위의 한 명 — 읽기 전용 판이 그리는 최소값. */
export type PitchPlayer = {
  nickname: string
  /** 격자 칸. 🔴 화면 픽셀이 아니다(계약 3-7절 「홈 판 격자」). */
  col: number
  row: number
  pos: PosCode
  /** 나인가 — 우리 판에서 **이 자리에만** 진짜 선수 카드를 그린다. */
  mine?: boolean
}

/** 비슷한 팀 한 줄. */
export type MatchTeam = {
  id: string
  name: string
  region: string
  /** 판 크기 — `'3'` · `'5'` · `'7'`. 우리와 같은 것만 온다. */
  size: string
  /** 언제 하는가(ISO). 명단에서는 요일 · 시각으로 줄여 그린다. */
  playedAt: string
  place: string
  /**
   * **왜 이 팀이 비슷한가** — 사용자에게 근거를 그대로 보여 준다.
   *
   * 🔴 **지어내지 않는다. 조건과 대조해서 만든다**(`whyMatches`) — 손으로 적어
   * 두었다가 「토요일」이라 해 놓고 날짜가 일요일인 적이 있었다. 지금은 이
   * 팀의 실제 값과 내 조건이 겹칠 때만 적힌다.
   *
   * 🔴 진짜 RAG 가 붙으면 **이 자리가 그대로 대체된다** — 고른 쪽이 이유를
   * 함께 줘야 하고, 근거 없이 「비슷합니다」만 말하면 목록을 믿을 수 없다.
   */
  why: string[]
  squad: PitchPlayer[]
}

/** 우리 팀 — 대기 팝업의 왼쪽에 선다. */
export type MyTeamSummary = { name: string; squad: PitchPlayer[] }

/**
 * 판 한 벌 — 🔴 **크기마다 자리가 다르다.** `SquadPanel` 의 `FORMATIONS` 와
 * 같은 칸을 써야 대기 팝업의 두 판이 같은 모양으로 선다.
 */
function squad3(n: [string, string, string]): PitchPlayer[] {
  return [
    { nickname: n[0], col: 1, row: 0, pos: 'FW' },
    { nickname: n[1], col: 1, row: 1, pos: 'MF' },
    { nickname: n[2], col: 1, row: 3, pos: 'GK' },
  ]
}

function squad5(n: [string, string, string, string, string]): PitchPlayer[] {
  return [
    { nickname: n[0], col: 1, row: 0, pos: 'FW' },
    { nickname: n[1], col: 0, row: 1, pos: 'MF' },
    { nickname: n[2], col: 2, row: 1, pos: 'MF' },
    { nickname: n[3], col: 1, row: 2, pos: 'DF' },
    { nickname: n[4], col: 1, row: 3, pos: 'GK' },
  ]
}

function squad7(n: [string, string, string, string, string, string, string]): PitchPlayer[] {
  return [
    { nickname: n[0], col: 1, row: 0, pos: 'FW' },
    { nickname: n[1], col: 0, row: 1, pos: 'MF' },
    { nickname: n[2], col: 1, row: 1, pos: 'MF' },
    { nickname: n[3], col: 2, row: 1, pos: 'MF' },
    { nickname: n[4], col: 0, row: 2, pos: 'DF' },
    { nickname: n[5], col: 2, row: 2, pos: 'DF' },
    { nickname: n[6], col: 1, row: 3, pos: 'GK' },
  ]
}

/**
 * ⚠️ 붙박이 목록. 🔴 **우리와 판 크기가 같은 팀만** 보여 준다 — 5:5 를 짜 놓고
 * 7:7 팀이 나오면 그 자체로 「비슷하다」가 아니다.
 *
 * 🔴 **세 크기를 다 채워 둔다.** 5:5 만 넣어 뒀더니 판을 7:7 로 바꾼 사람에게
 * 「조건이 맞는 팀이 없습니다」만 떴다(사용자 지적, 2026-09-10) — mock 이
 * 비어 있는 것과 조건이 안 맞는 것이 화면에서 같아 보인다.
 */
const TEAMS: Omit<MatchTeam, 'why'>[] = [
  {
    id: 'mt-1',
    name: '번개FC',
    region: '서울 강남구',
    size: '5',
    playedAt: '2026-09-19T10:00:00',
    place: '강남 풋살장 2구장',
    squad: squad5(['정우진', '한서준', '오세영', '문지호', '배준영']),
  },
  {
    id: 'mt-2',
    name: '망원 유나이티드',
    region: '서울 마포구',
    size: '5',
    playedAt: '2026-09-19T09:00:00',
    place: '망원 실내구장 A',
    squad: squad5(['임재현', '고동현', '류시온', '남기준', '천우빈']),
  },
  {
    id: 'mt-3',
    name: '수원 슈터스',
    region: '경기 수원시',
    size: '5',
    playedAt: '2026-09-20T11:00:00',
    place: '수원 스포츠센터',
    squad: squad5(['서동하', '윤태경', '강민석', '조성빈', '백승우']),
  },
  // ── 3:3 ─────────────────────────────────────────────────────────
  {
    id: 'mt-4',
    name: '삼삼오오',
    region: '서울 강남구',
    size: '3',
    playedAt: '2026-09-19T14:00:00',
    place: '역삼 미니풋살장',
    squad: squad3(['하도윤', '신재훈', '권해성']),
  },
  {
    id: 'mt-5',
    name: '반포 트리오',
    region: '서울 서초구',
    size: '3',
    playedAt: '2026-09-20T16:00:00',
    place: '반포 한강공원 구장',
    squad: squad3(['진성우', '유하람', '노건희']),
  },
  // ── 7:7 ─────────────────────────────────────────────────────────
  {
    id: 'mt-6',
    name: '강남 세븐스',
    region: '서울 강남구',
    size: '7',
    playedAt: '2026-09-19T10:00:00',
    place: '대치 축구장',
    squad: squad7(['차민준', '홍시우', '구태양', '양지환', '심재원', '표현우', '방동석']),
  },
  {
    id: 'mt-7',
    name: '한강 유나이티드',
    region: '서울 용산구',
    size: '7',
    playedAt: '2026-09-20T09:30:00',
    place: '이촌 한강 축구장',
    squad: squad7(['설민호', '주하준', '탁서진', '변우성', '남시혁', '연도현', '석준혁']),
  },
]

/**
 * 팀 id 로 그 팀을 찾는다 — **이름을 그릴 때** 쓴다.
 *
 * 🔴 **계약 응답에 팀 이름이 없다**(3-15절 — `requester_team_id` 만 온다).
 * 알림 판이 「망원 유나이티드가 경기를 걸었습니다」라고 쓰려면 id → 이름이
 * 필요한데, 그 경로가 아직 없어서 이 붙박이 목록으로 맞춘다.
 *
 * ⚠️ **진짜 백엔드에서는 여기서 못 찾는 id 가 온다** — 그때는 `null` 이고,
 * 부르는 쪽이 「상대 팀」으로 적는다. 이름을 지어내지 않는다.
 * 계약에 팀 이름을 실어 달라고 미결로 올렸다(paik 「경기 신청 알림에 팀 이름」).
 */
export function teamById(id: string): Omit<MatchTeam, 'why'> | null {
  return TEAMS.find((t) => t.id === id) ?? null
}

/**
 * 경기를 신청한다 — 상대 팀장에게 알림이 가고, **상대가 수락해야** 확정된다.
 *
 * ✅ **2026-09-16 — 진짜 경로에 붙었다**(계약 3-15절, CCC 42번). 전에는
 * 1.4초 뒤 `{accepted:true}` 를 돌려주는 가짜라, 신청하자마자 잡힌 것처럼
 * 보였다.
 *
 * 🔴 **돌려주는 것은 「걸렸다」이지 「잡혔다」가 아니다.** 확정은 상대가
 * 수락하는 순간이고, 그것은 알림으로 온다 — 부르는 쪽이 이 둘을 같은 것으로
 * 다루면 대기 화면이 다시 너무 일찍 뜬다.
 */
export async function applyToTeam(
  myTeamId: string,
  team: Pick<MatchTeam, 'id' | 'playedAt' | 'place'>,
): Promise<{ requestId: string }> {
  const res = await fetch(`/api/teams/${encodeURIComponent(myTeamId)}/match-requests`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      target_team_id: team.id,
      played_at: team.playedAt,
      place: team.place,
    }),
  })
  const body: unknown = await res.json().catch(() => null)
  if (!res.ok) {
    const msg =
      typeof body === 'object' && body !== null && 'error' in body
        ? ((body as { error?: { message?: string } }).error?.message ?? null)
        : null
    throw new Error(msg ?? '경기를 신청하지 못했습니다.')
  }
  return { requestId: (body as { id: string }).id }
}

/**
 * **「맞는 상대」 후보 한 팀** — 서버가 준 것 (계약 3-13절, CCC 40번).
 *
 * 🔴 **`MatchTeam` 과 다르다.** 후보는 **팀**이고 `MatchTeam` 은 붙박이
 * mock 이 갖고 있던 **경기 공고**였다 — 후보에는 경기 시각·구장이 없다.
 * 그 둘은 신청할 때 **우리가 고른다**(`lib/matchProposal.ts` · `lib/venues.ts`).
 */
export type CandidateTeam = {
  id: string
  name: string
  region: string
  /** 판 크기 — `'3'`·`'5'`·`'7'`. 서버가 `"5:5"` 로 주는 것을 앞자리만 쓴다. */
  size: string
  /**
   * **왜 이 팀이 나왔는가** — 🔴 **서버가 준 사실값 문장 그대로**다
   * (「토요일 11:00~12:00 겹침」). 화면이 겹침을 다시 계산하지 않는다
   * (계약의 「하지 말 것」: 다시 계산하면 서버와 다른 답이 나온다).
   *
   * ⚠️ 빈 배열도 정상이다 — 소프트 근거가 0개라는 뜻이고, 하드 필터는
   * 통과했으므로 목록에 남는다.
   */
  why: string[]
}

/**
 * **조건에 맞는 팀들** — 서버가 **이미 정렬해서** 준다.
 *
 * ✅ **2026-09-17 — 진짜 경로에 붙었다**(CCC 40번). 위 `TEAMS` 붙박이 7팀과
 * `whyMatches()` 가 하던 일이다. 🔴 판 크기·자기 팀 제외·로스터 충원·조건
 * 등록 여부는 **서버가 하드 필터로 이미 걸렀다** — 화면이 다시 거르지 않는다.
 *
 * 🔴 **우리가 조건을 안 올렸으면 빈 목록이다** — 서버가 「조건을 하나라도
 * 등록한 팀만」 후보로 고르기 때문이다. 그 규칙의 짝이 곧 「우리도 남의
 * 목록에 안 뜬다」다.
 */
export async function findCandidates(myTeamId: string): Promise<CandidateTeam[]> {
  const res = await fetch(`/api/teams/${encodeURIComponent(myTeamId)}/match-candidates`)
  if (!res.ok) throw new Error('맞는 상대를 찾지 못했습니다.')
  const rows = ((await res.json().catch(() => null)) ?? []) as {
    team_id: string
    team_name: string
    region_label: string
    formation: string
    reasons: { kind: string; detail: string }[]
  }[]
  return rows.map((r) => ({
    id: r.team_id,
    name: r.team_name,
    region: r.region_label,
    // `"5:5"` → `"5"`. 판 크기 표기는 화면이 한 자리로 쓴다(`SquadSize`).
    size: r.formation.split(':')[0],
    why: r.reasons.map((x) => x.detail),
  }))
}
