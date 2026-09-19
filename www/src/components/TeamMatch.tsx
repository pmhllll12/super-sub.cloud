'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { applyToTeam, findCandidates, type CandidateTeam } from '@/lib/teamMatch'
import { proposalsFrom, toPlayedAt, type Proposal } from '@/lib/matchProposal'
import { VENUES } from '@/lib/venues'
import MatchPrefsForm from '@/components/MatchPrefs'
import { type MatchPrefs } from '@/lib/matchPrefs'
import { loadTeamPrefs, saveTeamPrefs } from '@/lib/teamPrefsStore'
import { startSeeking, stopSeeking } from '@/lib/seekingStore'
import { useFitToViewport } from '@/lib/useFitToViewport'
import { useWheelTrap } from '@/lib/useWheelTrap'

/**
 * **비슷한 팀 명단** — 「팀 매칭」을 누르면 판 오른쪽에 선다(사용자 요청,
 * 2026-09-10).
 *
 * 자리를 다 채운 팀들 중 **우리와 조건이 비슷한** 쪽을 골라 보여 주고, 줄마다
 * 경기를 신청할 수 있다. 신청하면 상대 팀장의 수락을 기다리고, 수락되면
 * 대기 팝업(`MatchWaiting`)이 뜬다.
 *
 * 🔴 **판을 대신 서지 않고 오른쪽에 선다**(사용자 결정) — 내 스쿼드를 보면서
 * 상대를 골라야 하기 때문이다. 그래서 「팀원」 판(판 자리를 대신 차지)과
 * 다르고, 추천 판 · 챗봇과 **같은 칸을 나눠 쓴다**(한 번에 하나).
 *
 * 🔴 **처음에는 조건부터 묻는다**(사용자 결정, 2026-09-10). 「어느 동네에서 ·
 * 언제」를 모르면 무엇을 비슷하다고 할 근거가 없다 — 명단의 알약이 그 대조
 * 결과다. 한 번 정하면 다음부터는 바로 명단이고, 머리의 「설정 수정」로
 * 다시 연다(설정을 따로 찾아가게 하지 않는다).
 *
 * ⚠️ **여기서 서버로 나가는 것은 하나도 없다** — 무엇이 없는지는
 * `lib/teamMatch.ts` 첫머리에 있다.
 */

/** `2026-09-20T10:00:00` → `토 10:00`. 명단은 훑는 자리라 짧게 적는다. */
function whenText(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const day = ['일', '월', '화', '수', '목', '금', '토'][d.getDay()]
  const p = (n: number) => String(n).padStart(2, '0')
  return `${day} ${p(d.getHours())}:${p(d.getMinutes())}`
}

type State =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'ok'; teams: CandidateTeam[] }

/** 두 자리로 맞춘다 — `datetime-local` 은 `2026-09-05T07:30` 처럼 0 을 요구한다. */
function pad2(n: number): string {
  return String(n).padStart(2, '0')
}

export default function TeamMatch({
  size,
  closing,
  onClose,
  teamId,
  onRequested,
}: {
  /** 우리 판 크기 — **같은 크기의 팀만** 찾는다. */
  size: string
  /** 닫히는 중 — 물러나는 동안 DOM 에 남아야 애니메이션이 보인다. */
  closing: boolean
  onClose: () => void
  /**
   * 내 팀 id — 경기 신청이 이 팀 밑으로 나간다(계약 3-15절).
   * `null` 이면 아직 못 읽었거나 주장인 팀이 없다 — 신청 단추가 안 눌린다.
   */
  teamId: string | null
  /**
   * 신청을 **걸었다**. 🔴 「잡혔다」가 아니다 — 부모가 이 id 를 기억해 두었다가
   * 상대가 수락하는 순간(알림)에 대기 팝업을 띄운다.
   */
  onRequested: (requestId: string, team: CandidateTeam) => void
}) {
  const [state, setState] = useState<State>({ kind: 'loading' })
  /* 🔴 화면 아래로 넘치지 않게 — 「팀원」 판과 같은 상자에 매달려 있어 같은
     문제를 겪는다(`useFitToViewport` 머리말). */
  const fitRef = useFitToViewport<HTMLElement>()
  /** 굴릴 대상 — 판 안의 목록. 아래 휠 처리기가 이것을 대신 굴린다. */
  const listRef = useRef<HTMLUListElement>(null)

  /**
   * **판 안에서 굴리면 페이지가 안 움직인다** (사용자 지적, 2026-09-18:
   * 「팀 매칭 판에서 다른 팀 보려고 스크롤 하면 아예 비디오로 내려와」).
   *
   * 🔴 **영상 쪽 「다음 영상」 목록에서도 같은 일이 났다.** 되풀이하지 않게
   * `lib/useWheelTrap.ts` 로 뺐다 — 왜 이렇게 하는지는 그 머리말에 있다.
   *
   * 🔴 `.ss-tm-list` 에는 이미 `overscroll-behavior: contain` 이 있다. 새는
   * 자리는 **목록 밖**이다 — 머리줄이나 아래 안내 위에서 굴리면 그 휠은
   * 목록이 아니라 **페이지**로 가고, 홈은 아래가 영상 모음이라 거기까지
   * 내려간다. CSS 로는 못 막는다(그 자리들은 스크롤 상자가 아니다).
   *
   * 🔴 **목록이 아직 구를 수 있으면 막지 않는다** — 다 막으면 목록 자체가
   * 안 움직인다. 페이지로 넘어가는 것만 막는 것이 요점이다.
   * 🔴 **`passive: false` 로 붙인다** — React 의 `onWheel` 은 passive 라
   * `preventDefault()` 가 조용히 무시된다.
   */
  useWheelTrap(fitRef, listRef)
  /** 지금 수락을 기다리는 팀. 하나뿐이다 — 두 곳에 동시에 신청하지 않는다. */
  const [waiting, setWaiting] = useState<string | null>(null)
  /** 신청이 실제로 나간 팀 — 줄에 「수락 대기 중」이라고 적는다. */
  const [sentTo, setSentTo] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  /**
   * 정해 둔 조건. `null` 은 **아직 안 정했다**는 뜻이라 조건 판이 뜬다 —
   * 빈 조건(다 지운 것)과 갈라야 한다.
   *
   * 🔴 **그릴 때 저장소를 읽지 않는다**(하이드레이션) — 붙은 뒤에 읽는다.
   * 그동안은 「찾고 있습니다」가 떠 있어 화면이 비지 않는다.
   */
  const [prefs, setPrefs] = useState<MatchPrefs | null>(null)
  const [asking, setAsking] = useState(false)
  const [ready, setReady] = useState(false)
  /* 🔴 **서버에서 읽는다**(CCC 40번). 전에는 `localStorage` 였고, 그래서
     조건이 이 브라우저를 벗어나지 못했다 — 화면은 설정이 끝난 것처럼 보이는데
     **서버에는 아무것도 안 올라가서 우리 팀이 남의 후보 목록에 안 떴다.**
     🔴 팀 id 를 모르면 물을 데가 없다 — 그때는 조건 판부터 띄운다. */
  useEffect(() => {
    if (!teamId) {
      setReady(true)
      setAsking(true)
      return
    }
    let alive = true
    void loadTeamPrefs(teamId)
      .then((saved) => {
        if (!alive) return
        setPrefs(saved)
        setAsking(saved === null)
        setReady(true)
      })
      /* 🔴 **던지면 판이 「찾고 있습니다…」에서 멈춘다**(2026-09-18). 이 통은
         `ready` 가 서야 다음을 그리는데, 조회가 거절되면 그 줄에 영영 못
         닿았다 — 연결이 한 번 끊긴 것뿐인데 판이 굳는다. 못 읽었으면 **조건을
         안 정한 것처럼** 물어본다: 다시 정하면 그대로 이어진다. */
      .catch(() => {
        if (!alive) return
        setAsking(true)
        setReady(true)
      })
    return () => {
      alive = false
    }
  }, [teamId])

  /**
   * ✅ **명단이 서버 것이 됐다**(CCC 40번, 2026-09-17) — 붙박이 7팀과
   * `whyMatches()` 를 걷었다.
   *
   * 🔴 **서버가 이미 정렬해서 준다.** 판 크기·자기 팀 제외·로스터 충원·조건
   * 등록 여부는 하드 필터로 걸러져 오므로 **화면이 다시 거르지 않는다**.
   * 근거(`why`)도 서버가 준 문장 그대로다 — 다시 계산하면 서버와 다른 답이
   * 나온다(계약의 「하지 말 것」).
   */
  useEffect(() => {
    if (!prefs || !teamId) return
    let alive = true
    setState({ kind: 'loading' })
    void findCandidates(teamId)
      .then((teams) => {
        if (alive) setState({ kind: 'ok', teams })
      })
      .catch(() => {
        if (alive) setState({ kind: 'error', message: '맞는 상대를 불러오지 못했습니다.' })
      })
    return () => {
      alive = false
    }
  }, [teamId, prefs])

  /**
   * **신청할 때 고르는 시각·구장** (사용자 요청, 2026-09-17).
   *
   * 🔴 후보에는 시각·구장이 **없다**(팀 후보이지 경기 공고가 아니다). 그런데
   * 신청은 둘을 필수로 받는다 — 그래서 **우리가 제안한다.** 지어내지 않는다:
   * 시각은 **우리가 서버에 올린 조건**에서, 구장은 **경기장 목록**(서울시
   * 공공데이터)에서 온다.
   */
  const proposals = useMemo(() => (prefs ? proposalsFrom(prefs.times) : []), [prefs])
  /** 지금 신청 칸을 열어 둔 팀. 한 번에 하나다. */
  const [picking, setPicking] = useState<string | null>(null)
  const [pickedAt, setPickedAt] = useState<Proposal | null>(null)
  /**
   * **직접 고른 시각** — `datetime-local` 의 값(`2026-09-18T19:30`).
   *
   * 🔴 **제안만으로는 오늘 경기를 못 잡는다.** 제안은 조건(요일+시간대)에서
   * 「**다음에** 오는 그 요일」로 만들어져서(`nextOccurrence`), 조건이
   * 토요일뿐이면 아무리 빨라도 다음 토요일이다. 시연에서 대기 화면 → 경기
   * 끝내기 → 리뷰를 한자리에서 보여 주려면 **몇 분 뒤**로 잡을 수 있어야
   * 한다(사용자 요청, 2026-09-18).
   *
   * 🔴 **제안을 대신하는 것이 아니다** — 비어 있으면 전처럼 제안을 쓴다.
   * 평소에는 그쪽이 맞다(「시각을 지어내지 않는다」).
   */
  const [customAt, setCustomAt] = useState('')

  /**
   * 직접 고른 값을 실제 시각으로. **모양이 덜 됐으면 `null`** 이다 —
   * `datetime-local` 은 사람이 타이핑하는 동안 반쯤 채워진 값을 준다.
   *
   * 🔴 **지난 시각은 안 쓴다.** 서버가 받아 줘도 아무도 못 뛰고, 대기 화면이
   * 열리자마자 「경기 끝내기」로 바뀐다(`matchProposal.ts` 의 같은 판단).
   */
  /** `Date` → `datetime-local` 값(`2026-09-18T19:30`). **지역 시각 그대로**다. */
  const toInput = (at: Date) =>
    `${at.getFullYear()}-${pad2(at.getMonth() + 1)}-${pad2(at.getDate())}` +
    `T${pad2(at.getHours())}:${pad2(at.getMinutes())}`

  const customDate = useMemo(() => {
    if (!customAt) return null
    const at = new Date(customAt)
    if (Number.isNaN(at.getTime())) return null
    return at
  }, [customAt])
  /** 골라 놓고 **지난** 시각이면 신청을 막는다 — 왜 안 눌리는지 옆에 적는다. */
  const customIsPast = customDate !== null && customDate.getTime() <= Date.now()
  /** 달력이 **지난 시각을 못 고르게** 한다 — 막는 것과 별개로 손이 덜 간다. */
  const minAt = toInput(new Date())
  const [pickedPlace, setPickedPlace] = useState<string>('')

  /**
   * 고를 수 있는 구장 — **우리 조건 지역**의 것을 앞에 둔다.
   * ⚠️ 목록이 비지 않게, 지역이 안 맞아도 전부 고를 수 있게 남겨 둔다.
   */
  const venues = useMemo(() => {
    const mine = new Set(prefs?.regions ?? [])
    return [...VENUES].sort((a, b) => Number(mine.has(b.region)) - Number(mine.has(a.region)))
  }, [prefs])

  /**
   * 경기를 건다.
   *
   * 🔴 **여기서 대기 팝업을 띄우지 않는다**(사용자 요청, 2026-09-16). 전에는
   * 가짜 `applyToTeam` 이 1.4초 뒤 "수락됨"을 돌려줘서 신청하자마자 잡힌 것처럼
   * 보였다 — **확정은 상대 팀장이 수락하는 순간**이고, 그것은 알림으로 온다
   * (`useNotifyInbox` → `HomeStage`). 이 줄이 하는 일은 신청을 거는 것까지다.
   *
   * 🔴 **한 번에 한 곳에만 건다.** 서버는 여러 곳에 거는 것을 막지 않지만
   * (수락되면 나머지를 알아서 정리한다), 화면에서 여러 줄이 동시에 「대기 중」
   * 이면 어느 것을 기다리는지가 안 읽힌다.
   */
  async function apply(team: CandidateTeam) {
    if (waiting || !teamId) return
    /* 🔴 **고르지 않았으면 안 보낸다.** 시각·구장을 화면이 채우면 아무도 못
       뛰는 경기가 잡힌다 — 조건이 없으면 고를 것도 없다(`proposals` 가 빈다). */
    /* 🔴 **직접 고른 값이 있으면 그것이 이긴다.** 둘 다 비면 보낼 시각이
       없다 — 조건도 없고 직접 고르지도 않은 경우다. */
    const at = customDate ?? pickedAt?.at ?? null
    if (!at || !pickedPlace) {
      setError('경기 시각과 구장을 고르세요.')
      return
    }
    setWaiting(team.id)
    setError(null)
    try {
      const { requestId } = await applyToTeam(teamId, {
        id: team.id,
        playedAt: toPlayedAt(at),
        place: pickedPlace,
      })
      setPicking(null)
      onRequested(requestId, team)
      setSentTo(team.id)
    } catch (e) {
      setError(e instanceof Error ? e.message : '경기를 신청하지 못했습니다.')
      setWaiting(null)
    }
  }

  return (
    <section
      ref={fitRef}
      className="ss-tm"
      data-closing={closing ? 'true' : undefined}
      aria-label="비슷한 팀"
      /* 🔴 backdrop-filter 는 **인라인으로만** 준다 — globals.css 에 두면
         Lightning CSS 를 지나며 떨어져 나간 전례가 있다.

         🔴 **흐림을 판에서 올린다**(사용자 요청, 2026-09-10 — 「안 읽힌다」).
         줄마다 걸 수가 없다: 이 판이 펼쳐지는 연출로 `transform` 을 계속
         쥐고 있어 **변형된 조상이 backdrop root 를 만들고**, 자식의 흐림은
         조용히 죽는다. 그래서 흐림은 여기서 한 번에 세게 걸고, 글자가
         읽히는 일은 줄의 검은 막(`.ss-tm-row`)이 맡는다.

         ⚠️ `--ss-glass-blur` 를 **전역에서 올리지 않는다** — 로그인 카드 ·
         홈 카드 · 추천 판이 다 같이 흐려진다. 여기서만 배로 쓴다. */
      style={{
        backdropFilter:
          'blur(calc(var(--ss-glass-blur) * 2)) saturate(var(--ss-glass-saturate))',
        WebkitBackdropFilter:
          'blur(calc(var(--ss-glass-blur) * 2)) saturate(var(--ss-glass-saturate))',
      }}
    >
      <header className="ss-tm-head">
        <h2>비슷한 팀</h2>
        <div className="ss-tm-head-right">
          {/* 조건을 정해 둔 뒤에만 나온다 — 정하는 중에 또 열 자리는 없다. */}
          {prefs && !asking && (
            <button type="button" className="ss-tm-edit" onClick={() => setAsking(true)}>
              {/* 🔴 아이콘은 **장식**이라 낭독기에서 숨긴다 — 옆의 글자가
                  이미 무엇인지 말하고 있다(두 번 읽히면 성가시다). */}
              <span className="material-symbols-outlined" aria-hidden="true">
                rule_settings
              </span>
              설정 수정
            </button>
          )}
          {/* 🔴 **× 와 다른 일을 한다**(2026-09-18). × 는 이 판을 닫을 뿐이고
              찾기는 계속된다 — 머리칸에 「팀 찾는 중」이 남는다. 그만두는 길이
              따로 없으면 한 번 시작한 표시를 영영 못 끈다. */}
          {prefs && !asking && (
            <button
              type="button"
              className="ss-tm-edit"
              onClick={() => {
                stopSeeking()
                onClose()
              }}
            >
              <span className="material-symbols-outlined" aria-hidden="true">
                search_off
              </span>
              그만 찾기
            </button>
          )}
          <button type="button" className="ss-tm-close" onClick={onClose} aria-label="닫기">
            <span className="material-symbols-outlined" aria-hidden="true">
              close
            </span>
          </button>
        </div>
      </header>

      {/* 🔴 조건이 먼저다 — 없으면 명단을 아예 안 그린다. */}
      {asking && (
        <MatchPrefsForm
          kind="team"
          value={prefs}
          onDone={(next) => {
            /* 🔴 **여기가 「우리 팀이 남에게 보이기 시작하는」 자리다** —
               서버가 「조건을 하나라도 등록한 팀만」 후보로 고른다(계약
               3-13절). 실패하면 화면이 그것을 숨기지 않고 말한다. */
            setPrefs(next)
            setAsking(false)
            /* 🔴 **「팀 찾기」를 누른 이 순간이 「찾기 시작」이다**(사용자
               요청, 2026-09-18). 이 표시가 있어야 다른 화면으로 가도 머리칸에
               「팀 찾는 중」이 남고, 돌아왔을 때 이 판이 다시 펴진다.
               ⚠️ 조건 저장과 **따로** 둔다 — 저장이 실패해도 찾는 중이라는
               사실 자체는 맞고, 실패는 아래에서 따로 말한다. */
            if (teamId) startSeeking(teamId)
            void saveTeamPrefs(teamId, next).catch(() =>
              setError('조건을 저장하지 못했습니다 — 다시 시도해 주세요.'),
            )
          }}
          /* 처음 묻는 자리에서는 그만둘 데가 없다 — 고칠 때만 준다. */
          onCancel={prefs ? () => setAsking(false) : undefined}
        />
      )}

      {!asking && (!ready || state.kind === 'loading') && (
        <p className="ss-tm-note">비슷한 팀을 찾고 있습니다…</p>
      )}

      {!asking && state.kind === 'error' && (
        <p className="ss-tm-note" role="alert">
          {state.message}
        </p>
      )}

      {!asking && state.kind === 'ok' && state.teams.length === 0 && (
        <p className="ss-tm-note">지금은 조건이 맞는 팀이 없습니다.</p>
      )}

      {!asking && state.kind === 'ok' && state.teams.length > 0 && (
        <ul ref={listRef} className="ss-tm-list">
          {state.teams.map((t) => (
            <li key={t.id} className="ss-tm-row">
              <span className="ss-tm-name">{t.name}</span>
              {/* 🔴 **시각을 적지 않는다** — 후보는 팀이고 경기 공고가
                  아니라서 시각이 없다. 시각은 아래에서 **우리가 고른다.** */}
              <span className="ss-tm-where">
                {t.region} · {t.size} : {t.size}
              </span>
              {/* 🔴 **왜 이 팀이 나왔는지 적는다**(사용자 결정). 근거 없이
                  「비슷합니다」만 말하면 목록을 믿을 근거가 없다. */}
              <span className="ss-tm-why">
                {t.why.map((w) => (
                  <span key={w} className="ss-tm-tag">
                    {w}
                  </span>
                ))}
              </span>
              <button
                type="button"
                className="ss-tm-apply"
                /* 다른 곳에 신청해 둔 동안에는 못 누른다 — 위 `apply` 주석.
                   주장인 팀을 아직 못 읽었으면 보낼 곳이 없어 못 누른다. */
                disabled={waiting !== null || !teamId}
                onClick={() => {
                  /* 🔴 **바로 안 보낸다** — 시각·구장을 먼저 고른다(후보에는
                     그 둘이 없다). 조건이 없으면 고를 것이 없으므로 그렇게 적는다. */
                  setError(null)
                  setPicking(picking === t.id ? null : t.id)
                  setPickedAt(proposals[0] ?? null)
                  setPickedPlace('')
                  /* 🔴 **열자마자 쓸 수 있는 시각을 채운다**(사용자 지적,
                     2026-09-18). 비워 두었더니 달력에서 **날짜만** 고르고
                     시각이 `00:00` 으로 남아 「지난 시각입니다」에 걸렸다 —
                     사람이 잘못한 것이 아니라 빈 칸이 그렇게 만든 것이다.
                     10분 뒤면 신청·수락·대기 화면을 보기에 충분하고, 시연에서
                     경기 끝내기·리뷰까지 가는 데도 알맞다. */
                  setCustomAt(toInput(new Date(Date.now() + 10 * 60 * 1000)))
                }}
              >
                {sentTo === t.id
                  ? '상대 수락 대기 중'
                  : waiting === t.id
                    ? '신청하는 중…'
                    : picking === t.id
                      ? '접기'
                      : '경기 신청'}
              </button>

              {/* 🔴 **시각·구장은 우리가 제안한다.** 지어내지 않는다 — 시각은
                  서버에 올린 우리 조건에서, 구장은 경기장 목록에서 온다. */}
              {picking === t.id && (
                <div className="ss-tm-pick">
                  <>
                      {/* 🔴 **제안이 없어도 신청은 할 수 있어야 한다**(2026-09-18).
                          전에는 여기서 「조건에 시간대가 없습니다」로 끝나
                          **판이 통째로 닫혔다** — 그런데 시간 조건을 비우는
                          것은 추천 후보 필터를 푸는 정상적인 길이라(프로필의
                          「시간 조건 지우기」), 그 상태에서 경기를 못 걸면
                          앞뒤가 안 맞는다. 아래 「직접 고르기」로 잡으면 된다. */}
                      {/* 🔴 **직접 고른 값이 있으면 제안을 안 그린다**(사용자
                          지적, 2026-09-18: 「내가 직접 고르면 이거는 필요없는거
                          아님?」). 직접 고른 쪽이 이기는데 둘이 같이 떠 있으면
                          **어느 것이 쓰이는지 알 수 없다.** 칸을 비우면 제안이
                          다시 나온다 — 제안을 없앤 것이 아니다. */}
                      {customAt ? null : proposals.length === 0 ? (
                        <p className="ss-tm-note">
                          경기 조건에 시간대가 없습니다 — 아래에서 직접 고르세요.
                        </p>
                      ) : (
                        <label className="ss-tm-pick-row">
                          <span>언제</span>
                          <select
                            value={pickedAt?.label ?? ''}
                            onChange={(e) =>
                              setPickedAt(proposals.find((x) => x.label === e.target.value) ?? null)
                            }
                          >
                            {proposals.map((x) => (
                              <option key={x.label} value={x.label}>
                                {x.label}
                              </option>
                            ))}
                          </select>
                        </label>
                      )}
                      {/* 🔴 **직접 고르는 길**(사용자 요청, 2026-09-18 — 시연
                          촬영). 제안은 「다음에 오는 그 요일」이라 조건이
                          토요일뿐이면 다음 토요일이다 — 몇 분 뒤로 잡을 수가
                          없어서 대기 화면 → 경기 끝내기 → 리뷰를 한자리에서
                          못 보여 준다. 적으면 이 값이 제안을 이긴다. */}
                      <label className="ss-tm-pick-row">
                        <span>직접 고르기</span>
                        <input
                          type="datetime-local"
                          min={minAt}
                          value={customAt}
                          onChange={(e) => setCustomAt(e.target.value)}
                        />
                      </label>
                      {customIsPast && (
                        <p className="ss-tm-note" role="alert">
                          지난 시각입니다 — 앞으로 올 시각을 고르세요.
                        </p>
                      )}

                      <label className="ss-tm-pick-row">
                        <span>어디서</span>
                        <select
                          value={pickedPlace}
                          onChange={(e) => setPickedPlace(e.target.value)}
                        >
                          <option value="">구장을 고르세요</option>
                          {venues.map((v) => (
                            <option key={v.id} value={v.name}>
                              {v.name} · {v.region}
                            </option>
                          ))}
                        </select>
                      </label>
                      <button
                        type="button"
                        className="ss-tm-apply"
                        disabled={
                          waiting !== null ||
                          !pickedPlace ||
                          customIsPast ||
                          (!customDate && !pickedAt)
                        }
                        onClick={() => void apply(t)}
                      >
                        이 시각으로 신청
                      </button>
                  </>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {error && (
        <p className="ss-tm-foot" role="alert">
          {error}
        </p>
      )}

      {/* 🔴 **「데모입니다」를 걷었다**(2026-09-16) — 신청은 이제 진짜로 나간다
          (계약 3-15절). 대신 **명단 자체는 아직 붙박이**라는 것을 밝힌다:
          「비슷한 팀」을 고르는 경로가 없어서다(`lib/teamMatch.ts` 첫머리).
          어디까지가 진짜인지 안 적으면 다음 사람이 둘 다 진짜로 여긴다. */}
      {!asking && !error && (
        <p className="ss-tm-foot">
          신청은 상대 팀장에게 갑니다 — 수락해야 경기가 잡힙니다.
        </p>
      )}
    </section>
  )
}
