'use client'

import { useEffect, useRef, useState } from 'react'
import type { PublicPlayerCard, Squad } from '@/server/backend'
import PlayerCardView from '@/components/PlayerCardView'
import BlankPlayerCard from '@/components/BlankPlayerCard'
import SquadSuggest from '@/components/SquadSuggest'
import SquadFriends from '@/components/SquadFriends'
import MatchBot from '@/components/MatchBot'

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
 * 🔴 **읽기는 서버에서 온다**(2026-09-04). `GET /teams/{id}/squad` 가
 * 09-03 에 생겨서, 홈이 그것을 받아 `squad` 로 넘겨준다 — 새로고침해도
 * 등재된 사람이 그대로 앉아 있다.
 *
 * ⚠️ **넣기 · 빼기는 아직 이 컴포넌트 안에서만 일어난다.** 등재
 * (`POST …/squad/members`)가 `player_card_id` 를 요구하는데, **팀 구성원의
 * 카드 id 를 얻을 경로가 계약에 없다** — `GET /teams/{id}` 는 `user_id` ·
 * `nickname` · `role` 까지만 준다. 그 경로가 생기면 setMates 를 부르는 자리
 * 둘을 API 호출로 바꾸면 된다.
 *
 * 브라우저 저장은 일부러 안 넣었다 — 서버가 진짜가 되는 순간 상태가 두 곳에
 * 생겨 어느 쪽이 맞는지 헷갈린다.
 */

/** 판 위의 자리. `area` 는 globals.css 의 grid-template-areas 이름이다. */
type Slot = { area: string; label: string; mine?: boolean }

/** 판의 크기 — 3:3 · 5:5 · 7:7. 화면 글자와 같은 값이라 그대로 쓴다. */
export type SquadSize = '3' | '5' | '7'

/**
 * 크기마다의 포메이션.
 *
 * 🔴 **자리 이름을 역할+번호로 둔다**(`fw1` · `mf2` · `df1` …). 크기를 바꿔도
 * 같은 이름이 같은 자리를 가리켜야, 7인에서 넣은 사람이 5인으로 줄였다가
 * 되돌아왔을 때 **제자리에 그대로 앉아 있다**(사용자 요청: 줄어들면 감췄다가
 * 되돌리면 돌아온다). `ml`·`mr` 처럼 위치로 이름 지으면 3인의 MF 하나가
 * 어느 쪽인지부터 정해야 하고, 크기가 바뀔 때마다 이름이 갈린다.
 *
 * 🔴 포지션 코드는 계약이 정한 축구 넷(`GK`·`DF`·`MF`·`FW`)만 쓴다 — 세 판
 * 모두 그 안에서 된다(계약 3-4절). 새 코드를 만들지 않는다.
 */
export const FORMATIONS: Record<SquadSize, { label: string; slots: Slot[] }> = {
  // 1-1-1 — 셋이면 공격 · 중원 · 골키퍼 하나씩이다.
  '3': {
    label: '3 : 3',
    slots: [
      { area: 'fw1', label: 'FW', mine: true },
      { area: 'mf1', label: 'MF' },
      { area: 'gk', label: 'GK' },
    ],
  },
  // 1-2-1 — 풋살 5인. 이 판이 원래 그리던 것이다.
  '5': {
    label: '5 : 5',
    slots: [
      { area: 'fw1', label: 'FW', mine: true },
      { area: 'mf1', label: 'MF' },
      { area: 'mf2', label: 'MF' },
      { area: 'df1', label: 'DF' },
      { area: 'gk', label: 'GK' },
    ],
  },
  // 2-3-1 — 7인제에서 가장 흔한 형태다.
  '7': {
    label: '7 : 7',
    slots: [
      { area: 'fw1', label: 'FW', mine: true },
      { area: 'mf1', label: 'MF' },
      { area: 'mf2', label: 'MF' },
      { area: 'mf3', label: 'MF' },
      { area: 'df1', label: 'DF' },
      { area: 'df2', label: 'DF' },
      { area: 'gk', label: 'GK' },
    ],
  },
}

/** 처음 여는 크기 — 풋살 5인(사용자 요청). */
const DEFAULT_SIZE: SquadSize = '5'

// 추천 판이 닫히며 물러나는 시간 — globals.css 의 ss-suggest-out 과 같아야
// 한다. 짧으면 애니메이션 도중에 잘리고, 길면 사라진 자리가 남는다.
const SUGGEST_EXIT_MS = 200

/**
 * 서버가 준 스쿼드를 **판의 자리 이름표**로 바꾼다.
 *
 * 🔴 내 자리(FW)는 건너뛴다 — 거기는 `card` 가 그리므로, 서버 목록에 내가
 * 들어 있어도 같은 사람이 두 번 나오지 않는다.
 * 🔴 같은 포지션이 둘인 자리(MF)는 **먼저 온 사람부터** 채운다. 서버는 어느
 * 쪽 MF 인지까지는 모른다 — 좌 · 우는 화면만의 배치다.
 */
function seatsFromSquad(squad: Squad | null, slots: Slot[]): Record<string, string | null> {
  if (!squad) return {}
  const left = [...squad.members]
  const seats: Record<string, string | null> = {}
  for (const slot of slots) {
    if (slot.mine) continue
    const at = left.findIndex((m) => m.position_code === slot.label)
    if (at >= 0) seats[slot.area] = left.splice(at, 1)[0].nickname
  }
  return seats
}

export default function SquadPanel({
  card,
  squad = null,
  scouting = false,
  onCloseScouting,
  bot = false,
  onBotChange,
}: {
  card?: PublicPlayerCard | null
  /**
   * 서버가 준 스쿼드. **없을 수 있다** — 팀이 없거나(개인 계정) 팀은 있어도
   * 스쿼드를 아직 안 만든 경우다. 계약이 그 둘을 갈라 두었으므로(404
   * `SQUAD_NOT_FOUND`) 여기서도 null 하나로 뭉뚱그리지 않고, 판은 빈 자리로
   * 그린다.
   */
  squad?: Squad | null
  /**
   * 알약 '용병 찾기' 를 눌렀는가 — 켜지면 판 오른쪽에 **AI 추천 판과 지인
   * 찾기 판이 나란히** 열린다.
   *
   * 🔴 예전에는 '지인 찾기' 알약이 지인 판만 열었다. 두 일이 결국 **같은
   * 빈 자리를 채우는 한 가지 일**이라 단추를 하나로 합쳤다(사용자 요청,
   * 2026-09-08) — 그래서 판도 짝으로 여닫는다.
   */
  scouting?: boolean
  onCloseScouting?: () => void
  /**
   * AI 챗봇이 열려 있는가 — 켜지면 **지인 찾기와 같은 자리**에서 나온다.
   *
   * 🔴 챗봇 자체는 `HomeStage` 것이지만 그릴 자리는 여기다. 판 오른쪽
   * (`left: 100%`)은 `.ss-squad-wrap` 안에서만 잡히는 좌표라, 바깥에서
   * 그리면 그 자리를 다시 재서 옮겨야 한다 — 자리를 정하는 곳이 둘이 된다.
   */
  bot?: boolean
  onBotChange?: (next: boolean) => void
}) {
  /**
   * 🔴 **판 오른쪽은 이제 칸이 둘이다**(2026-09-08).
   *
   *   첫째 칸 — AI 추천 판 · 챗봇 (`.ss-suggest`)
   *   둘째 칸 — 지인 찾기 판 (`.ss-friends`)
   *
   * 전에는 셋이 **한 좌표**에 서서 "한 번에 하나만" 이 규칙이었다(여는 쪽이
   * 다른 것을 닫았다). 용병 찾기 하나가 추천과 지인을 **같이** 열어야 해서
   * 칸을 갈랐다 — 첫째 칸은 여전히 한 번에 하나다(챗봇이 켜지면 추천이 닫힌다).
   * 좌표는 globals.css 의 `--ss-side-panel-w` 가 정한다.
   */
  /* 🔴 서버가 준 것을 **첫 값으로만** 읽는다. 그 뒤로는 이 화면이 들고 있다 —
     넣기 · 빼기가 아직 서버로 안 가므로(위 주석), 매번 서버 값으로 되돌리면
     방금 넣은 사람이 사라진다. */
  /**
   * 판의 크기(3:3 · 5:5 · 7:7) — 머리글의 단추가 바꾼다(사용자 요청,
   * 2026-09-08). 전에는 「풋살 5인」이라고 적어 두기만 했다.
   */
  const [size, setSize] = useState<SquadSize>(DEFAULT_SIZE)
  const slots = FORMATIONS[size].slots

  /* 🔴 앉은 사람은 **크기가 줄어도 안 지운다**(사용자 요청). 자리 이름이
     역할+번호라(FORMATIONS 주석) 없어진 자리는 그리지 않을 뿐이고, 다시
     키우면 그대로 앉아 있다 — 실수로 눌렀을 때 잃는 것이 없다. */
  const [mates, setMates] = useState<Record<string, string | null>>(() =>
    seatsFromSquad(squad, FORMATIONS[DEFAULT_SIZE].slots),
  )
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
    if (scouting) {
      clearTimeout(friendTimer.current)
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setFriendVisible(true)
      return
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPlacing(null)
    friendTimer.current = window.setTimeout(() => setFriendVisible(false), SUGGEST_EXIT_MS)
    return () => clearTimeout(friendTimer.current)
  }, [scouting])

  /**
   * 용병 찾기로 열 때 **어느 자리의 추천**을 낼 것인가 — 빈 자리 중 첫
   * 번째다(FW → MF → MF → DF → GK). 이 순서는 판 위에서 위에서 아래로
   * 읽히는 순서라, "지금 가장 급한 자리"로 그대로 읽힌다.
   * 다 찼으면 마지막 자리를 낸다 — 판이 안 열리는 것보다 낫다(빼고 나서
   * 다시 누를 필요가 없다).
   */
  const firstEmpty =
    slots.find((slot) => !slot.mine && !mates[slot.area]) ?? slots[slots.length - 1]

  /* 알약이 켜지면 추천 판도 같이 연다. 🔴 **자리를 여기서 다시 고르지
     않는다** — 빈 자리를 직접 눌러 연 뒤(picking 이 이미 있다) 알약 상태가
     바뀌었다고 그 자리를 첫 빈 자리로 되돌리면, 방금 고른 자리가 사라진다. */
  useEffect(() => {
    clearTimeout(timer.current)
    if (scouting) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setClosing(null)
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setPicking((now) => now ?? firstEmpty)
      return
    }
    // 꺼지면 추천 판도 같이 접는다 — 한 단추가 연 한 벌이다.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPicking((now) => {
      if (now) {
        setClosing(now)
        timer.current = window.setTimeout(() => setClosing(null), SUGGEST_EXIT_MS)
      }
      return null
    })
    // firstEmpty 는 자리가 채워질 때마다 새 값이 된다 — 넣을 때마다 판이
    // 다시 열리면 안 되므로 켜고 끄는 순간만 본다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scouting])

  /**
   * 🔴 **챗봇이 켜지면 추천 판을 닫는다** — 둘은 **첫째 칸**을 나눠 쓴다.
   *
   * ⚠️ 빈 자리를 눌러 연 추천은 `scouting` 이 아니라 이 판이 제 상태
   * (`picking`)로 들고 있다. 그래서 알약으로 연 경우만 닫히고, **빈 자리로
   * 연 경우에는 AI 판이 그 뒤에 나왔다**(사용자 지적) — 같은 좌표라 z 로는
   * 가려질 뿐이다. 여는 쪽이 닫는다는 규칙을 이 길에도 건다.
   *
   * 빈 자리 누르기 쪽에도 `onBotChange?.(false)` 가 있어 **양쪽이 서로를
   * 닫는다** — 어느 쪽을 먼저 눌러도 첫째 칸에는 하나만 선다.
   */
  useEffect(() => {
    if (!bot) return
    clearTimeout(timer.current)
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPicking((now) => {
      if (now) {
        setClosing(now)
        timer.current = window.setTimeout(() => setClosing(null), SUGGEST_EXIT_MS)
      }
      return null
    })
  }, [bot])

  function close() {
    setClosing(picking)
    setPicking(null)
    clearTimeout(timer.current)
    timer.current = window.setTimeout(() => setClosing(null), SUGGEST_EXIT_MS)
    // 🔴 알약으로 연 한 벌이면 **둘 다** 접는다. 추천만 닫고 지인 판을
    // 남기면, 알약은 아직 켜진 것으로 남아 다시 눌러도 안 열린다.
    onCloseScouting?.()
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
    slots.flatMap((slot) => {
      const name = mates[slot.area]
      return name ? [[name, slot.label] as const] : []
    }),
  )

  /* 🔴 전에는 두 판이 **같은 자리**라 지인 찾기가 열려 있는 동안 추천을
     아예 안 그렸다. 이제 칸이 둘이라(위 주석) 같이 뜬다 — 그 막음을 걷어냈다.
     첫째 칸을 챗봇과 나눠 쓰는 것은 그대로다(챗봇을 켜면 추천이 닫힌다). */
  const shown = picking ?? closing

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
      {/* 🔴 배치는 CSS 가 `data-size` 로 고른다 — grid-template-areas 를 인라인
          으로 주면 자리 이름이 두 곳(여기와 globals.css)에 살게 된다. */}
      <div
        className="ss-squad-board"
        data-size={size}
        data-placing={placing ? 'true' : undefined}
      >
        {/* 머리글이 경기장 선 **안쪽**에 앉아야 한다 — 판 위쪽에 따로
            두면 선 밖으로 나간다. 선을 그리는 상자 안에 넣고 위 여백을
            그만큼 준다(globals.css). */}
        <header className="ss-squad-head">
          <h2>MY SQUAD</h2>
          {/* 🔴 「풋살 5인」이라고 **적어 두기만** 하던 자리다 — 이제 고를 수
              있다(사용자 요청, 2026-09-08). 판의 배치가 같이 바뀐다.
              라디오처럼 하나만 골라진다 — 판이 동시에 두 크기일 수는 없다. */}
          <div className="ss-squad-size" role="radiogroup" aria-label="판 크기">
            {(Object.keys(FORMATIONS) as SquadSize[]).map((key) => (
              <button
                key={key}
                type="button"
                role="radio"
                aria-checked={size === key}
                className="ss-squad-size-btn"
                data-on={size === key ? 'true' : undefined}
                onClick={() => setSize(key)}
              >
                {FORMATIONS[key].label}
              </button>
            ))}
          </div>
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

        {slots.map((slot) => {
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
                    // 🔴 추천 판도 챗봇과 **같은 자리**에 선다 — 켜져 있으면
                    // 먼저 물린다(그냥 열면 챗봇 뒤에 가려 나온다).
                    onBotChange?.(false)
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

      {/* 지인 찾기 판 — 추천 판 **바로 오른쪽**(둘째 칸)에 같은 방식으로
          나온다. 자리는 globals.css 의 `.ss-friends` 가 정한다. */}
      {friendVisible && (
        <SquadFriends
          placing={placing}
          placed={placed}
          closing={!scouting}
          onChoose={setPlacing}
          onClose={() => onCloseScouting?.()}
        />
      )}

      {/* 🔴 AI 단추는 **판의 오른쪽 변에 붙는다**(사용자 요청). 그래서
          알약 줄이 아니라 **여기**서 그린다 — 판 폭은 `width: max-content`
          라 CSS 상수가 없고(내용이 정한다), 판 바깥에서 맞추려면 그 폭을
          다시 재서 두 곳에서 자리를 정하게 된다. 판 안에서는 `right: 0`
          한 줄이면 무슨 폭이든 정확히 오른쪽 끝이다. */}
      <button
        type="button"
        className="ss-home-ai ss-traveling-edge"
        aria-label="AI 용병 찾기"
        aria-expanded={bot}
        onClick={() => onBotChange?.(!bot)}
      >
        AI
      </button>

      {/* AI 챗봇 — 추천 판과 **같은 첫째 칸**이다(사용자 요청). 여는 쪽이
          상대를 닫는다(`onBotChange` · 빈 자리 누르기). 둘째 칸의 지인 판과는
          자리가 갈렸으므로 겹치지 않는다. */}
      {bot && <MatchBot open onClose={() => onBotChange?.(false)} />}

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
