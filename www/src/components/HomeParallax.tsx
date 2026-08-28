'use client'

import { useRef } from 'react'
import BrandMark from '@/components/ui/BrandMark'
import DestinationCard from '@/components/DestinationCard'
import FigureBackground from '@/components/FigureBackground'
import LogoutButton from '@/components/LogoutButton'
import PillButton from '@/components/ui/PillButton'
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
 * 인사말 < 목적지 카드. 실제 로직(보간 · rAF · reduced-motion/터치 예외)은
 * `useMouseParallax` 가 맡는다.
 *
 * 배율은 화면에서 마우스를 끝에서 끝까지 움직여 보며 눈으로 정했다: 가장
 * 크게 움직이는 카드 층도 최대 {@link FRONT_STRENGTH}px 를 넘지 않는다
 * (요청한 "10~20px 상한" 안에서, 시차가 보이되 멀미 나지 않는 지점).
 * 배경은 그 1/5 이하로 — "거의 안 움직이는" 정도로만 흔들린다.
 *
 * `page.tsx`(서버 컴포넌트)는 이 컴포넌트를 감싸기만 하고, 마우스가 필요한
 * 화면(인사말 · 목적지 목록)은 여기로 prop 으로 내려받는다. `/` 는 로그인
 * 여부와 무관하게 항상 이 화면이다 — `user` 가 있으면 닉네임 + 로그아웃을,
 * 없으면 로그인 · 회원가입 버튼을 인사말 자리에 보여준다.
 */
const BACKGROUND_STRENGTH = 3
const MID_STRENGTH = 7
const FRONT_STRENGTH = 14

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

  return (
    <>
      <FigureBackground ref={bgRef} />
      <div
        ref={midRef}
        className="flex flex-col items-center gap-10"
        style={{ willChange: 'transform' }}
      >
        <BrandMark />
        {user ? (
          <div className="flex flex-col items-center gap-2">
            <p className="text-lg font-medium" style={{ color: 'var(--ss-fg)' }}>
              {user.nickname}
            </p>
            <LogoutButton />
          </div>
        ) : (
          <div className="flex flex-wrap justify-center gap-3">
            <PillButton href="/login">로그인</PillButton>
            <PillButton href="/signup" variant="ghost">
              회원가입
            </PillButton>
          </div>
        )}
      </div>
      <div
        ref={frontRef}
        className="grid w-full grid-cols-2 gap-3"
        style={{ willChange: 'transform' }}
      >
        {destinations.map((d, i) => (
          <DestinationCard
            key={d.title}
            title={d.title}
            icon={d.icon}
            summary={d.summary}
            href={d.href}
            phase={i * 0.13}
            locked={Boolean(d.authRequired) && !user}
          />
        ))}
      </div>
    </>
  )
}
