'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import type { PublicPlayerCard, Squad } from '@/server/backend'
import SquadPanel from '@/components/SquadPanel'
import MatchBot from '@/components/MatchBot'
import SiteHeader from '@/components/SiteHeader'
import HomeNav, { type Destination } from '@/components/HomeNav'
import { FRIEND_SEARCH, MATCH_BOT } from '@/lib/destinations'
import { useIntroDone } from '@/lib/useIntroDone'
import { useHideChrome, useLeaving } from '@/lib/pageTransition'
import LogoutButton from '@/components/LogoutButton'
import HomeFeed from '@/components/HomeFeed'

export type { Destination }

/**
 * 홈 한 화면 — 배경 사진 위에 글자를 얹는 레퍼런스(Nile Travel) 배치다.
 *
 *   워드마크        영상분석 레슨·상점 …       닉네임 로그아웃
 *   (용병 매칭) (내 팀)                    OWN / THE / PITCH
 *   스쿼드 판
 *
 * 예전에는 화면 아래에 카드 6장이 가로로 흐르는 캐러셀이 있었다. 카드가
 * 배경 사진을 절반 넘게 가려서, 목적지는 위쪽 **글자**로만 적고 카드는
 * 그 글자를 가리켰을 때만 아래로 떠오르게 바꿨다(`HomeNav`).
 *
 * 지금 가리킨 목적지(`active`)를 여기서 쥔다. 한때 우하단 번호 목록과
 * 강조를 맞추려고 올려 둔 상태인데, 그 목록을 지운 지금은 상단 글자
 * 내비만 쓴다 — 목록이 다시 생길 자리를 남겨 둔 것이다.
 *
 * 🔴 **글자는 마우스를 따라 움직이지 않는다.** 한때 마우스 시차로 헤더와
 * 헤드라인을 미세하게 흔들었는데(`useMouseParallax`), 글자가 화면을
 * 채우는 지금 배치에서는 읽는 내내 흔들려 어지러웠다 — 사용자 요청으로
 * 걷어냈다. 되살릴 거면 배경이나 사진 층에만 걸 것.
 */

export default function HomeStage({
  user,
  card,
  squad = null,
  destinations,
  featured = [],
  defaultActive = null,
}: {
  user: { nickname: string } | null
  /** 로그인한 사람의 선수 카드. 아직 카드가 없으면 null 이다. */
  card?: PublicPlayerCard | null
  /** 팀의 스쿼드. 팀이 없거나 아직 안 만들었으면 null 이다. */
  squad?: Squad | null
  destinations: Destination[]
  /**
   * 헤드라인 자리에 **유리 알약 버튼**으로 크게 내놓는 목적지들.
   * 상단 글자 줄(`destinations`)과 **겹치지 않아야 한다** — 같은 곳으로 가는
   * 항목을 한 화면에 둘 두지 않는다(우상단 '내 프로필'을 글자 줄에서 뺀 것과
   * 같은 규칙).
   */
  featured?: Destination[]
  /**
   * 아무것도 안 가리켰을 때 강조해 둘 목적지. 알약 둘 중 하나가 늘 골라져
   * 있어야 "고르는 자리"로 읽히기 때문이다 — 가리켰다 치우면 여기로 돌아온다
   * (`HomeNav` 는 치울 때 null 을 준다).
   */
  defaultActive?: string | null
}) {
  /**
   * 인트로가 끝나면 각 덩어리가 바깥에서 제자리로 들어온다(globals.css 의
   * `[data-enter]` 규칙). 헤더는 제 것을 따로 쥔다(SiteHeader).
   */
  const leaving = useLeaving()
  const entered = useIntroDone()

  /**
   * 아래로 굴리면 **화면이 통째로 비켜난다**(사용자 요청).
   *
   * 다른 화면으로 갈 때와 **같은 나가는 연출**을 쓴다 — 덩어리들이 들어온 방향
   * 그대로 되나가고(`data-enter='out'`), 그다음에 배경이 위로 빠지면서 아래에서
   * 완전한 검정이 올라온다(globals.css 의 `ss-home-out` 규칙들).
   *
   * 🔴 굴림 자체가 화면을 옮기지는 않는다. 홈은 한 화면짜리라 굴릴 것이 없고,
   * 굴림은 **신호로만** 쓴다(레슨 · 상점 입구의 `HeroGate` 와 같은 방식).
   */
  const [out, setOut] = useState(false)
  /**
   * 🔴 지금 상태를 **ref 로도** 들고 있는다. 굴림 듣기는 한 번만 걸고 다시 걸지
   * 않으므로(다시 걸면 굴리는 도중에 손잡이가 바뀐다) 그 안에서 읽는 값이 늘
   * 최신이어야 한다.
   */
  const outRef = useRef(out)
  useEffect(() => {
    outRef.current = out
  }, [out])
  /**
   * 영상 모음으로 내려간 것을 **기록에 한 걸음으로 남긴다**(사용자 요청).
   *
   * 🔴 안 남기면 브라우저 뒤로 가기가 이 화면을 통째로 떠나 **직전 주소**로 간다
   * (사용자 지적: 영상 모음에서 뒤로 갔더니 `/analysis` 가 나왔다). 주소는 그대로
   * 두고 표시만 쌓아, 뒤로 가기가 "홈 화면으로 되올라가기" 가 되게 한다 —
   * 레슨 · 상점 판이 쓰는 방식과 같다(`MarketGates`).
   */
  const stepped = useRef(false)
  /**
   * 🔴 떠나는 중인지를 **ref 로도** 들고 있는다. 아래 굴림 듣기는 한 번만 걸고
   * 다시 걸지 않으므로(다시 걸면 굴리는 도중에 손잡이가 바뀐다), 그 안에서
   * 읽는 값은 늘 최신이어야 한다.
   */
  const leavingRef = useRef(leaving)
  useEffect(() => {
    leavingRef.current = leaving
  }, [leaving])

  /**
   * 내려가고 올라오는 **유일한 길**. 상태를 직접 바꾸지 않고 **기록을 통해** 바꾼다
   * — 그래야 화면과 브라우저의 뒤로/앞으로가 같은 것을 가리킨다.
   */
  const goOut = useCallback((next: boolean) => {
    if (next === outRef.current) return
    if (next) {
      stepped.current = true
      window.history.pushState({ ssHome: 'feed' }, '')
      setOut(true)
      return
    }
    // 내려온 걸음이 있으면 되감는다(실제 되돌리기는 `popstate` 가 한다).
    if (stepped.current) {
      window.history.back()
      return
    }
    setOut(false)
  }, [])

  /** 뒤로/앞으로를 받아 화면을 그 걸음에 맞춘다. */
  useEffect(() => {
    const onPop = (e: PopStateEvent) => {
      const feed = (e.state as { ssHome?: string } | null)?.ssHome === 'feed'
      stepped.current = feed
      setOut(feed)
    }
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  /**
   * 🔴 다시 태어나도 기록에 적힌 자리로 돌아온다 — 라우터가 이 나무를 다시 그리면
   * 상태가 처음값으로 돌아가 영상 모음이 저 혼자 닫힌다(`MarketGates` 와 같은 함정).
   */
  useEffect(() => {
    if ((window.history.state as { ssHome?: string } | null)?.ssHome !== 'feed') return
    stepped.current = true
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setOut(true)
  }, [])

  useEffect(() => {
    /**
     * 🔴 트랙패드는 한 번 굴리는 동안 `deltaY` 가 0 이나 아주 작은 반대 부호로도
     * 들어온다 — 죽은 구간을 두지 않으면 내리는 몸짓 한가운데에 "올린다"가
     * 섞여 방금 내보낸 것을 도로 불러들인다(`HeroGate` 에서 이미 겪었다).
     */
    const DEAD = 4
    let touchY = 0

    const move = (dir: number) => {
      // 떠나는 중에는 아무것도 되돌리지 않는다 — 있던 자리 그대로 나가야 한다.
      if (dir === 0 || leavingRef.current) return
      goOut(dir > 0)
    }
    const dirOf = (d: number) => (d > DEAD ? 1 : d < -DEAD ? -1 : 0)

    const onWheel = (e: WheelEvent) => {
      if (e.ctrlKey) return
      move(dirOf(e.deltaY))
    }
    const onTouchStart = (e: TouchEvent) => {
      touchY = e.touches[0]?.clientY ?? 0
    }
    const onTouchMove = (e: TouchEvent) => {
      // 손가락이 위로 = 내용은 아래로 = 내리는 것.
      move(dirOf(touchY - (e.touches[0]?.clientY ?? 0)))
    }
    /** 자판으로도 오갈 수 있어야 한다 — 굴림이 없으니 이게 유일한 다른 길이다. */
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown' || e.key === 'PageDown' || e.key === ' ') move(1)
      else if (e.key === 'ArrowUp' || e.key === 'PageUp') move(-1)
    }

    window.addEventListener('wheel', onWheel, { passive: true })
    window.addEventListener('touchstart', onTouchStart, { passive: true })
    window.addEventListener('touchmove', onTouchMove, { passive: true })
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('wheel', onWheel)
      window.removeEventListener('touchstart', onTouchStart)
      window.removeEventListener('touchmove', onTouchMove)
      window.removeEventListener('keydown', onKey)
    }
  }, [goOut])

  /**
   * 🔴 배경 사진은 **레이아웃**이 그린다(`AppFigure`) — 이 컴포넌트에서 못
   * 건드린다. 그래서 표시를 문서에 걸어 CSS 가 움직이게 한다.
   */
  useEffect(() => {
    const el = document.documentElement
    if (out) el.dataset.ssHomeOut = 'true'
    else delete el.dataset.ssHomeOut
    return () => {
      delete el.dataset.ssHomeOut
    }
  }, [out])

  /**
   * 🔴 내려가 있는 동안 **워드마크는 눌린다**(사용자 요청) — 누르면 홈 화면으로
   * 되올라간다. 지금 화면이 이미 `/` 라 링크로는 아무 일도 안 일어나므로, 클릭을
   * 가로채 되올리기로 바꾼다. 헤더는 레이아웃이 그리므로 손댈 수가 없어 문서에서
   * 잡는다(누르기 **전에** 가로채야 해서 캡처 단계다).
   */
  useEffect(() => {
    if (!out) return
    const onClick = (e: MouseEvent) => {
      const mark = (e.target as HTMLElement | null)?.closest?.('[aria-label="홈"]')
      if (!mark) return
      e.preventDefault()
      e.stopPropagation()
      goOut(false)
    }
    document.addEventListener('click', onClick, true)
    return () => document.removeEventListener('click', onClick, true)
  }, [out, goOut])

  /** 헤더도 같이 나간다 — 다른 화면으로 갈 때와 같은 길을 쓴다. */
  useHideChrome(out)

  const enter = leaving || out ? 'out' : entered ? 'true' : 'false'
  /** 알약 줄에서 지금 가리킨 것. 헤더의 글자 줄과는 따로 논다. */
  const [active, setActive] = useState<string | null>(defaultActive)
  const activate = (title: string | null) => setActive(title ?? defaultActive)

  /**
   * 눌러서 고른 알약. `active` 는 가리키기만 해도 바뀌므로 실제 선택은
   * 이쪽이다 — '지인 찾기' 를 고르면 스쿼드 판 옆에 찾기 판이 열린다.
   */
  const [picked, setPicked] = useState<string | null>(defaultActive)
  const friendSearch = picked === FRIEND_SEARCH
  const matchBot = picked === MATCH_BOT

  return (
    <>
      {/* 🔴 아래에서 올라오는 **완전한 검정**(사용자 요청). 배경 사진(z-index -1)
          위, 무대(z-index 10) 아래에 깔려 사진만 덮는다. 덩어리들이 다 빠져나간
          뒤에 움직이도록 늦춘다(globals.css). */}
      <div className="ss-home-outro" data-up={out} aria-hidden={!out}>
        <HomeFeed active={out} by={user?.nickname ?? '나'} />
      </div>

      {/* 헤더는 모든 화면이 같이 쓴다(SiteHeader). 홈에서만 화면에
          고정한다 — 한 화면을 통째로 쓰는 배치라 흐름에 두면 가운데 정렬이
          밀린다. */}
      <SiteHeader user={user} card={card} destinations={destinations} fixed />

      {/* 헤드라인 · 보조 문구 · 정보 블록. 로그인 화면과 같은 문구를 쓴다 —
          두 화면이 한 목소리로 들리게. */}
      <div
        className="ss-home-stage"
        style={{ padding: 'var(--ss-home-content-pad)' }}
        data-enter={enter}
      >
        <div className="flex items-start justify-between gap-8">
          {/* 왼쪽 — 한 줄. 한때 두 줄 그리드로 쪼개(FIND | Y | OUR /
              SQUAD) 둘째 줄을 윗줄 둘째 글자에 맞췄는데, 한 줄로 바꾸면서
              그 장치가 통째로 필요 없어졌다 — 낱말을 span 으로 쪼갤 이유도,
              접근성 이름을 따로 줄 이유도 없다(그냥 글자 하나라 그대로
              읽힌다). 크기는 오른쪽 덩어리보다 한참 작다(아래 CSS). */}
          {/* 왼쪽 덩어리 — 헤드라인과 그 바로 아래 스쿼드 판. 자리
              잡기(위로 · 오른쪽으로)는 이 묶음이 맡는다. 안쪽 글자에
              margin 을 주면 판이 따라오지 않는다. */}
          <div className="ss-home-left">
            {/* 예전에는 여기에 큰 글자 `FIND YOUR SQUAD` 가 있었다. 읽기만
                하고 아무 데도 못 가는 자리라, 주요 목적지 두 개를 유리 알약
                버튼으로 바꿔 앉혔다(사용자 요청). 동작은 상단 글자 줄과 같다
                — 대거나 누르면 카드가 떠오르고, 이동은 그 카드가 한다. */}
            <div className="ss-home-featured">
              <HomeNav
                destinations={featured}
                loggedIn={Boolean(user)}
                active={active}
                onActivate={activate}
                variant="pill"
                label="주요 목적지"
                picked={picked}
                onPick={setPicked}
              />
            </div>
            <SquadPanel
              card={card}
              squad={squad}
              friendSearch={friendSearch}
              // 판의 × 로 닫으면 알약 선택도 같이 풀려야 한다 — 안 그러면
              // 고른 채로 판만 없어져 다시 눌러도 안 열린다.
              onCloseFriendSearch={() => {
                setPicked(defaultActive)
                setActive(defaultActive)
              }}
            />
          </div>

          {/* 오른쪽 — 왼쪽과 같은 글꼴 · 같은 크기(ss-home-display)로 세 줄.
              줄이 내려갈수록 시작점이 조금씩 오른쪽으로 밀린다(계단).
              여기도 낱말이 각자 span 이라 이름을 따로 준다. */}
          {/* 왼쪽 헤드라인이 알약 버튼으로 바뀌면서 이 줄이 화면의 유일한
              큰 글자가 됐다 — 문서에 h1 이 하나는 있어야 해서 여기로 옮겼다.
              보이는 모양은 그대로다(크기 · 계단은 아래 CSS 가 정한다). */}
          <h1 className="ss-home-display ss-home-subhead" aria-label="OWN THE PITCH">
            <span>OWN</span>
            <span>THE</span>
            <span>PITCH</span>
          </h1>
        </div>

        {/* 🔴 **내리면 무엇이 나오는지 미리 말한다**(사용자 요청). 레슨 · 상점
            입구와 같은 안내이고 같은 모양을 쓴다 — 같은 뜻의 것에 다른 모양을
            주지 않는다. 다른 것은 가리키는 곳뿐이라 글만 바꾼다.
            무대 **안**에 두므로 아래로 내릴 때 나머지와 같이 나간다. */}
        <p className="ss-market-scroll ss-home-hint">
          {/* 그림을 한 겹 싸는 이유 — 껍데기는 자리를 잡고, 안쪽 그림은 제
              흔들림(transform)을 쓴다. 한 겹으로 하면 둘이 서로 덮어쓴다. */}
          <span className="ss-market-scroll-icon" aria-hidden="true">
            <span className="material-symbols-outlined">keyboard_double_arrow_down</span>
          </span>
          아래로 내려 영상 둘러보기
        </p>
      </div>

      {/* 오른쪽 아래 구석 — 로그아웃 아이콘 하나. 여기 있던 01~05 번호
          목록은 지웠다(상단 글자 내비와 같은 목록이라 두 벌이었다). */}
      {user && (
        <div className="ss-home-footer" data-enter={enter}>
          <LogoutButton />
        </div>
      )}

      {/* 스쿼드 판과 달리 자리(포지션 슬롯)와 무관해 그 판 안에 넣지 않고
          독립된 떠 있는 판으로 연다 — SquadPanel 은 스쿼드 레이아웃 전용이다. */}
      <MatchBot
        open={matchBot}
        onClose={() => {
          setPicked(defaultActive)
          setActive(defaultActive)
        }}
      />
    </>
  )
}
