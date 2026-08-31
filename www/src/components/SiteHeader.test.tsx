import { render, screen } from '@testing-library/react'
import SiteHeader from './SiteHeader'
import type { Destination } from './HomeNav'

const pathname = vi.fn(() => '/')
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => pathname(),
}))

const DESTINATIONS: Destination[] = [
  { title: '영상 분석', icon: 'camera_video', summary: '경기 영상을 올리면', href: '/analysis' },
  { title: '레슨 · 상점', icon: 'add_business', summary: '제휴 코치와 장비를' },
]

describe('화면 맨 위 줄', () => {
  it('모든 목적지를 적는다', () => {
    pathname.mockReturnValue('/')
    render(<SiteHeader user={{ nickname: '홍길동' }} destinations={DESTINATIONS} />)
    expect(screen.getByRole('button', { name: '영상 분석' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '레슨 · 상점' })).toBeInTheDocument()
  })

  // 🔴 눌러도 제자리인 글자를 남겨 두면 "안 눌린다"로 읽힌다.
  it('지금 보고 있는 화면은 목적지에서 뺀다', () => {
    pathname.mockReturnValue('/analysis')
    render(<SiteHeader user={{ nickname: '홍길동' }} destinations={DESTINATIONS} />)
    expect(screen.queryByRole('button', { name: '영상 분석' })).toBeNull()
    expect(screen.getByRole('button', { name: '레슨 · 상점' })).toBeInTheDocument()
  })
})
