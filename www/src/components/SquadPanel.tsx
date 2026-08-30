'use client'

import { useState } from 'react'
import type { PublicPlayerCard } from '@/server/backend'
import PlayerCardView from '@/components/PlayerCardView'
import GlassPanel from '@/components/ui/GlassPanel'
import BrandMark from '@/components/ui/BrandMark'

/**
 * 홈 첫 화면의 스쿼드 판 — 판 하나 위에 선수 카드를 **포지션 자리대로**
 * 앉힌다(참고: 축구 게임의 스쿼드 화면). 한 줄로 늘어놓지 않는 이유가
 * 그것이다 — 누가 어느 자리인지가 배치로 읽혀야 한다.
 *
 * 풋살 5인, 1-2-1 포메이션: GK · DF 하나 · MF 둘 · FW 하나.
 * 내 카드는 맨 위(FW)에 놓는다 — 가운데 열의 맨 앞이라 눈이 먼저 간다.
 * 나머지 넷은 빈 카드 — 같은 틀 · 같은 머리글(SUPERSUB · PLAYER CARD)에
 * 가운데 + 만 있다. 눌러 보기 전에 무슨 자리인지 알 수 있어야 해서다.
 *
 * ⚠️ **아직 서버에 저장하지 않는다.** 계약(api-contract.md)에 스쿼드를
 * 만들거나 사람을 넣는 엔드포인트가 없다 — `GET /me` 의 `teams` 는 이미
 * 소속된 팀을 읽기만 하는 값이다. 지금은 이 컴포넌트의 상태로만 들고
 * 있고 새로고침하면 사라진다. 백엔드가 생기면 setMates 를 부르는 자리
 * 둘(넣기 · 빼기)을 API 호출로 바꾸면 된다. 브라우저 저장도 일부러 안
 * 넣었다 — 서버가 붙는 순간 상태가 두 곳에 생겨 어느 쪽이 진짜인지
 * 헷갈린다.
 */

/** 판 위의 자리. `area` 는 globals.css 의 grid-template-areas 이름이다. */
type Slot = { area: string; label: string; mine?: boolean }

const SLOTS: Slot[] = [
  { area: 'fw', label: 'FW', mine: true },
  { area: 'ml', label: 'MF' },
  { area: 'mr', label: 'MF' },
  { area: 'df', label: 'DF' },
  { area: 'gk', label: 'GK' },
]

export default function SquadPanel({ card }: { card?: PublicPlayerCard | null }) {
  const [mates, setMates] = useState<Record<string, string | null>>({})
  const [editing, setEditing] = useState<string | null>(null)
  const [draft, setDraft] = useState('')

  function commit(area: string) {
    const name = draft.trim()
    if (name) setMates((prev) => ({ ...prev, [area]: name }))
    setEditing(null)
    setDraft('')
  }

  return (
    <GlassPanel className="ss-squad">
      <header className="ss-squad-head">
        <h2>MY SQUAD</h2>
        <p>풋살 5인</p>
      </header>

      <div className="ss-squad-board">
        {/* 경기장 선 — 장식이라 스크린리더에서 숨긴다. preserveAspectRatio
            를 none 으로 두어 판이 어떤 비율이 되든 선이 판을 꽉 채운다
            (원은 그만큼 타원이 되지만, 배경 장식이라 그편이 낫다 —
            비율을 지키면 위아래에 선 없는 빈 띠가 생긴다). */}
        <svg
          className="ss-squad-pitch"
          viewBox="0 0 100 140"
          preserveAspectRatio="none"
          aria-hidden="true"
          focusable="false"
        >
          <rect x="1" y="1" width="98" height="138" rx="3" />
          <line x1="1" y1="70" x2="99" y2="70" />
          <circle cx="50" cy="70" r="14" />
          <circle className="ss-squad-pitch-dot" cx="50" cy="70" r="1.2" />
          <rect x="27" y="1" width="46" height="20" />
          <rect x="38" y="1" width="24" height="9" />
          <rect x="27" y="119" width="46" height="20" />
          <rect x="38" y="130" width="24" height="9" />
        </svg>

        {SLOTS.map((slot) => {
          const name = mates[slot.area] ?? null
          return (
            <div key={slot.area} className="ss-squad-seat" style={{ gridArea: slot.area }}>
              <div className="ss-pcard-mini">
                {slot.mine && card ? (
                  <PlayerCardView card={card} />
                ) : (
                  <SquadCardFrame>
                    {slot.mine ? (
                      <p className="ss-squad-note">아직 카드가 없습니다</p>
                    ) : editing === slot.area ? (
                      <input
                        autoFocus
                        aria-label={`${slot.label} 선수 이름`}
                        className="ss-squad-input"
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                        onBlur={() => commit(slot.area)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') commit(slot.area)
                          if (e.key === 'Escape') {
                            setEditing(null)
                            setDraft('')
                          }
                        }}
                      />
                    ) : name ? (
                      <button
                        type="button"
                        aria-label={`${name} 빼기`}
                        className="ss-squad-name"
                        onClick={() => setMates((prev) => ({ ...prev, [slot.area]: null }))}
                      >
                        {name}
                      </button>
                    ) : (
                      <button
                        type="button"
                        aria-label={`${slot.label} 자리에 선수 넣기`}
                        className="ss-squad-plus"
                        onClick={() => {
                          setEditing(slot.area)
                          setDraft('')
                        }}
                      >
                        +
                      </button>
                    )}
                  </SquadCardFrame>
                )}
              </div>
              <span className="ss-squad-pos">{slot.label}</span>
            </div>
          )
        })}
      </div>
    </GlassPanel>
  )
}

/**
 * 빈 카드의 틀. 선수 카드와 **같은 클래스**를 쓴다 — 따로 만들면 카드
 * 모양을 바꿀 때 두 벌이 따로 늙는다. 가운데 자리만 비워서 넘겨받는다.
 */
function SquadCardFrame({ children }: { children: React.ReactNode }) {
  return (
    <article className="ss-pcard">
      <div className="ss-pcard-inner">
        <header className="ss-pcard-top">
          <BrandMark size={22} color="var(--ss-pcard-fg)" />
          <p className="ss-pcard-kicker">PLAYER CARD</p>
        </header>
        <div className="ss-squad-seat-body">{children}</div>
      </div>
    </article>
  )
}
