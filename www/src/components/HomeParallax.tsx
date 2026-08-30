'use client'

import Link from 'next/link'
import { useRef, useState } from 'react'
import BrandMark from '@/components/ui/BrandMark'
import FigureBackground from '@/components/FigureBackground'
import HomeIndexList from '@/components/HomeIndexList'
import HomeNav, { type Destination } from '@/components/HomeNav'
import LogoutButton, { HEADER_LINK_CLASS, HEADER_LINK_HOVER_CLASS } from '@/components/LogoutButton'
import { useMouseParallax } from '@/lib/useMouseParallax'

export type { Destination }

/**
 * 홈 한 화면 — 배경 사진 위에 글자를 얹는 레퍼런스(Nile Travel) 배치다.
 *
 *   워드마크        영상분석 용병매칭 …        닉네임 로그아웃
 *   헤드라인(큰 글자)                          보조 문구
 *   정보 블록 3열
 *   SCROLL DOWN  소셜                          01~06 번호 목록
 *
 * 예전에는 화면 아래에 카드 6장이 가로로 흐르는 캐러셀이 있었다. 카드가
 * 배경 사진을 절반 넘게 가려서, 목적지는 위쪽 **글자**로만 적고 카드는
 * 그 글자를 가리켰을 때만 아래로 떠오르게 바꿨다(`HomeNav`).
 *
 * 지금 가리킨 목적지(`active`)를 여기서 쥔다 — 위쪽 글자와 우하단 번호
 * 목록이 **같은 항목을 같이 밝혀야** 해서다(레퍼런스에서 04 번이 그렇다).
 * 어느 쪽에 마우스를 올려도 반대쪽이 따라 밝아진다.
 *
 * 마우스를 따라 요소를 아주 미세하게 움직여 시차(입체감)를 낸다. 배경
 * 사진은 고정 — 사용자 요청("배경 사진은 안 움직이게 하자")으로 시차를
 * 걷어냈다. 뒤(헤더) → 앞(헤드라인)으로 갈수록 크게 움직인다. 배율은
 * 화면에서 마우스를 끝에서 끝까지 움직여 보며 눈으로 정했다: 가장 크게
 * 움직이는 층도 {@link FRONT_STRENGTH}px 를 넘지 않는다(요청한 "10~20px
 * 상한" 안에서, 시차가 보이되 멀미 나지 않는 지점). 실제 로직(보간 · rAF ·
 * reduced-motion/터치 예외)은 `useMouseParallax` 가 맡는다.
 *
 * `page.tsx`(서버 컴포넌트)는 이 컴포넌트를 감싸기만 하고, 마우스가 필요한
 * 부분은 여기로 prop 으로 내려받는다.
 */
const MID_STRENGTH = 7
const FRONT_STRENGTH = 14

// 레퍼런스의 `Meeting Point / Price / Duration` 자리. 아직 없는 기능을
// 있는 것처럼 적지 않는다 — 세 번째 칸은 준비 중인 목적지를 그대로 적는다.
const INFO_BLOCKS = [
  { heading: '시작하기', body: '영상 한 편이면 됩니다\n올린 뒤 기다리면 됩니다' },
  { heading: '무엇이 나오나', body: '점수가 아니라 호칭입니다\n잘한 것에 이름을 붙입니다' },
  { heading: '준비 중', body: '용병 매칭 · 내 팀\n레슨 · 상점 · 경기장 예약' },
]

const SOCIALS = ['FACEBOOK', 'INSTAGRAM', 'TIKTOK']

export default function HomeParallax({
  user,
  destinations,
}: {
  user: { nickname: string } | null
  destinations: Destination[]
}) {
  const midRef = useRef<HTMLDivElement>(null)
  const frontRef = useRef<HTMLDivElement>(null)
  const [active, setActive] = useState<string | null>(null)

  useMouseParallax([
    { ref: midRef, strength: MID_STRENGTH },
    { ref: frontRef, strength: FRONT_STRENGTH },
  ])

  return (
    <>
      <FigureBackground />

      {/* 헤더 — 워드마크 · 목적지 글자 · 인사말. 화면에 고정한다. */}
      <div
        ref={midRef}
        className="fixed inset-x-0 top-0 z-20 flex items-start justify-between gap-8"
        style={{ padding: 'var(--ss-home-content-pad)', willChange: 'transform' }}
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
          <div className="flex shrink-0 items-center gap-1">
            <span className={HEADER_LINK_CLASS} style={{ color: 'var(--ss-fg)' }}>
              {user.nickname}
            </span>
            <LogoutButton />
          </div>
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
      <div
        ref={frontRef}
        className="ss-home-stage"
        style={{ padding: 'var(--ss-home-content-pad)', willChange: 'transform' }}
      >
        <div className="flex items-start justify-between gap-8">
          <h1 className="ss-home-headline">
            안개 속에서도,
            <br />
            실력은
            <br />
            숨지 않습니다.
          </h1>
          <p className="ss-home-meta">
            생활체육 경기 영상 분석
            <br />
            용병 스카우팅 &amp; 실력 검증
          </p>
        </div>

        <dl className="ss-home-info">
          {INFO_BLOCKS.map((b) => (
            <div key={b.heading}>
              <dt>{b.heading}</dt>
              <dd>{b.body}</dd>
            </div>
          ))}
        </dl>
      </div>

      {/* 하단 줄 — 가운데는 비워 둔다(로그인했으면 FloatingNavBar 가 그 자리). */}
      <div className="ss-home-footer">
        <div className="ss-home-footer-left">
          <span className="ss-home-scroll">
            SCROLL DOWN <span aria-hidden="true">↓</span>
          </span>
          <ul className="ss-home-socials">
            {SOCIALS.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>

        <HomeIndexList destinations={destinations} active={active} onActivate={setActive} />
      </div>
    </>
  )
}
