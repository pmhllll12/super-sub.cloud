'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import BrandMark from './BrandMark'
import GlassPanel from './GlassPanel'

type NavLink = {
  href: string
  label: string
  icon: string
  disabled?: false
}

type NavDisabled = {
  href?: undefined
  label: string
  icon: string
  disabled: true
}

type NavEntry = NavLink | NavDisabled

// 앱(flutter/lib/core/widgets/floating_nav_bar.dart)과 같은 글리프 · 같은 뜻.
// sports_soccer 는 앱에서도 "축구·매칭"을 가리키므로 홈에 쓰지 않는다 — 아직 준비 중인 자리.
const NAV_ITEMS: NavEntry[] = [
  { href: '/analysis', label: '영상 분석', icon: 'videocam' },
  { label: '용병 매칭 (준비 중)', icon: 'sports_soccer', disabled: true },
  { href: '/me/card', label: '내 선수 카드', icon: 'id_card' },
  { href: '/me', label: '내 프로필', icon: 'person' },
]

export default function FloatingNavBar() {
  const pathname = usePathname()
  const homeActive = pathname === '/home'

  return (
    // inset-x-0 로 뷰포트 전체 폭을 차지하므로, 알약 바깥의 빈 공간은 클릭을 그냥 통과시킨다.
    // 알약 안쪽에서만 pointer-events-auto 로 되돌린다.
    <nav className="pointer-events-none fixed inset-x-0 bottom-0 z-40 flex justify-center px-4 pb-6">
      <GlassPanel className="pointer-events-auto flex w-full max-w-[560px] items-center gap-2 px-3 py-2">
        <Link
          href="/home"
          aria-label="홈"
          aria-current={homeActive ? 'page' : undefined}
          className="flex shrink-0 items-center px-2"
        >
          <BrandMark size={22} />
        </Link>
        <ul className="flex flex-1 items-center justify-evenly">
          {NAV_ITEMS.map((item) => {
            if (item.disabled) {
              return (
                <li key={item.label}>
                  <button
                    type="button"
                    disabled
                    aria-label={item.label}
                    className="flex items-center justify-center p-2 opacity-40"
                    style={{ color: 'var(--ss-fg)' }}
                  >
                    <span className="material-symbols-outlined" aria-hidden="true">
                      {item.icon}
                    </span>
                  </button>
                </li>
              )
            }
            const active = pathname === item.href
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-label={item.label}
                  aria-current={active ? 'page' : undefined}
                  className="flex items-center justify-center p-2"
                  style={{ color: active ? 'var(--ss-accent)' : 'var(--ss-fg)' }}
                >
                  <span className="material-symbols-outlined" aria-hidden="true">
                    {item.icon}
                  </span>
                </Link>
              </li>
            )
          })}
        </ul>
      </GlassPanel>
    </nav>
  )
}
