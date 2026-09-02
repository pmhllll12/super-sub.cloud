'use client'

import { useState } from 'react'
import type { PublicPlayerCard } from '@/server/backend'
import SquadPanel from '@/components/SquadPanel'
import SiteHeader from '@/components/SiteHeader'
import HomeNav, { type Destination } from '@/components/HomeNav'
import { FRIEND_SEARCH } from '@/lib/destinations'
import { useIntroDone } from '@/lib/useIntroDone'
import { useLeaving } from '@/lib/pageTransition'
import LogoutButton from '@/components/LogoutButton'

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
  destinations,
  featured = [],
  defaultActive = null,
}: {
  user: { nickname: string } | null
  /** 로그인한 사람의 선수 카드. 아직 카드가 없으면 null 이다. */
  card?: PublicPlayerCard | null
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
  const enter = leaving ? 'out' : entered ? 'true' : 'false'
  /** 알약 줄에서 지금 가리킨 것. 헤더의 글자 줄과는 따로 논다. */
  const [active, setActive] = useState<string | null>(defaultActive)
  const activate = (title: string | null) => setActive(title ?? defaultActive)

  /**
   * 눌러서 고른 알약. `active` 는 가리키기만 해도 바뀌므로 실제 선택은
   * 이쪽이다 — '지인 찾기' 를 고르면 스쿼드 판 옆에 찾기 판이 열린다.
   */
  const [picked, setPicked] = useState<string | null>(defaultActive)
  const friendSearch = picked === FRIEND_SEARCH

  return (
    <>

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
