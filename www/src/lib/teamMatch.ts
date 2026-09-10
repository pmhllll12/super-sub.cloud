import type { PosCode } from '@/lib/pitchGrid'
import { slotsOverlap, type MatchPrefs, type TimeSlot } from '@/lib/matchPrefs'

/**
 * **팀 매칭** — 우리 팀과 조건이 비슷하고 **자리를 다 채운** 팀들.
 *
 * ⚠️ **전부 mock 이다.** 계약에 넷 다 없다:
 *
 *   - 「비슷한 팀」을 골라 주는 경로 (RAG — 무엇을 근거로 비슷하다고 할지가
 *     정해지지 않았다. 미결로 올렸다: 정상호)
 *   - 경기 신청 (`POST /matches/{id}/applications` 는 **사람이 경기에** 지원하는
 *     것이지 **팀이 팀에게** 거는 것이 아니다 — 다른 개념이다. 정어진)
 *   - 상대 팀장에게 가는 **알림**
 *   - 상대의 **수락**
 *
 * 🔴 경로가 생기면 **이 파일만 갈아 끼운다.** 부르는 쪽(`TeamMatch`)은 아래
 * 두 함수만 안다 — `published.ts`·`squadBoard.ts` 가 같은 방식이었다.
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

/** 그 경기가 언제인가 — 조건의 시간대와 견주려고 요일·시각으로 편다. */
function slotOf(playedAt: string): TimeSlot | null {
  const d = new Date(playedAt)
  if (Number.isNaN(d.getTime())) return null
  const p = (n: number) => String(n).padStart(2, '0')
  const from = `${p(d.getHours())}:${p(d.getMinutes())}`
  // 한 경기를 두 시간짜리로 본다 — 끝나는 시각이 계약에 없다(미결로 올렸다).
  const end = new Date(d.getTime() + 2 * 60 * 60 * 1000)
  return { day: d.getDay(), from, to: `${p(end.getHours())}:${p(end.getMinutes())}` }
}

/**
 * **왜 이 팀이 나왔는가** — 조건과 실제로 겹치는 것만 적는다.
 *
 * 🔴 **겹치지 않으면 안 적는다.** 빈 배열이면 「크기만 같다」는 뜻이고, 그것도
 * 사실이다 — 없는 근거를 지어내는 것보다 낫다.
 */
export function whyMatches(team: Omit<MatchTeam, 'why'>, prefs: MatchPrefs): string[] {
  const out: string[] = []
  if (prefs.regions.includes(team.region)) out.push('같은 지역')
  const slot = slotOf(team.playedAt)
  if (slot && prefs.times.some((t) => slotsOverlap(t, slot))) out.push('시간이 맞음')
  out.push(`${team.size} : ${team.size}`)
  return out
}

/**
 * **조건에 맞는 팀들** — 우리와 판 크기가 같고, 조건과 겹치는 쪽이 앞에 온다.
 *
 * 🔴 **안 겹친다고 빼지 않는다.** 조건은 「이런 걸 찾는다」이지 「이것만
 * 보겠다」가 아니다 — 다 빼 버리면 조건을 조금 잘못 적은 사람에게 빈 화면만
 * 남는다. 근거가 많은 쪽을 위로 올리고, 왜 나왔는지는 알약이 말한다.
 *
 * ⚠️ mock 이라 지연을 일부러 둔다 — 즉시 답하면 「찾는 중」 화면을 안 만들게
 * 되고, 진짜 경로가 붙는 날 그 화면이 없다는 것을 알게 된다(`AnalysisChat` 이
 * 같은 이유로 같은 일을 한다).
 */
export function findTeams(size: string, prefs: MatchPrefs): Promise<MatchTeam[]> {
  const found = TEAMS.filter((t) => t.size === size)
    .map((t) => ({ ...t, why: whyMatches(t, prefs) }))
    .sort((a, b) => b.why.length - a.why.length)
  return new Promise((resolve) => setTimeout(() => resolve(found), 500))
}

/**
 * 경기를 신청한다 — 상대 팀장에게 알림이 가고, 수락하면 확정된다.
 *
 * ⚠️ **아무 데도 안 보낸다.** 계약에 없는 경로라, 상대가 수락한 것으로
 * **쳐 준다.** 화면에도 그렇게 적는다 — 숨기면 진짜로 신청된 줄 안다.
 */
export function applyToTeam(_teamId: string): Promise<{ accepted: true }> {
  return new Promise((resolve) => setTimeout(() => resolve({ accepted: true }), 1400))
}
