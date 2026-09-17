import type { PosCode } from '@/lib/pitchGrid'

/**
 * **팀 매칭** — 우리 팀과 조건이 맞는 팀들.
 *
 * ✅ **거의 다 진짜가 됐다.** 신청·알림·수락은 2026-09-16(계약 3-15절),
 * 후보 목록은 2026-09-17(계약 3-13절 · CCC 40번)에 붙었다 — 붙박이 7팀을
 * 크기로 거르고 근거를 `whyMatches()` 로 다시 계산하던 코드는 **걷었다**
 * (계약이 「다시 계산하지 말 것」으로 못 박았다).
 *
 * ✅ **mock 이 하나도 없다**(2026-09-17). 마지막까지 남아 있던 붙박이 7팀
 * (`TEAMS`)과 `teamById` 를 걷었다 — 대기 팝업이 상대 팀 이름·판을 거기서
 * 찾던 자리였고, **`USE_MOCK` 으로 안 꺼지는 화면 mock** 이라 실제 도메인
 * 에서도 그것이 떴다(목록에 없는 진짜 팀이 수락하면 「상대 팀」에 빈 판).
 * 🔴 경기 신청 응답이 **두 팀 스쿼드의 공개 슬러그**를 실어 주면서
 * (`api-contract.md` 3-15절) `GET /squads/{slug}` 로 상대 판을 진짜로 읽는다.
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
  /**
   * 그 사람 **카드의 공개 슬러그** — 있으면 진짜 카드를 그릴 수 있다
   * (`GET /cards/{slug}`, 2026-09-17 리뷰 판이 쓴다).
   *
   * ⚠️ **없을 수 있다** — 카드를 아직 안 만든 사람이다. 그때는 이름만 그린다.
   */
  cardSlug?: string | null
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
