import Link from 'next/link'
import BrandMark from '@/components/ui/BrandMark'

// 로그인 전용 화면(analysis/, me/) 셸 — 이 그룹의 페이지는 모두 requireUser()
// 로 이미 로그인이 보장돼 있다. `/`(홈)는 이 그룹 밖에 있다.
//
// 하단 내비바(FloatingNavBar)는 2026-08-30 에 없앴다 — 홈이 상단 글자
// 내비를 갖게 되면서 홈에서는 같은 목적지가 두 벌이 됐다. 다만 이 그룹의
// 화면에는 그 글자 내비가 없어서, 바까지 빼면 홈으로 돌아갈 길이 사라진다.
// 그래서 워드마크만 남긴다 — 홈 헤더의 왼쪽 위와 같은 자리 · 같은 크기다.
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <div
        className="fixed inset-x-0 top-0 z-20 flex items-start"
        style={{ padding: 'var(--ss-home-content-pad)' }}
      >
        <Link href="/" aria-label="홈">
          <BrandMark size={26} />
        </Link>
      </div>
      <div className="mx-auto max-w-[1120px] px-6 pb-32">{children}</div>
    </>
  )
}
