'use client'

import Link from 'next/link'
import { useState } from 'react'
import type { PublicPlayerCard } from '@/server/backend'
import PlayerCardView from '@/components/PlayerCardView'
import BrandMark from '@/components/ui/BrandMark'
import FigureBackground from '@/components/FigureBackground'
import HomeNav, { type Destination } from '@/components/HomeNav'
import LogoutButton, { HEADER_LINK_CLASS, HEADER_LINK_HOVER_CLASS } from '@/components/LogoutButton'

export type { Destination }

/**
 * 홈 한 화면 — 배경 사진 위에 글자를 얹는 레퍼런스(Nile Travel) 배치다.
 *
 *   워드마크        영상분석 용병매칭 …        닉네임 로그아웃
 *   OWN THE / PITCH                     FIND / YOUR / SQUAD
 *                                              01~05 번호 목록
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
}: {
  user: { nickname: string } | null
  /** 로그인한 사람의 선수 카드. 아직 카드가 없으면 null 이다. */
  card?: PublicPlayerCard | null
  destinations: Destination[]
}) {
  const [active, setActive] = useState<string | null>(null)

  return (
    <>
      <FigureBackground />

      {/* 헤더 — 워드마크 · 목적지 글자 · 인사말. 화면에 고정한다. */}
      <div
        // 워드마크 · 목적지 글자 · 인사말 세 덩어리 사이는 목적지 글자
        // **칸 사이(40px)보다 넉넉히** 띄운다 — 안 그러면 닉네임이 목적지
        // 글자 하나처럼 붙어 읽힌다(실측: 32px 이면 그렇게 보였다).
        className="fixed inset-x-0 top-0 z-20 flex items-start justify-between gap-16"
        style={{ padding: 'var(--ss-home-content-pad)' }}
      >
        <BrandMark size={26} />

        <div className="ss-home-nav-slot">
          <HomeNav
            destinations={destinations}
            loggedIn={Boolean(user)}
            active={active}
            onActivate={setActive}
          />
        </div>

        {user ? (
          /* '내 프로필' 자리다 — 목적지 글자 줄에 같은 항목을 또 두지
             않는다(사용자 요청). 카드가 있으면 그 카드를 작게 줄여
             보여주고, 없으면 닉네임 글자로 대신한다. 어느 쪽이든 누르면
             /me 로 가고, 카드 아래에 무엇인지 적어 둔다 — 카드만 있으면
             눌러 보기 전엔 어디로 가는지 알 수 없다. */
          <Link href="/me" className="ss-home-profile shrink-0">
            {card ? (
              <span className="ss-pcard-mini">
                <PlayerCardView card={card} />
              </span>
            ) : (
              <span style={{ color: 'var(--ss-fg)' }}>{user.nickname}</span>
            )}
            <span className="ss-home-profile-label">내 프로필</span>
          </Link>
        ) : (
          <div className="flex shrink-0 items-center gap-1">
            <Link href="/login" className={`${HEADER_LINK_CLASS} ${HEADER_LINK_HOVER_CLASS}`} style={{ color: 'var(--ss-accent)' }}>
              로그인
            </Link>
            <Link href="/signup" className={`${HEADER_LINK_CLASS} ${HEADER_LINK_HOVER_CLASS}`} style={{ color: 'var(--ss-fg)' }}>
              회원가입
            </Link>
          </div>
        )}
      </div>

      {/* 헤드라인 · 보조 문구 · 정보 블록. 로그인 화면과 같은 문구를 쓴다 —
          두 화면이 한 목소리로 들리게. */}
      <div className="ss-home-stage" style={{ padding: 'var(--ss-home-content-pad)' }}>
        <div className="flex items-start justify-between gap-8">
          {/* 왼쪽 — 두 줄짜리 그리드. 둘째 줄이 윗줄 **두 번째 낱말의 둘째
              글자** 자리에서 시작한다(사용자 요청). 그래서 그 낱말을
              첫 글자와 나머지로 쪼개 3열(FIND | Y | OUR)에 앉히고, 둘째
              줄은 앞 두 칸을 비워 셋째 칸에 온다 — 눈대중 여백 없이
              layout 이 자리를 맞춘다.

              🔴 자리와 글자는 따로 논다. 좌우를 맞바꿀 때 덩어리째 옮기지
              않고 **글자만** 옮겼다 — 각 자리의 짜임(왼쪽은 이 그리드,
              오른쪽은 계단)은 그대로 두라는 요청이었다.

              낱말이 각자 span 이라 사이에 공백 문자가 없다 — 그냥 두면
              접근성 이름이 "FINDYOURSQUAD" 로 붙어 읽힌다. 이름을 따로 준다. */}
          <h1 className="ss-home-display ss-home-headline" aria-label="FIND YOUR SQUAD">
            <span className="ss-home-headline-first">FIND</span>
            <span>Y</span>
            <span>OUR</span>
            <span className="ss-home-headline-second">SQUAD</span>
          </h1>

          {/* 오른쪽 — 왼쪽과 같은 글꼴 · 같은 크기(ss-home-display)로 세 줄.
              줄이 내려갈수록 시작점이 조금씩 오른쪽으로 밀린다(계단).
              여기도 낱말이 각자 span 이라 이름을 따로 준다. */}
          <p className="ss-home-display ss-home-subhead" aria-label="OWN THE PITCH">
            <span>OWN</span>
            <span>THE</span>
            <span>PITCH</span>
          </p>
        </div>
      </div>

      {/* 오른쪽 아래 구석 — 로그아웃 아이콘 하나. 여기 있던 01~05 번호
          목록은 지웠다(상단 글자 내비와 같은 목록이라 두 벌이었다). */}
      {user && (
        <div className="ss-home-footer">
          <LogoutButton />
        </div>
      )}
    </>
  )
}
