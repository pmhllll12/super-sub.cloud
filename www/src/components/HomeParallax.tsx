'use client'

import Link from 'next/link'
import { useRef, type CSSProperties } from 'react'
import BrandMark from '@/components/ui/BrandMark'
import DestinationCard from '@/components/DestinationCard'
import FigureBackground from '@/components/FigureBackground'
import LogoutButton, { HEADER_LINK_CLASS, HEADER_LINK_HOVER_CLASS } from '@/components/LogoutButton'
import { useCarouselFlow } from '@/lib/useCarouselFlow'
import { useMouseParallax } from '@/lib/useMouseParallax'

export type Destination = {
  title: string
  icon: string
  summary: string
  href?: string
  /** 이 목적지가 결국 requireUser() 에 걸리는 로그인 전용 경로인가 — 로그인
   *  안 한 사람에게는 "로그인이 필요합니다" 안내를 보여준다(링크 자체는
   *  살려 둔다, 눌러야 /login 으로 보내는 지금 방식 그대로). */
  authRequired?: boolean
}

/**
 * 배경 사진 위에 얹힌 요소들을 마우스를 따라 아주 미세하게 움직여 시차
 * (입체감)를 낸다. 배경 사진은 고정 — 사용자 요청("배경 사진은 안
 * 움직이게 하자")으로 시차를 걷어냈다. 워드마크 · 인사말과 카드
 * 캐러셀만 움직인다: 뒤(워드마크 · 인사말) → 앞(카드)으로 갈수록 크게.
 * 배경이 고정이라 오히려 이 두 층이 그 위에 떠 있는 느낌이 산다.
 * 실제 로직(보간 · rAF · reduced-motion/터치 예외)은 `useMouseParallax`
 * 가 맡는다.
 *
 * 배율은 화면에서 마우스를 끝에서 끝까지 움직여 보며 눈으로 정했다: 가장
 * 크게 움직이는 카드 층도 최대 {@link FRONT_STRENGTH}px 를 넘지 않는다
 * (요청한 "10~20px 상한" 안에서, 시차가 보이되 멀미 나지 않는 지점).
 *
 * 카드 캐러셀은 같은 층(frontRef)에 두 가지가 동시에 걸려 있다: 이
 * `useMouseParallax` 는 `transform` 으로 박스 전체를 살짝 흔들고,
 * `useCarouselFlow` 는 그 안의 `scrollLeft` 로 카드 줄을 흐르게 한다.
 * 서로 다른 CSS 속성이라 부딪히지 않는다(자세한 이유는
 * `lib/useCarouselFlow.ts` 코멘트). 카드는 6장 한 벌뿐 — 무한 루프 없이
 * 양 끝에서 멈춘다.
 *
 * `page.tsx`(서버 컴포넌트)는 이 컴포넌트를 감싸기만 하고, 마우스가 필요한
 * 화면(인사말 · 카드)은 여기로 prop 으로 내려받는다. `/` 는 로그인 여부와
 * 무관하게 항상 이 화면이다 — `user` 가 있으면 닉네임 + 로그아웃을, 없으면
 * 로그인 · 회원가입 버튼을 인사말 자리에 보여준다.
 */
const MID_STRENGTH = 7
const FRONT_STRENGTH = 14

export default function HomeParallax({
  user,
  destinations,
}: {
  user: { nickname: string } | null
  destinations: Destination[]
}) {
  const midRef = useRef<HTMLDivElement>(null)
  const frontRef = useRef<HTMLDivElement>(null)

  useMouseParallax([
    { ref: midRef, strength: MID_STRENGTH },
    { ref: frontRef, strength: FRONT_STRENGTH },
  ])
  useCarouselFlow(frontRef)

  return (
    <>
      <FigureBackground />

      {/* 헤더 — 워드마크 좌상단, 인사말 우상단. 화면에 고정해 캐러셀이
          가로로 얼마나 흐르든 그 자리에 그대로 있는다. 뷰포트 가장자리에
          붙지 않도록 --ss-home-content-pad 만큼 안쪽으로 들인다. */}
      <div
        ref={midRef}
        className="fixed inset-x-0 top-0 z-20 flex items-start justify-between"
        style={{ padding: 'var(--ss-home-content-pad)', willChange: 'transform' }}
      >
        <BrandMark size={26} />
        {user ? (
          <div className="flex items-center gap-1">
            <span className={HEADER_LINK_CLASS} style={{ color: 'var(--ss-fg)' }}>
              {user.nickname}
            </span>
            <LogoutButton />
          </div>
        ) : (
          <div className="flex items-center gap-1">
            <Link href="/login" className={`${HEADER_LINK_CLASS} ${HEADER_LINK_HOVER_CLASS}`} style={{ color: 'var(--ss-accent)' }}>
              로그인
            </Link>
            <Link href="/signup" className={`${HEADER_LINK_CLASS} ${HEADER_LINK_HOVER_CLASS}`} style={{ color: 'var(--ss-fg)' }}>
              회원가입
            </Link>
          </div>
        )}
      </div>

      {/* 카드 캐러셀 — 화면 아래쪽에 깔고, 가로로 흐른다(6장 한 벌, 양
          끝에서 멈춤). 위쪽은 지금은 비워 둔다(참고 디자인처럼 나중에
          소개 문구가 들어갈 자리). 좌우 padding(--ss-home-content-pad)은
          캐러셀 자신의 스크롤 뷰포트를 그만큼 안쪽에서 시작·끝나게 한다 —
          카드가 이 뷰포트 밖으로는 애초에 그려지지 않는다(overflow-x:
          auto 가 자신의 박스 기준으로 자른다). 로그인 상태면 하단
          내비바(FloatingNavBar, 실측 높이 80px)에 안 가리게 아래쪽을
          그만큼 더 띄운다. */}
      <div
        className="relative z-10 flex min-h-screen w-full items-end"
        style={{
          paddingBottom: user ? 'calc(var(--ss-home-content-pad) + 80px)' : 'var(--ss-home-content-pad)',
          paddingLeft: 'var(--ss-home-content-pad)',
          paddingRight: 'var(--ss-home-content-pad)',
        }}
      >
        <div ref={frontRef} className="ss-carousel w-full" style={{ willChange: 'transform' }}>
          <div className="ss-carousel-track">
            {destinations.map((d, i) => (
              <div
                key={d.title}
                className="ss-carousel-item"
                style={
                  {
                    // 계단처럼 규칙적으로 어긋나게 — 짝수 번째는 위로, 홀수 번째는 아래로.
                    '--ss-card-offset':
                      i % 2 === 0 ? 'calc(var(--ss-card-stagger) * -1)' : 'var(--ss-card-stagger)',
                  } as CSSProperties
                }
              >
                <DestinationCard
                  title={d.title}
                  icon={d.icon}
                  summary={d.summary}
                  href={d.href}
                  phase={i * 0.13}
                  locked={Boolean(d.authRequired) && !user}
                />
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  )
}
