'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import type { PublicPlayerCard, Squad } from '@/server/backend'
import SquadPanel from '@/components/SquadPanel'
import SiteHeader from '@/components/SiteHeader'
import { useNotifyInbox } from '@/lib/useNotifyInbox'
import { takeMatchOpen } from '@/lib/seekingStore'
import HomeNav, { type Destination } from '@/components/HomeNav'
import { MATCH_BOT, TEAM_SEEK } from '@/lib/destinations'
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
  sportCode = null,
  teamName = null,
  myCardId = null,
  isCaptain = false,
  destinations,
  featured = [],
  defaultActive = null,
}: {
  user: { nickname: string } | null
  /** 로그인한 사람의 선수 카드. 아직 카드가 없으면 null 이다. */
  card?: PublicPlayerCard | null
  /** 팀의 스쿼드. 팀이 없거나 아직 안 만들었으면 null 이다. */
  squad?: Squad | null
  /** 그 팀의 종목 — 스쿼드 판이 포지션 목록을 받아 올 때 쓴다(CCC 28). */
  sportCode?: string | null
  /** 홈에 그리는 팀 이름 — 스쿼드 판의 머리글. 소속이 없으면 `null`. */
  teamName?: string | null
  /** 내 카드 id — 판에 나를 앉힐 때 쓴다(계약이 `player_card_id` 를 받는다). */
  myCardId?: string | null
  /**
   * 내가 이 팀의 **팀장인가**(`role === 'owner'`).
   *
   * 🔴 **기본이 `false` 다.** 안 넘기면 못 만지는 쪽으로 떨어진다 — 권한은
   * 빠뜨렸을 때 **막히는** 편이 맞다.
   */
  isCaptain?: boolean
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
   * 영상 모음으로 내려가 있는가 — **누를 때만 바뀐다**(사용자 요청,
   * 2026-09-18).
   *
   * 다른 화면으로 갈 때와 **같은 나가는 연출**을 쓴다 — 덩어리들이 들어온 방향
   * 그대로 되나가고(`data-enter='out'`), 그다음에 배경이 위로 빠지면서 아래에서
   * 완전한 검정이 올라온다(globals.css 의 `ss-home-out` 규칙들).
   *
   * 🔴 **굴림·터치·자판으로는 안 넘어간다.** 한때 굴림을 신호로 받았는데
   * (레슨 · 상점 입구의 `HeroGate` 와 같은 방식), 홈은 굴릴 것이 없는 한
   * 화면이라 **의도하지 않은 굴림 하나하나가 화면을 통째로 바꿨다** — 판
   * 위에서 굴린 것, 챗봇에 글을 치다 누른 스페이스, 트랙패드의 되튐까지
   * 전부 이 길로 새어 들어와 그때마다 예외를 하나씩 붙이고 있었다.
   * 길을 **누르는 것 하나로** 좁혀 그 부류를 통째로 없앤다.
   *
   * 🔴 되살리지 말 것 — 아래 둘이 그 자리다:
   *   내려가기 = 무대 바닥의 「클릭해서 영상 둘러보기」 단추
   *   올라오기 = 워드마크(`[aria-label="홈"]`) 누르기
   */
  const [out, setOut] = useState(false)
  /**
   * 🔴 지금 상태를 **ref 로도** 들고 있는다 — `goOut` 이 기록을 건드리기 전에
   * 같은 걸음을 두 번 걷지 않는지 보는 자물쇠다(아래 머리말).
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
   * 내려가고 올라오는 **유일한 길**. 상태를 직접 바꾸지 않고 **기록을 통해** 바꾼다
   * — 그래야 화면과 브라우저의 뒤로/앞으로가 같은 것을 가리킨다.
   */
  const goOut = useCallback((next: boolean) => {
    if (next === outRef.current) return
    /**
     * 🔴 **여기서 바로 못박는다 — 렌더를 기다리면 안 된다.**
     *
     * 한 번 누른 것이 렌더 전에 두 번 들어올 수 있다(빠른 두 번 누르기,
     * 단추와 문서 쪽 잡개가 같은 클릭을 볼 때). `outRef` 를 effect 에서만
     * 갱신하면 그 둘이 **같은 옛 값**을 보고 각자 기록을 건드린다 — 내려갈 때
     * `pushState` 가 두 번 쌓이고 올라올 때 `history.back()` 이 두 번 나간다.
     * 두 수가 다르면 남는 뒤로 가기가 **화면 밖으로 걸어 나간다**(굴림으로
     * 오가던 시절 도메인에서 실제로 겪었다: 영상 모음에서 휠을 올렸더니
     * `/market` 으로 가거나 사이트를 떠났다. 2026-09-06 헤드리스로 재현).
     *
     * 정본은 여전히 기록이다(`popstate` 가 마지막에 맞춘다). 이 값은 같은
     * 걸음을 두 번 걷지 않기 위한 **자물쇠**다.
     */
    outRef.current = next
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

  /**
   * ⛔ **여기 있던 굴림 · 터치 · 자판 듣기를 걷어냈다**(사용자 요청,
   * 2026-09-18: 「스크롤 문제 계속 있어서 그냥 클릭해서만 넘어가게 만들자」).
   *
   * 무엇이 있었는지 남겨 둔다 — 되살리려는 사람이 같은 값을 다시 치르지
   * 않도록:
   *
   * | 무엇 | 왜 붙어 있었나 |
   * |---|---|
   * | 죽은 구간 `DEAD = 4` | 트랙패드가 내리는 몸짓 한가운데에 반대 부호를 섞는다 |
   * | `onOwnPanel` 선택자 다섯 | 챗봇 · 추천 판 · 경기 판 · 리뷰 위에서 굴린 것이 창까지 올라온다 |
   * | `isTyping` · `isComposing` | 스페이스는 **띄어쓰기**다 — 챗봇에 「안녕하세요. 」를 치면 넘어갔다 |
   *
   * 🔴 셋 다 **같은 결함의 증상**이다: 굴림은 어디서 났는지가 안 적혀 오는
   * 신호라, 화면 전체를 바꾸는 일을 그것에 맡기면 예외 목록이 끝없이 는다.
   * 판을 하나 새로 만들 때마다 여기 선택자를 더해야 했고, 실제로 매번
   * 빠뜨려서 사용자가 잡아 줬다(2026-09-08 · 09-18 두 번).
   *
   * 단추로 옮기면 그 목록이 통째로 필요 없다 — 누른 자리가 곧 뜻이다.
   */

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
  /**
   * **용병 찾기를 눌렀는가** — 켜지면 스쿼드 판 오른쪽에 추천 판과 지인
   * 찾기 판이 **나란히** 열린다.
   *
   * 🔴 `picked === MATCH_BOT` 으로 판단하지 않는다. 그 제목이
   * `DEFAULT_FEATURED` 이기도 해서 **홈에 들어오자마자 켜져 있고, ×를 눌러
   * 선택을 `defaultActive` 로 되돌리면 곧바로 다시 켜진다** — 챗봇을 이
   * 알약으로 열던 시절에 실제로 그렇게 갇혔다(destinations.ts 주석).
   * 알약 선택과 **떼어 놓은 제 상태**여야 그 얽힘이 안 생긴다.
   */
  const [scouting, setScouting] = useState(false)

  /* 🔴 헤더(`SiteHeader`)도 제 통을 따로 돈다 — 빨간 점과 판은 그쪽 것이고,
     여기 것은 **대기 팝업을 띄울 신호**를 받기 위한 것이다. 폴링 둘이 도는
     셈이지만 GET 둘이라 가볍고, 하나로 합치려면 통을 앱 전체 컨텍스트로
     올려야 해서 그 값이 더 비싸다. */
  const inbox = useNotifyInbox()

  /**
   * 🔴 **다른 화면에서 「경기 잡힘」을 누르고 온 경우**(사용자 요청,
   * 2026-09-18). 경기 화면을 그리는 것은 이 아래 스쿼드 판뿐이라, 다른
   * 화면에서는 「열어 달라」만 적어 두고 홈으로 보낸다 — 여기서 집어 연다.
   *
   * 🔴 **집으면서 지운다**(`takeMatchOpen`). 안 지우면 그 뒤로 홈에 들어올
   * 때마다 경기 화면이 저절로 뜬다 — 「누를 때만 뜬다」가 규칙이다.
   * 🔴 `confirmed` 를 기다린다 — 첫 조회가 오기 전에는 열 내용이 없다.
   */
  const asked = useRef<string | null>(null)
  useEffect(() => {
    if (asked.current === null) asked.current = takeMatchOpen()
    if (!asked.current || !inbox.confirmed) return
    if (asked.current !== inbox.confirmed.matchId) return
    asked.current = null
    inbox.reopenConfirmed()
  }, [inbox])

  /**
   * 챗봇이 열려 있는가.
   *
   * 🔴 **알약(`picked`)과 떼어 놓는다**(사용자 요청). 한때 `picked === '용병
   * 찾기'` 로 열었는데, 그 값이 `defaultActive` 로 시작하는 바람에 **홈에
   * 들어오자마자 떠 있었고 닫기(×)를 눌러도 `defaultActive` 로 되돌아가
   * 다시 열렸다**(실측). 여는 자리를 제 단추 하나로 옮기면서 그 얽힘이
   * 통째로 없어졌다 — 알약 셋은 이제 챗봇과 아무 상관이 없다.
   */
  const [bot, setBot] = useState(false)
  /**
   * 알약 '팀원' 을 눌렀는가 — 켜지면 **스쿼드 판 자리에** 사람을 찾는 팀들의
   * 명단이 선다(사용자 요청, 2026-09-08).
   *
   * 🔴 `picked === TEAM_SEEK` 로 판단해도 지금은 안전하다(그 제목은
   * `defaultActive` 가 아니다). 그래도 제 상태로 드는 것은 **기본 알약이
   * 나중에 바뀌어도 여기가 안 흔들리게** 하기 위해서다 — '용병 찾기' 를
   * `picked` 로 열었다가 갇힌 적이 있다(destinations.ts 주석).
   */
  const [seeking, setSeeking] = useState(false)

  /**
   * 🔴 **판 오른쪽 자리는 한 번에 하나만 쓴다**(사용자 지적: AI 를 켠 채
   * 지인 찾기를 누르면 AI 가 사라지지 않고 **그 뒤에** 나왔다).
   *
   * 셋(챗봇 · 지인 찾기 · AI 추천)이 같은 좌표에 서므로 z 를 아무리 손봐야
   * 뒤에 가려질 뿐이다 — 여는 쪽에서 **다른 것을 닫는 것**이 맞다.
   *
   * 알약 선택을 `defaultActive` 로 되돌리는 것은 지인 찾기 판의 × 가 하는
   * 것과 같다 — 알약 하나는 늘 골라져 있어야 "고르는 자리"로 읽힌다.
   */
  const showBot = useCallback(
    (next: boolean) => {
      setBot(next)
      if (!next) return
      // 챗봇이 서는 곳은 **첫째 칸**이다 — 추천 판을 밀어낸다. 둘째 칸의
      // 지인 판까지 닫을 이유는 없지만, 짝으로 여닫는 것이라 같이 접는다.
      setScouting(false)
      setSeeking(false)
      setPicked(defaultActive)
      setActive(defaultActive)
    },
    [defaultActive],
  )

  /**
   * 알약을 고르면 챗봇은 물러난다 — 첫째 칸을 같이 쓴다.
   *
   * '용병 찾기'는 **한 번 더 누르면 닫힌다**(토글). 이 알약은 늘 골라져
   * 있는 기본값이라, 누를 때마다 열기만 하면 닫을 길이 판의 ×밖에 없다.
   */
  const pick = useCallback((title: string | null) => {
    setPicked(title)
    setBot(false)
    setScouting((on) => (title === MATCH_BOT ? !on : false))
    /* 🔴 '팀원' 도 **한 번 더 누르면 닫힌다**(토글). 이 판은 스쿼드 판을
       대신 서므로, 닫을 길이 판의 × 뿐이면 알약을 눌러 놓고 되돌리는 길이
       없다 — '팀장' 과 같은 규칙이다. */
    setSeeking((on) => (title === TEAM_SEEK ? !on : false))
  }, [])

  /** 판의 × — 둘 중 어느 쪽을 닫아도 짝으로 접힌다(한 단추가 연 한 벌이다). */
  const closeScout = useCallback(() => setScouting(false), [])
  /** 팀원 판의 × — 스쿼드 판이 도로 선다. */
  const closeSeek = useCallback(() => setSeeking(false), [])

  return (
    <>
      {/* 🔴 아래에서 올라오는 **완전한 검정**(사용자 요청). 배경 사진(z-index -1)
          위, 무대(z-index 10) 아래에 깔려 사진만 덮는다. 덩어리들이 다 빠져나간
          뒤에 움직이도록 늦춘다(globals.css). */}
      <div className="ss-home-outro" data-up={out} aria-hidden={!out}>
        <HomeFeed active={out} />
      </div>

      {/* 헤더는 모든 화면이 같이 쓴다(SiteHeader). 홈에서만 화면에
          고정한다 — 한 화면을 통째로 쓰는 배치라 흐름에 두면 가운데 정렬이
          밀린다. */}
      {/* 🔴 **알림함을 내려보낸다**(2026-09-17). 헤더가 제 통을 따로 만들면
          거기서 수락한 결과(`acceptedTeam`)가 대기 화면을 그리는 `SquadPanel`
          쪽 통에 **영영 안 들어간다** — 눌러도 아무 일이 없었다. */}
      <SiteHeader
        user={user}
        card={card}
        destinations={destinations}
        fixed
        inbox={inbox}
        /* 🔴 **홈만 준다** — 경기 화면은 아래 스쿼드 판이 그린다. */
        onReopenMatch={inbox.reopenConfirmed}
      />

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
                onPick={pick}
              />
            </div>
            <SquadPanel
              /* 경기 신청 · 확정은 헤더의 알림함과 한 벌이다 — 신청은 여기서
                 걸고, **확정은 알림이 알려 준다**(사용자 요청, 2026-09-16). */
              myTeamId={inbox.teamId}
              onRequested={(requestId, team) => inbox.noteSent(requestId, team.id)}
              acceptedTeamId={inbox.acceptedTeamId}
              acceptedTeam={inbox.acceptedTeam}
              acceptedUs={inbox.acceptedUs}
              acceptedMatchId={inbox.acceptedMatchId}
              onAcceptedShown={() => {
                inbox.clearAccepted()
                /* 🔴 **닫으면 메인으로 돌아온다**(사용자 요청, 2026-09-18:
                   「리뷰 마치고 이 화면으로 넘어오는데 메인으로 넘어오게」).
                   판이 화면을 덮고 있는 동안 뒤가 영상 모음으로 내려가
                   있을 수 있어서, 닫는 김에 무대로 되돌린다. */
                setOut(false)
              }}
              card={card}
              squad={squad}
              sportCode={sportCode}
              teamName={teamName}
              isCaptain={isCaptain}
              myCardId={myCardId}
              scouting={scouting}
              // 🔴 챗봇도 **판 오른쪽 그 자리**에서 나온다(사용자 요청) —
              // 지인 찾기 · AI 추천과 같은 자리다. 그 자리는 `.ss-squad-wrap`
              // 안에서만 잡히므로(`left: 100%`) 여기서 못 그리고 판에 넘긴다.
              bot={bot}
              onBotChange={showBot}
              onCloseScouting={closeScout}
              // 빈 자리(+)를 눌러도 알약과 **같은 한 벌**이 열린다
              // (사용자 요청, 2026-09-16) — 추천 판 옆에 지인 찾기 판도 선다.
              onOpenScouting={() => setScouting(true)}
              seeking={seeking}
              onCloseSeeking={closeSeek}
            />
          </div>

          {/* 오른쪽 — 왼쪽과 같은 글꼴 · 같은 크기(ss-home-display)로 세 줄.
              줄이 내려갈수록 시작점이 조금씩 오른쪽으로 밀린다(계단).
              여기도 낱말이 각자 span 이라 이름을 따로 준다. */}
          {/* 왼쪽 헤드라인이 알약 버튼으로 바뀌면서 이 줄이 화면의 유일한
              큰 글자가 됐다 — 문서에 h1 이 하나는 있어야 해서 여기로 옮겼다.
              보이는 모양은 그대로다(크기 · 계단은 아래 CSS 가 정한다). */}
          {/* 🔴 판이 열리면 **비켜선다**(사용자 요청). 추천 판과 지인 판이
              나란히 서면 이 글자 자리를 침범한다 — 1440 에서 298px, 1700
              에서 161px 을 파고든다(실측). 글자는 읽고 마는 장식이고 판은
              지금 하는 일이라, 비키는 쪽은 글자다.
              🔴 **오른쪽으로 크게 못 민다** — 이미 화면 오른쪽 끝에 닿아
              있다(1280 에서 왼끝 938). 그래서 조금 물러나며 흐려진다. */}
          <h1
            className="ss-home-display ss-home-subhead"
            aria-label="OWN THE PITCH"
            data-aside={scouting ? 'true' : undefined}
          >
            <span>OWN</span>
            <span>THE</span>
            <span>PITCH</span>
          </h1>
        </div>

        {/* 🔴 **영상 모음으로 가는 유일한 길**(사용자 요청, 2026-09-18).
            한때는 「아래로 내려…」라고 적힌 **안내문**이었고 실제로 넘기는
            것은 굴림이었다. 굴림을 걷어낸 지금은 이것이 문이므로 `<p>` 가
            아니라 **단추**여야 한다 — 자판과 화면 낭독기가 누를 수 있는 것은
            단추뿐이고, 굴림을 없애면서 그 둘의 길까지 없애면 안 된다.
            모양은 레슨 · 상점 입구의 안내와 같은 것을 그대로 쓴다.
            무대 **안**에 두므로 아래로 내릴 때 나머지와 같이 나간다. */}
        {/* 🔴 **옆 판이 열려 있는 동안은 안 눌린다**(사용자 요청, 2026-09-18:
            「판이랑 겹칠 때는 그냥 판이 위로 오게 · 판을 닫아야 클릭」).
            겹쳐 보이는 것은 CSS 가 판을 위에 두어 푸는데(globals.css 의
            `body:has(.ss-suggest)`), 그 `pointer-events: none` 은 **마우스만**
            막는다 — 자판으로 짚어 Enter 를 누르면 그대로 넘어간다. 못 누르게
            하는 뜻은 여기 `disabled` 가 정본이고 CSS 는 보이는 쪽 몫이다. */}
        <button
          type="button"
          className="ss-market-scroll ss-home-hint"
          onClick={() => goOut(true)}
          disabled={scouting}
        >
          {/* 그림을 한 겹 싸는 이유 — 껍데기는 자리를 잡고, 안쪽 그림은 제
              흔들림(transform)을 쓴다. 한 겹으로 하면 둘이 서로 덮어쓴다. */}
          <span className="ss-market-scroll-icon" aria-hidden="true">
            <span className="material-symbols-outlined">keyboard_double_arrow_down</span>
          </span>
          클릭해서 영상 둘러보기
        </button>
      </div>

      {/* 오른쪽 아래 구석 — 로그아웃 아이콘 하나. 여기 있던 01~05 번호
          목록은 지웠다(상단 글자 내비와 같은 목록이라 두 벌이었다). */}
      {user && (
        <div className="ss-home-footer" data-enter={enter}>
          <LogoutButton />
        </div>
      )}

    </>
  )
}
