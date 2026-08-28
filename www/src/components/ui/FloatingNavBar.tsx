'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import BrandMark from './BrandMark'
import GlassPanel from './GlassPanel'

type NavItem = {
  href: string
  label: string
  icon: string
}

// 앱(flutter/lib/core/widgets/floating_nav_bar.dart)과 같은 목적지 · 같은 글리프.
const NAV_ITEMS: NavItem[] = [
  { href: '/home', label: '홈', icon: 'sports_soccer' },
  { href: '/analysis', label: '영상 분석', icon: 'videocam' },
  { href: '/me/card', label: '내 선수 카드', icon: 'id_card' },
  { href: '/me', label: '내 프로필', icon: 'person' },
]

export default function FloatingNavBar() {
  const pathname = usePathname()

  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 flex justify-center px-4 pb-6">
      <GlassPanel className="flex w-full max-w-[560px] items-center gap-2 px-3 py-2">
        <BrandMark size={22} className="shrink-0 px-2" />
        <ul className="flex flex-1 items-center justify-evenly">
          {NAV_ITEMS.map((item) => {
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
