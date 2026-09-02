'use client'

import { useState } from 'react'
import { TransitionLink } from '@/lib/pageTransition'
import {
  LEVEL_LABEL,
  SPORT_LABEL,
  won,
  type Coach,
  type Level,
  type SportCode,
} from '@/lib/market'

/**
 * 코치 목록과 거름망.
 *
 * 🔴 종목 알약은 **영상 분석과 같은 모양**을 쓴다(`.ss-shot-sport`). 사용자가
 * 이미 한 번 배운 조작이라 여기서 새로 배울 것이 없어야 한다 — 같은 뜻의 것에
 * 다른 모양을 주지 않는다.
 *
 * 거름망을 클라이언트에 둔 이유: 지금은 mock 이라 목록이 몇 개뿐이고, 서버로
 * 다시 물으면 화면이 한 번 비었다 돌아온다. API 가 붙으면 이 컴포넌트가 쿼리
 * 파라미터를 바꾸는 쪽으로 옮겨 가면 된다.
 */
export default function CoachList({ coaches }: { coaches: Coach[] }) {
  const [sport, setSport] = useState<SportCode | null>(null)
  const [level, setLevel] = useState<Level | null>(null)

  const shown = coaches.filter(
    (c) => (!sport || c.sport === sport) && (!level || c.levels.includes(level)),
  )

  return (
    <>
      <div className="ss-market-filters">
        <div className="ss-shot-sports" role="group" aria-label="종목">
          {(Object.keys(SPORT_LABEL) as SportCode[]).map((code) => (
            <button
              key={code}
              type="button"
              className="ss-shot-sport"
              aria-pressed={sport === code}
              // 같은 것을 다시 누르면 풀린다 — 종목을 안 고른 상태가 "전체" 다.
              onClick={() => setSport(sport === code ? null : code)}
            >
              {SPORT_LABEL[code]}
            </button>
          ))}
        </div>

        <div className="ss-shot-sports" role="group" aria-label="수준">
          {(Object.keys(LEVEL_LABEL) as Level[]).map((code) => (
            <button
              key={code}
              type="button"
              className="ss-shot-sport"
              aria-pressed={level === code}
              onClick={() => setLevel(level === code ? null : code)}
            >
              {LEVEL_LABEL[code]}
            </button>
          ))}
        </div>
      </div>

      {shown.length === 0 ? (
        <p className="ss-market-empty">조건에 맞는 코치가 아직 없습니다.</p>
      ) : (
        <ul className="ss-coach-list">
          {shown.map((c) => (
            <li key={c.id}>
              <TransitionLink href={`/market/coaches/${c.id}`} className="ss-coach-card">
                <span className="ss-coach-card-head">
                  <b>{c.name}</b>
                  <span>
                    {SPORT_LABEL[c.sport]} · {c.region}
                  </span>
                </span>

                <span className="ss-coach-card-tagline">{c.tagline}</span>

                {/* 🔴 간판. 다른 곳은 코치가 자기 실력을 자기소개로 쓰지만
                    우리는 **같은 잣대로 잰 것**을 보여준다. 수치는 안 그린다
                    (부록 D.5) — 받은 호칭뿐이다. */}
                <span className="ss-coach-card-analysis">
                  <em>우리 분석을 받은 코치</em>
                  <span className="ss-coach-titles">
                    {c.titles.map((t) => (
                      <b key={t}>{t}</b>
                    ))}
                  </span>
                </span>

                <span className="ss-coach-card-foot">
                  회당 {won(c.pricePerSession)}
                  <i>후기 {c.reviews.length}</i>
                </span>
              </TransitionLink>
            </li>
          ))}
        </ul>
      )}
    </>
  )
}
