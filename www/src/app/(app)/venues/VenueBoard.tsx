'use client'

import { useMemo, useState } from 'react'
import { SPORT_LABEL, type SportCode } from '@/lib/market'
import { HOURS, loadPrefs, type MatchPrefs } from '@/lib/matchPrefs'
import {
  EMPTY_QUERY,
  countOpen,
  filterVenues,
  hasQuery,
  type DayKind,
  type TimeBand,
  type VenueQuery,
} from '@/lib/venueFilter'
import type { Venue } from '@/lib/venues'

/**
 * 경기장 예약 판 — **레슨 · 상점 판과 같은 두 색**으로 짠다(사용자 요청,
 * 2026-09-10 · 참고 디자인은 호텔 예약 화면).
 *
 * 🔴 **판 안의 색은 두 개뿐이다** — 짙은 초록과 종이색. 0.8 회차가 레슨 ·
 * 상점에서 정한 규칙을 그대로 쓴다: 자리마다 **바탕(`--ss-vb-ground`)과
 * 글자(`--ss-vb-ink`)** 두 값만 갈아 끼우면 글 · 테두리 · 알약이 한꺼번에
 * 따라온다. 위 띠는 그 둘을 맞바꿔 종이 바탕이 된다(사용자 요청).
 *
 * 🔴 **앱 민트(`#70ed88`)는 이 판에서 안 쓴다.** 검은 화면에서 뜨라고 고른
 * 색이라 짙은 초록 위에서 저 혼자 형광으로 튄다 — 「접수중」 배지도 종이색
 * 계열이다(전에는 민트였다). 판 **바깥**의 헤더 워드마크는 이 규칙 밖이라
 * 앱 색 그대로다.
 *
 * 🔴 **우리는 예약을 중개하지 않는다.** 「예약하러 가기」는 서울시 공식
 * 예약 사이트로 나가는 **바깥 링크**이고 결제 · 접수는 전부 그쪽이다
 * (미결 7번 결정, 2026-09-04). 화면이 그 사실을 계속 말한다.
 *
 * 🔴 **거르는 규칙은 여기 없다** — `lib/venueFilter.ts` 에 있다. 요일 · 때 ·
 * 시각이 서로 얽혀서(같은 시간대 하나가 다 만족해야 한다) 화면 안에 흩어
 * 두면 검사할 수가 없다.
 */

const DAY_LABEL: Record<DayKind, string> = { weekday: '평일', weekend: '주말·공휴일' }

/** 🔴 이름이 아니라 `hours` 의 숫자로 나눈 때다 — 자세한 이유는 `venueFilter.ts`. */
const BAND_LABEL: Record<TimeBand, string> = {
  early: '조기 (~09시)',
  day: '낮',
  night: '야간 (17시~)',
}

export default function VenueBoard({ venues }: { venues: Venue[] }) {
  const [q, setQ] = useState<VenueQuery>(EMPTY_QUERY)
  /** 세세한 조건은 접어 둔다 — 늘 펼쳐 두면 목록이 화면 밖으로 밀린다. */
  const [more, setMore] = useState(false)
  /** 「내 조건」을 켤 때 무엇을 기준으로 삼았는지, 혹은 왜 못 켰는지. */
  const [prefsNote, setPrefsNote] = useState<string | null>(null)

  /** 데이터에 실제로 있는 구만 고를 수 있게 한다 — 없는 것을 고르면 늘 0건이다. */
  const regions = useMemo(
    () => [...new Set(venues.map((v) => v.region))].sort((a, b) => a.localeCompare(b, 'ko')),
    [venues],
  )

  const shown = useMemo(() => filterVenues(venues, q), [venues, q])

  const set = (patch: Partial<VenueQuery>) => setQ((cur) => ({ ...cur, ...patch }))

  /** 켜져 있으면 빼고 없으면 넣는다 — 알약 여럿을 같이 고르는 자리 전용. */
  function toggle<T>(list: T[], value: T): T[] {
    return list.includes(value) ? list.filter((x) => x !== value) : [...list, value]
  }

  /**
   * 🔴 **정해 둔 경기 조건을 여기서 다시 묻지 않는다.** 팀 매칭에서 이미
   * 받아 둔 것(`lib/matchPrefs.ts`)을 그대로 조건으로 건다 — 같은 것을 두 번
   * 물으면 두 값이 어긋난다.
   *
   * 🔴 **누를 때 읽는다.** 그리는 동안 읽으면 서버에는 없는 값이라(브라우저
   * 저장소다) 서버가 그린 것과 달라져 물갈이(hydration)에서 어긋난다.
   */
  function togglePrefs() {
    if (q.prefs) {
      set({ prefs: null })
      setPrefsNote(null)
      return
    }
    const team = loadPrefs('team')
    const mine = loadPrefs('me')
    const picked: MatchPrefs | null = team ?? mine
    if (!picked) {
      setPrefsNote('아직 정해 둔 경기 조건이 없습니다 — 홈 스쿼드판의 「팀 매칭」에서 정합니다.')
      return
    }
    set({ prefs: picked })
    setPrefsNote(team ? '팀 조건으로 걸렀습니다.' : '내 조건으로 걸렀습니다.')
  }

  return (
    <div className="ss-vb">
      <header className="ss-vb-top">
        <div className="ss-vb-sign">
          <h1>VENUES</h1>
          <p>경기장 예약</p>
        </div>

        {/* 🔴 거르는 줄은 **늘 그린다** — 결과 안쪽에 두면 「없습니다」가 떴을 때
            거르기가 같이 사라져 되돌릴 길이 없어진다(팀원 판에서 정한 규칙). */}
        <div className="ss-vb-filters">
          <label className="ss-vb-search">
            <span className="sr-only">시설 이름</span>
            <input
              type="search"
              value={q.text}
              placeholder="시설 이름"
              autoComplete="off"
              onChange={(e) => set({ text: e.target.value })}
            />
          </label>

          <div className="ss-vb-sports" role="group" aria-label="종목">
            <button
              type="button"
              className="ss-vb-pill"
              data-on={q.sport === null ? 'true' : undefined}
              aria-pressed={q.sport === null}
              onClick={() => set({ sport: null })}
            >
              전체
            </button>
            {(Object.keys(SPORT_LABEL) as SportCode[]).map((code) => (
              <button
                key={code}
                type="button"
                className="ss-vb-pill"
                data-on={q.sport === code ? 'true' : undefined}
                aria-pressed={q.sport === code}
                onClick={() => set({ sport: code })}
              >
                {SPORT_LABEL[code]}
              </button>
            ))}
          </div>

          <button
            type="button"
            className="ss-vb-pill"
            data-on={q.openOnly ? 'true' : undefined}
            aria-pressed={q.openOnly}
            onClick={() => set({ openOnly: !q.openOnly })}
          >
            접수중만
          </button>

          <button
            type="button"
            className="ss-vb-pill"
            data-on={more ? 'true' : undefined}
            aria-expanded={more}
            onClick={() => setMore((now) => !now)}
          >
            자세히
          </button>
        </div>
      </header>

      {more && (
        <div className="ss-vb-more">
          <div className="ss-vb-field" role="group" aria-label="지역">
            <p className="ss-vb-legend">지역</p>
            <div className="ss-vb-chips">
              {regions.map((r) => (
                <button
                  key={r}
                  type="button"
                  className="ss-vb-pill"
                  data-on={q.regions.includes(r) ? 'true' : undefined}
                  aria-pressed={q.regions.includes(r)}
                  onClick={() => set({ regions: toggle(q.regions, r) })}
                >
                  {r.replace('서울 ', '')}
                </button>
              ))}
            </div>
          </div>

          <div className="ss-vb-field" role="group" aria-label="요일">
            <p className="ss-vb-legend">요일</p>
            <div className="ss-vb-chips">
              {(Object.keys(DAY_LABEL) as DayKind[]).map((d) => (
                <button
                  key={d}
                  type="button"
                  className="ss-vb-pill"
                  data-on={q.days.includes(d) ? 'true' : undefined}
                  aria-pressed={q.days.includes(d)}
                  onClick={() => set({ days: toggle(q.days, d) })}
                >
                  {DAY_LABEL[d]}
                </button>
              ))}
            </div>
            {/* ⚠️ 원본이 요일을 안 나누고 파는 시설이 3분의 1이다 — 감추면 거짓말이 된다. */}
            <p className="ss-vb-hint">요일이 안 적힌 시간대는 아무 요일에나 나옵니다.</p>
          </div>

          <div className="ss-vb-field" role="group" aria-label="때">
            <p className="ss-vb-legend">때</p>
            <div className="ss-vb-chips">
              {(Object.keys(BAND_LABEL) as TimeBand[]).map((b) => (
                <button
                  key={b}
                  type="button"
                  className="ss-vb-pill"
                  data-on={q.bands.includes(b) ? 'true' : undefined}
                  aria-pressed={q.bands.includes(b)}
                  onClick={() => set({ bands: toggle(q.bands, b) })}
                >
                  {BAND_LABEL[b]}
                </button>
              ))}
            </div>
          </div>

          <div className="ss-vb-field">
            <label className="ss-vb-legend" htmlFor="ss-vb-at">
              이 시각에 열린 곳
            </label>
            <select
              id="ss-vb-at"
              className="ss-vb-at"
              value={q.at ?? ''}
              onChange={(e) => set({ at: e.target.value || null })}
            >
              <option value="">아무 때나</option>
              {HOURS.map((h) => (
                <option key={h} value={h}>
                  {h}
                </option>
              ))}
            </select>
          </div>

          <div className="ss-vb-field">
            <p className="ss-vb-legend">내 경기 조건</p>
            <button
              type="button"
              className="ss-vb-pill"
              data-on={q.prefs ? 'true' : undefined}
              aria-pressed={q.prefs !== null}
              onClick={togglePrefs}
            >
              정해 둔 조건에 맞는 곳만
            </button>
            {prefsNote && <p className="ss-vb-hint">{prefsNote}</p>}
          </div>

          {hasQuery(q) && (
            <button
              type="button"
              className="ss-vb-clear"
              onClick={() => {
                setQ(EMPTY_QUERY)
                setPrefsNote(null)
              }}
            >
              조건 비우기
            </button>
          )}
        </div>
      )}

      {/* ⚠️ **실시간이 아니다.** 지금까지 이 사실이 주석에만 있고 화면에 없었다 —
          「접수중」을 보고 갔는데 마감이면 우리 화면이 거짓말을 한 것이 된다.
          순서까지 여기서 밝힌다 — 안 적으면 「지금 비어 있는 순」으로 읽힌다. */}
      <p className="ss-vb-note">
        {shown.length}곳 · 접수중인 시간대가 많은 곳부터 · 접수 현황은{' '}
        <b>내려받은 시점 기준</b>이라 실시간이 아닙니다. 실제 예약·결제는 서울시
        공공서비스예약에서 이루어집니다.
      </p>

      {shown.length === 0 ? (
        <p className="ss-vb-empty">그 조건에 맞는 구장이 없습니다.</p>
      ) : (
        <ul className="ss-vb-list">
          {shown.map((v) => {
            const open = v.slots.filter((s) => s.open)
            return (
              <li key={v.id} className="ss-vb-card">
                {/* 🔴 **사진 자리다.** 원본 데이터에 사진 컬럼이 없어서 지금은
                    종목을 얹은 판이다 — 사진이 오면 이 상자에 `<Image>` 만
                    넣으면 참고 디자인 모양이 된다(상점이 같은 방식이다). */}
                <div className="ss-vb-thumb" aria-hidden="true">
                  <span>{v.sports.map((s) => SPORT_LABEL[s]).join(' · ')}</span>
                </div>

                <div className="ss-vb-body">
                  <b className="ss-vb-name">{v.name}</b>
                  <span className="ss-vb-region-text">
                    {v.region}
                    {/* 순서의 근거를 카드에도 적는다 — 왜 위에 있는지 보여야 한다. */}
                    {countOpen(v) > 0 && ` · 접수중 ${countOpen(v)}`}
                  </span>
                  <p className="ss-vb-tagline">{v.tagline}</p>

                  <ul className="ss-vb-slots">
                    {v.slots.map((s) => (
                      <li key={`${s.label}-${s.hours}`} className="ss-vb-slot">
                        <span className="ss-vb-badge" data-open={s.open ? 'true' : undefined}>
                          {s.open ? '접수중' : '마감'}
                        </span>
                        <span className="ss-vb-slot-time">
                          {s.label} · {s.hours}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>

                {/* 🔴 **바깥으로 나간다.** 새 탭으로 열고, 그 사실을 낭독기에도
                    알린다 — 우리가 결제하지 않는다는 것이 이 화면의 규칙이다.
                    열린 시간대가 하나도 없으면 단추 대신 그렇게 적는다. */}
                {open.length > 0 ? (
                  <a
                    className="ss-vb-book"
                    href={open[0].reserveUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    예약하러 가기
                    <span className="sr-only">(새 탭에서 서울시 예약 사이트로 열립니다)</span>
                    <span aria-hidden="true">→</span>
                  </a>
                ) : (
                  <p className="ss-vb-closed">지금은 접수중인 시간대가 없습니다</p>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
