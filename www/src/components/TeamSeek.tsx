'use client'

import { useEffect, useState } from 'react'
import type { OpenMatch } from '@/server/backend'
import { SPORTS, SPORT_CODE } from '@/lib/sports'
import MatchPrefsForm from '@/components/MatchPrefs'
import { loadPrefs, savePrefs, type MatchPrefs } from '@/lib/matchPrefs'

/**
 * 「팀원」 판 — **아직 사람을 못 채운 팀들의 명단**(사용자 요청, 2026-09-08).
 *
 * 알약 「팀원」을 누르면 **스쿼드 판이 물러나고 그 자리에** 이 판이 선다.
 * 나란히 세우지 않는 이유: 스쿼드 판은 *내 팀을 짜는* 자리이고 이 판은
 * *남의 팀에 들어가는* 자리라, 한 화면에 두면 어느 쪽을 하고 있는지가
 * 흐려진다. 판 오른쪽의 추천 · 지인 · 챗봇이 "한 번에 하나"인 것과 같은
 * 판단이다.
 *
 * 🔴 **목록이 붙박이가 아니다.** 계약 3-4절의 `GET /matches`(경기 탐색)를
 * 그대로 부른다 — 팀 id 를 몰라도 되는 유일한 경로라, 아직 팀이 없는 사람이
 * 갈 수 있는 곳이 여기뿐이다. 지인 판 · AI 추천 판이 아직 붙박이인 것과
 * 갈리는 점이다(그쪽은 계약에 자리가 없다).
 *
 * 🔴 **거르기는 서버가 한다**(2026-09-10, 미결 `jin` 15번). 종목 · 지역
 * 둘 다 `GET /matches` 가 받는 값이라 화면에서 걸러 내지 않는다 — 화면에서
 * 걸러 봐야 **첫 페이지 안에서만** 걸러져서, 20건 뒤에 있는 것은 영영 안 나온다.
 *
 * ⚠️ **포지션은 예외로 화면에서 거른다** — 서버가 아직 안 받는다(계약이 그렇게
 * 정했다: `needs` 가 오니 화면에서 하라고). 그래서 아직 안 붙였다.
 *
 * 🔴 **모집 글 한 건이 곧 팀 한 줄이다.** 계약이 주는 것은 경기이고 "인원이
 * 덜 찬 팀" 이라는 목록은 따로 없다 — 사람을 못 채웠으니 모집 글을 올린
 * 것이라 그 둘이 같다. 같은 팀이 두 경기를 올렸으면 두 줄로 나온다: 지원하는
 * 쪽이 고르는 것은 팀이 아니라 **그 경기**라 합치지 않는다.
 */

/** 언제 하는 경기인가 — 목록에서 훑으므로 요일까지 적는다. */
function whenText(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const day = ['일', '월', '화', '수', '목', '금', '토'][d.getDay()]
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getMonth() + 1}.${p(d.getDate())} (${day}) ${p(d.getHours())}:${p(d.getMinutes())}`
}

/** 몇 자리가 비었나 — 「인원을 못 채웠다」가 이 판의 제목이라 합을 앞세운다. */
function openSeats(m: OpenMatch): number {
  return m.needs.reduce((sum, n) => sum + n.head_count, 0)
}

type State =
  | { kind: 'loading' }
  | { kind: 'ok'; items: OpenMatch[]; total: number }
  | { kind: 'error'; message: string }

export default function TeamSeek({
  closing,
  onClose,
  sportCode = null,
}: {
  /** 닫히는 중 — 사라지는 동안에도 DOM 에 남아야 애니메이션이 보인다. */
  closing: boolean
  onClose: () => void
  /** 「내 자리」 후보를 받아 올 종목 — 조건 판이 쓴다. */
  sportCode?: string | null
}) {
  const [state, setState] = useState<State>({ kind: 'loading' })
  /**
   * 고른 종목. `null` 이 **전체**다.
   *
   * 🔴 **「전체」를 빈 문자열로 두지 않는다.** `sport_code=` 는 "전체"가 아니라
   * **없는 종목**이라 422 `UNKNOWN_SPORT` 로 튕긴다(계약 3-4절) — 오타와
   * "그 종목 경기가 없다"가 같아 보이면 안 된다는 판단이다. 전체는 **파라미터
   * 자체를 빼서** 부른다.
   */
  const [sport, setSport] = useState<string | null>(null)
  /**
   * 적어 넣은 지역. 🔴 **종목과 처리가 다르다** — 지역은 자유 문자열이라
   * 안 걸리면 그냥 빈 목록이고 422 가 아니다.
   */
  const [region, setRegion] = useState('')
  /** 실제로 보낸 지역 — 글자마다 부르지 않으려고 제출한 값만 따로 둔다. */
  const [asked, setAsked] = useState('')

  /**
   * 정해 둔 **내 조건**(팀장 쪽과 따로 둔다 — 같은 사람이 둘 다일 수 있다).
   *
   * 🔴 **거르기 줄을 대신하지 않는다.** 조건은 「늘 이런 경기를 찾는다」이고
   * 거르기는 「지금 이 목록에서 더 좁힌다」라 층이 다르다 — 조건이 거르기의
   * **첫 값을 채우고**, 그 뒤로는 거르기가 제 일을 한다(사용자와 확인).
   *
   * 🔴 그릴 때 저장소를 읽지 않는다(하이드레이션) — 붙은 뒤에 읽는다.
   */
  const [prefs, setPrefs] = useState<MatchPrefs | null>(null)
  const [asking, setAsking] = useState(false)
  /**
   * 🔴 **조건을 읽기 전에는 목록을 받지 않는다.** `asking` 은 처음에 `false`
   * 라, 이 표시가 없으면 조건을 읽는 effect 보다 목록 effect 가 먼저 돌아
   * **묻기도 전에** 한 번 받아 온다(시험이 잡았다).
   */
  const [ready, setReady] = useState(false)
  useEffect(() => {
    const saved = loadPrefs('me')
    setPrefs(saved)
    setAsking(saved === null)
    // 조건의 첫 지역을 거르기의 첫 값으로 — 없으면 그냥 전체다.
    if (saved?.regions[0]) {
      setRegion(saved.regions[0])
      setAsked(saved.regions[0])
    }
    setReady(true)
  }, [])

  /**
   * 🔴 **판이 열릴 때, 그리고 거르는 값이 바뀔 때만 받는다.** 그릴 때 부르면
   * 서버가 그린 첫 화면과 갈려 하이드레이션이 깨진다(공개 목록 · 카드
   * 꾸미기에서 데인 자리와 같다).
   */
  useEffect(() => {
    // 조건을 아직 안 읽었거나 묻는 중이면 안 받는다 — 정하고 나서 받는다.
    if (!ready || asking) return
    let alive = true
    /* 🔴 **여기서 「불러오는 중」으로 되돌리지 않는다.** effect 안의 동기
       setState 는 렌더를 한 번 더 부른다 — 되돌리는 일은 **값을 바꾼 손짓**
       (알약 · 찾기)이 하고, 이 effect 는 받아 온 뒤에만 상태를 만진다. */
    void (async () => {
      try {
        /* 🔴 **빈 값을 실어 보내지 않는다.** `URLSearchParams` 에 넣는 순간
           `sport_code=` 가 되어 422 다 — 있는 것만 넣는다. */
        const q = new URLSearchParams({ size: '20' })
        if (sport) q.set('sport_code', sport)
        if (asked) q.set('region', asked)
        const res = await fetch(`/api/matches?${q}`)
        const body: unknown = await res.json().catch(() => null)
        if (!alive) return
        if (!res.ok) {
          const msg =
            typeof body === 'object' && body !== null && 'error' in body
              ? ((body as { error?: { message?: string } }).error?.message ?? null)
              : null
          setState({ kind: 'error', message: msg ?? '목록을 가져오지 못했습니다.' })
          return
        }
        const page = body as { items?: OpenMatch[]; total?: number }
        setState({ kind: 'ok', items: page.items ?? [], total: page.total ?? 0 })
      } catch {
        if (alive) setState({ kind: 'error', message: '목록을 가져오지 못했습니다.' })
      }
    })()
    return () => {
      alive = false
    }
  }, [sport, asked, asking, ready])

  return (
    <section
      className="ss-teams"
      data-closing={closing ? 'true' : undefined}
      aria-label="사람을 찾는 팀"
      // 🔴 backdrop-filter 는 **인라인으로만** 준다 — globals.css 에 두면
      // Lightning CSS 를 지나며 떨어져 나간 전례가 있다(추천 판 · 시작 단추).
      style={{
        backdropFilter: 'blur(var(--ss-glass-blur)) saturate(var(--ss-glass-saturate))',
        WebkitBackdropFilter: 'blur(var(--ss-glass-blur)) saturate(var(--ss-glass-saturate))',
      }}
    >
      <header className="ss-teams-head">
        <h2>사람을 찾는 팀</h2>
        <div className="ss-tm-head-right">
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
          <button type="button" className="ss-teams-close" onClick={onClose} aria-label="닫기">
            <span className="material-symbols-outlined" aria-hidden="true">
              close
            </span>
          </button>
        </div>
      </header>

      {/* 🔴 조건이 먼저다 — 없으면 거르기 줄도 목록도 안 그린다. */}
      {asking && (
        <MatchPrefsForm
          kind="me"
          sportCode={sportCode}
          value={prefs}
          onDone={(next) => {
            savePrefs('me', next)
            setPrefs(next)
            setAsking(false)
            if (next.regions[0]) {
              setRegion(next.regions[0])
              setAsked(next.regions[0])
            }
          }}
          onCancel={prefs ? () => setAsking(false) : undefined}
        />
      )}

      {/* 🔴 **거르는 줄은 늘 그린다** — 결과 안쪽에 두면 「없습니다」가 떴을 때
          거르기가 같이 사라져서, 잘못 고른 것을 되돌릴 방법이 없어진다. */}
      <form
        className="ss-teams-filter"
        hidden={asking}
        onSubmit={(e) => {
          e.preventDefault()
          setAsked(region.trim())
          setState({ kind: 'loading' })
        }}
      >
        <div className="ss-teams-sports" role="group" aria-label="종목">
          <button
            type="button"
            className="ss-teams-pill"
            data-on={sport === null ? 'true' : undefined}
            aria-pressed={sport === null}
            onClick={() => {
              setSport(null)
              setState({ kind: 'loading' })
            }}
          >
            전체
          </button>
          {SPORTS.map((s) => (
            <button
              key={s.key}
              type="button"
              className="ss-teams-pill"
              data-on={sport === SPORT_CODE[s.key] ? 'true' : undefined}
              aria-pressed={sport === SPORT_CODE[s.key]}
              onClick={() => {
                setSport(SPORT_CODE[s.key])
                setState({ kind: 'loading' })
              }}
            >
              {s.label}
            </button>
          ))}
        </div>
        <label className="ss-teams-region">
          <span className="sr-only">지역</span>
          <input
            type="search"
            value={region}
            placeholder="지역 (예: 서울 강남구)"
            onChange={(e) => setRegion(e.target.value)}
          />
        </label>
        <button type="submit" className="ss-teams-pill">
          찾기
        </button>
      </form>

      {!asking && state.kind === 'loading' && (
        <p className="ss-teams-note">불러오는 중입니다…</p>
      )}

      {/* 🔴 실패를 빈 목록으로 그리지 않는다 — "못 가져왔다"와 "그런 팀이
          없다"가 같아 보이면 없는 것을 계속 기다리게 된다. */}
      {!asking && state.kind === 'error' && (
        <p className="ss-teams-note" data-error="true" role="alert">
          {state.message}
        </p>
      )}

      {!asking && state.kind === 'ok' && state.items.length === 0 && (
        /* 거르고 있으면 그렇게 말한다 — 「없습니다」만 뜨면 사이트가 빈 것으로
           읽히고, 거르기를 풀면 나온다는 것을 알 수 없다. */
        <p className="ss-teams-note">
          {sport || asked
            ? '그 조건에 맞는 팀이 없습니다.'
            : '지금은 사람을 찾는 팀이 없습니다.'}
        </p>
      )}

      {!asking && state.kind === 'ok' && state.items.length > 0 && (
        <>
          <p className="ss-teams-count">{state.total}팀이 자리를 채우고 있습니다</p>
          <ul className="ss-teams-list">
            {state.items.map((m) => (
              <li key={m.id} className="ss-teams-row">
                <span className="ss-teams-name">{m.team_name}</span>
                <span className="ss-teams-where">
                  {m.region} · {m.place}
                </span>
                <span className="ss-teams-when">{whenText(m.played_at)}</span>
                {/* 어느 자리가 비었는지가 이 목록을 고르는 기준이다 — 자리
                    이름과 인원을 그대로 적는다(계약이 이름까지 준다). */}
                <span className="ss-teams-needs">
                  {m.needs.map((n) => (
                    <span key={n.position_code} className="ss-teams-need">
                      {n.position_label} {n.head_count}
                    </span>
                  ))}
                </span>
                <span className="ss-teams-seats">{openSeats(m)}자리</span>
              </li>
            ))}
          </ul>
          {/* ⚠️ 지원(신청)은 아직 없다. 계약에는 `POST /matches/{id}/applications`
              가 있지만 이번에 요청받은 것은 **명단까지**다 — 없는 단추를 그려
              두면 눌러 보고 아무 일도 안 일어난다. */}
          <p className="ss-teams-foot">고르는 것은 다음 회차입니다 — 지금은 명단까지입니다.</p>
        </>
      )}
    </section>
  )
}
