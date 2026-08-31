'use client'

import { useEffect, useRef, useState } from 'react'
import type { PublicPlayerCard } from '@/server/backend'
import PlayerCardView from '@/components/PlayerCardView'
import BlankPlayerCard from '@/components/BlankPlayerCard'
import SquadSuggest from '@/components/SquadSuggest'
import SquadFriends from '@/components/SquadFriends'

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

// 추천 판이 닫히며 물러나는 시간 — globals.css 의 ss-suggest-out 과 같아야
// 한다. 짧으면 애니메이션 도중에 잘리고, 길면 사라진 자리가 남는다.
const SUGGEST_EXIT_MS = 200

const SLOTS: Slot[] = [
  { area: 'fw', label: 'FW', mine: true },
  { area: 'ml', label: 'MF' },
  { area: 'mr', label: 'MF' },
  { area: 'df', label: 'DF' },
  { area: 'gk', label: 'GK' },
]

export default function SquadPanel({
  card,
  friendSearch = false,
  onCloseFriendSearch,
}: {
  card?: PublicPlayerCard | null
  /** 알약 '지인 찾기' 가 골라져 있는가 — 켜지면 판 옆에 지인 찾기가 열린다. */
  friendSearch?: boolean
  onCloseFriendSearch?: () => void
}) {
  const [mates, setMates] = useState<Record<string, string | null>>({})
  /**
   * 지인 찾기에서 골라 둔 사람. 정해져 있으면 **빈 자리 버튼의 뜻이 바뀐다**
   * — 원래는 "AI 추천 열기"지만 이때는 "여기 넣기"다. 자리를 여기서 안 고르고
   * 진짜 판을 누르게 한 이유는 SquadFriends 주석에 있다.
   */
  const [placing, setPlacing] = useState<string | null>(null)
  // 지인 찾기 판이 DOM 에 있는가 — 닫힐 때 물러나는 동안 남아 있어야 한다.
  const [friendVisible, setFriendVisible] = useState(false)
  // 지금 추천을 열어 둔 자리. null 이면 닫혀 있다.
  const [picking, setPicking] = useState<Slot | null>(null)
  // 닫히는 중인 자리 — 물러나는 동안 DOM 에 남겨 둬야 애니메이션이 보인다.
  const [closing, setClosing] = useState<Slot | null>(null)
  const timer = useRef(0)

  const friendTimer = useRef(0)
  useEffect(() => () => {
    clearTimeout(timer.current)
    clearTimeout(friendTimer.current)
  }, [])

  // 지인 찾기가 켜지면 바로 띄우고, 꺼지면 물러나는 시간만큼 남겨 둔다.
  // 고르던 사람도 같이 지운다 — 판이 없는데 자리만 깜빡이면 안 된다.
  useEffect(() => {
    if (friendSearch) {
      clearTimeout(friendTimer.current)
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setFriendVisible(true)
      return
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPlacing(null)
    friendTimer.current = window.setTimeout(() => setFriendVisible(false), SUGGEST_EXIT_MS)
    return () => clearTimeout(friendTimer.current)
  }, [friendSearch])

  function close() {
    setClosing(picking)
    setPicking(null)
    clearTimeout(timer.current)
    timer.current = window.setTimeout(() => setClosing(null), SUGGEST_EXIT_MS)
  }

  // 열려 있는 동안 Esc 로 닫는다 — 바깥을 누르는 것과 같은 자리에 둔다.
  useEffect(() => {
    if (!picking) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') close()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  })

  /**
   * 이미 판에 들어가 있는 사람 → 그 자리 이름. 지인 목록이 이걸로 "여기
   * 있음" 표식을 붙이고 다시 못 고르게 막는다 — 없으면 같은 사람을 두 자리에
   * 넣을 수 있다.
   */
  const placed = Object.fromEntries(
    SLOTS.flatMap((slot) => {
      const name = mates[slot.area]
      return name ? [[name, slot.label] as const] : []
    }),
  )

  // 🔴 두 판(추천 · 지인)은 **같은 자리**에 뜬다 — 동시에 열면 겹친다.
  // 지인 찾기가 열려 있는 동안에는 추천을 그리지 않는다.
  const shown = friendSearch ? null : (picking ?? closing)

  return (
    /* 🔴 추천 판은 스쿼드 판의 **형제**다. 스쿼드 판이 overflow: hidden
       이라(모서리 밖으로 나가는 것을 자르려고) 자식으로 두면 판 밖으로
       나간 부분이 통째로 잘린다 — 실제로 그렇게 안 보였다. 자리 잡기는
       이 바깥 상자가 맡고, 두 판은 그 안에서 좌표를 잡는다. */
    <div className="ss-squad-wrap">
      {/* 유리 굴절(warp) — backdrop-filter 는 흐림·채도만 다루고 뒤 배경을
          휘게 하지는 못한다. 그건 SVG 필터의 몫이다: 부드러운 잡음
          (feTurbulence)을 만들고 그만큼 픽셀을 밀어(feDisplacementMap)
          두께 있는 유리를 통과한 것처럼 만든다. 세기(scale)는 실측으로
          골랐다 — 7 이면 화면의 9.7%가 달라지고(최대차 19), 15 면 18.4%
          (최대차 31)로 뒤 연기가 또렷하게 일렁인다. seed 를 고정해 두어
          새로고침해도 같은 무늬가 나온다. width/height 0 이라 자리를
          차지하지 않는다 — 정의만 두는 자리다. */}
      <svg width="0" height="0" aria-hidden="true" focusable="false" className="absolute">
        <filter
          id="ss-squad-warp"
          x="-10%"
          y="-10%"
          width="120%"
          height="120%"
          colorInterpolationFilters="sRGB"
        >
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.006 0.01"
            numOctaves="2"
            seed="4"
            result="warp"
          />
          <feDisplacementMap
            in="SourceGraphic"
            in2="warp"
            scale="15"
            xChannelSelector="R"
            yChannelSelector="G"
          />
        </filter>
      </svg>

      <section
        className="ss-squad"
        aria-label="내 스쿼드"
        // 🔴 backdrop-filter 는 **인라인으로** 준다. globals.css 에 두면
        // 같은 규칙의 color-mix() 때문에 Lightning CSS 가 @supports 로
        // 쪼개는 과정에서 통째로 떨어뜨린다(추천 판에서 실제로 그렇게
        // 날아갔다 — 계산값 none). 흐림 없이 굴절만 건다.
        style={{
          backdropFilter: 'url(#ss-squad-warp)',
          WebkitBackdropFilter: 'url(#ss-squad-warp)',
        }}
      >
      {/* 반짝임의 **시계**가 여기 하나 있다 — 자리마다 걸면 위상이 어긋난다
          (globals.css 의 --ss-beckon-t 주석 참고). */}
      <div className="ss-squad-board" data-placing={placing ? 'true' : undefined}>
        {/* 머리글이 경기장 선 **안쪽**에 앉아야 한다 — 판 위쪽에 따로
            두면 선 밖으로 나간다. 선을 그리는 상자 안에 넣고 위 여백을
            그만큼 준다(globals.css). */}
        <header className="ss-squad-head">
          <h2>MY SQUAD</h2>
          <p>풋살 5인</p>
        </header>

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
          <rect x="1" y="1" width="98" height="138" />
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
              {slot.mine ? (
                <div className="ss-pcard-mini">
                  {card ? (
                    <PlayerCardView card={card} />
                  ) : (
                    <BlankPlayerCard>
                      <p className="ss-squad-note">아직 카드가 없습니다</p>
                    </BlankPlayerCard>
                  )}
                </div>
              ) : (
                /* 🔴 카드 **전체**가 버튼이다. 가운데 + 만 눌리면 카드를
                   눌렀는데 아무 일도 안 일어나는 순간이 생긴다.
                   버튼이 곧 .ss-pcard-mini 여야 한다 — 그 규칙이 카드를
                   직접 자식으로 찾기 때문에(> .ss-pcard) 사이에 다른
                   요소를 끼우면 축소가 통째로 풀린다. */
                <button
                  type="button"
                  className="ss-pcard-mini ss-squad-seat-btn"
                  // 고른 지인이 있으면 이 버튼은 "여기 넣기"다 — 깜빡이는
                  // 것만으로는 스크린리더에서 아무 차이가 없다.
                  data-placing={!name && placing ? 'true' : undefined}
                  aria-label={
                    name
                      ? `${name} 빼기`
                      : placing
                        ? `${slot.label} 자리에 ${placing} 넣기`
                        : `${slot.label} 자리에 선수 넣기`
                  }
                  aria-expanded={
                    name || placing ? undefined : picking?.area === slot.area
                  }
                  onClick={() => {
                    if (name) {
                      setMates((prev) => ({ ...prev, [slot.area]: null }))
                      return
                    }
                    if (placing) {
                      setMates((prev) => ({ ...prev, [slot.area]: placing }))
                      // 판은 열어 둔다 — 여러 명을 이어서 넣는 게 보통이다.
                      setPlacing(null)
                      return
                    }
                    clearTimeout(timer.current)
                    setClosing(null)
                    setPicking(slot)
                  }}
                >
                  <BlankPlayerCard>
                    {name ? (
                      <span className="ss-squad-name">{name}</span>
                    ) : (
                      <span className="ss-squad-plus material-symbols-outlined" aria-hidden="true">
                        add
                      </span>
                    )}
                  </BlankPlayerCard>
                  {/* 빼는 표식 — 카드 오른쪽 위. 카드 **전체**가 이미 빼기
                      버튼이라(aria-label) 이건 장식이고 누를 수 있는 요소가
                      아니다. 버튼 안에 버튼을 두지 않는다.
                      카드의 형제로 둔다 — .ss-pcard-mini 는 카드를 직접
                      자식으로 찾으므로(> .ss-pcard) 감싸면 축소가 풀린다. */}
                  {name && (
                    <span className="ss-squad-remove material-symbols-outlined" aria-hidden="true">
                      cancel
                    </span>
                  )}
                </button>
              )}
              <span className="ss-squad-pos">{slot.label}</span>
            </div>
          )
        })}
      </div>

      </section>

      {/* 지인 찾기 판 — 추천 판과 **같은 자리**에 같은 방식으로 나온다. */}
      {friendVisible && (
        <SquadFriends
          placing={placing}
          placed={placed}
          closing={!friendSearch}
          onChoose={setPlacing}
          onClose={() => onCloseFriendSearch?.()}
        />
      )}

      {/* 추천 판 — 스쿼드 판 오른쪽에서 미끄러져 나온다. */}
      {shown && (
        <SquadSuggest
          position={shown.label}
          closing={picking === null}
          onClose={close}
          onPick={(name) => {
            setMates((prev) => ({ ...prev, [shown.area]: name }))
            close()
          }}
        />
      )}
    </div>
  )
}
