'use client'

import { useRef, type CSSProperties } from 'react'
import BrandMark from '@/components/ui/BrandMark'
import DestinationCard from '@/components/DestinationCard'
import FigureBackground from '@/components/FigureBackground'
import LogoutButton from '@/components/LogoutButton'
import PillButton from '@/components/ui/PillButton'
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
 * (입체감)를 낸다. 뒤 → 앞으로 갈수록 크게 움직인다: 배경 < 워드마크 ·
 * 인사말 < 카드 캐러셀. 실제 로직(보간 · rAF · reduced-motion/터치 예외)은
 * `useMouseParallax` 가 맡는다.
 *
 * 배율은 화면에서 마우스를 끝에서 끝까지 움직여 보며 눈으로 정했다: 가장
 * 크게 움직이는 카드 층도 최대 {@link FRONT_STRENGTH}px 를 넘지 않는다
 * (요청한 "10~20px 상한" 안에서, 시차가 보이되 멀미 나지 않는 지점).
 * 배경은 그 1/5 이하로 — "거의 안 움직이는" 정도로만 흔들린다.
 *
 * 카드 캐러셀은 같은 층(frontRef)에 두 가지가 동시에 걸려 있다: 이
 * `useMouseParallax` 는 `transform` 으로 박스 전체를 살짝 흔들고,
 * `useCarouselFlow` 는 그 안의 `scrollLeft` 로 카드 줄을 흐르게 한다.
 * 서로 다른 CSS 속성이라 부딪히지 않는다(자세한 이유는
 * `lib/useCarouselFlow.ts` 코멘트).
 *
 * `page.tsx`(서버 컴포넌트)는 이 컴포넌트를 감싸기만 하고, 마우스가 필요한
 * 화면(인사말 · 카드)은 여기로 prop 으로 내려받는다. `/` 는 로그인 여부와
 * 무관하게 항상 이 화면이다 — `user` 가 있으면 닉네임 + 로그아웃을, 없으면
 * 로그인 · 회원가입 버튼을 인사말 자리에 보여준다.
 */
const BACKGROUND_STRENGTH = 3
const MID_STRENGTH = 7
const FRONT_STRENGTH = 14

// 캐러셀 무한 루프 — 카드 목록을 이만큼 이어붙이고 가운데 벌에서
// 시작한다. 3벌이면 앞뒤로 한 벌씩 버퍼가 생겨 마우스를 어느 쪽으로
// 옮기든(왼쪽으로 계속/오른쪽으로 계속) 진짜 스크롤 끝(clamp)에 닿기 전에
// `useCarouselFlow` 가 항상 한 벌 폭만큼 티 안 나게 되돌린다.
const LOOP_COPIES = 3
const REAL_COPY_INDEX = 1 // 스크린리더 · 탭 순서에 걸리는 "진짜" 한 벌 — 시작 위치와 같은 가운데 벌.

export default function HomeParallax({
  user,
  destinations,
}: {
  user: { nickname: string } | null
  destinations: Destination[]
}) {
  const bgRef = useRef<HTMLDivElement>(null)
  const midRef = useRef<HTMLDivElement>(null)
  const frontRef = useRef<HTMLDivElement>(null)

  useMouseParallax([
    { ref: bgRef, strength: BACKGROUND_STRENGTH },
    { ref: midRef, strength: MID_STRENGTH },
    { ref: frontRef, strength: FRONT_STRENGTH },
  ])
  useCarouselFlow(frontRef, LOOP_COPIES)

  const looped = Array.from({ length: LOOP_COPIES }, (_, copy) =>
    destinations.map((d, i) => ({ ...d, copy, i, real: copy === REAL_COPY_INDEX })),
  ).flat()

  return (
    <>
      <FigureBackground ref={bgRef} />

      {/* 헤더 — 워드마크 좌상단, 인사말 우상단. 화면에 고정해 캐러셀이
          가로로 얼마나 흐르든 그 자리에 그대로 있는다. 글래스 테두리
          판(--ss-frame-*) 두께 + 여백만큼 안쪽으로 들여야 판에 안 가린다. */}
      <div
        ref={midRef}
        className="fixed inset-x-0 top-0 z-20 flex items-start justify-between"
        style={{ padding: 'var(--ss-frame-content-pad)', willChange: 'transform' }}
      >
        <BrandMark size={26} />
        {user ? (
          <div className="flex items-center gap-3">
            <p className="text-sm font-medium" style={{ color: 'var(--ss-fg)' }}>
              {user.nickname}
            </p>
            <LogoutButton />
          </div>
        ) : (
          <div className="flex flex-wrap justify-end gap-3">
            <PillButton href="/login">로그인</PillButton>
            <PillButton href="/signup" variant="ghost">
              회원가입
            </PillButton>
          </div>
        )}
      </div>

      {/* 카드 캐러셀 — 화면 아래쪽에 깔고, 가로로 무한히 흐른다. 위쪽은
          지금은 비워 둔다(참고 디자인처럼 나중에 소개 문구가 들어갈
          자리). 아래쪽 여백은 글래스 테두리 판(--ss-frame-content-pad,
          48px)에 안 가리도록 최소 확보하고, 로그인 상태면 하단
          내비바(FloatingNavBar, 실측 높이 80px)에도 안 가리게 그만큼
          더 띄운다. */}
      <div
        className="relative flex min-h-screen w-full items-end"
        style={{ paddingBottom: user ? 'calc(var(--ss-frame-content-pad) + 80px)' : 'var(--ss-frame-content-pad)' }}
      >
        <div ref={frontRef} className="ss-carousel w-full" style={{ willChange: 'transform' }}>
          <div className="ss-carousel-track">
            {looped.map(({ copy, i, real, ...d }) => (
              <div
                key={`${copy}-${d.title}`}
                className="ss-carousel-item"
                aria-hidden={real ? undefined : true}
                style={
                  {
                    // 계단처럼 규칙적으로 어긋나게 — 짝수 번째는 위로, 홀수
                    // 번째는 아래로. 복제본도 원본과 같은 i(0~5) 를 쓰므로
                    // 루프 이음매에서도 어긋남 패턴이 똑같이 이어진다.
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
                  tabIndex={real ? undefined : -1}
                />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 화면을 감싸는 글래스 테두리 판 — 클릭을 막으면 안 되므로
          pointer-events: none (CSS, .ss-frame). 장식일 뿐이라 스크린리더에서 숨긴다. */}
      <div aria-hidden="true" className="ss-frame" />
    </>
  )
}
