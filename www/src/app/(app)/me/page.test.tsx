import { render, screen } from '@testing-library/react'
import type { PlayerCard, User } from '@/server/backend'
import { MeBody } from './page'

// NicknameForm 이 useRouter 를 쓴다.
vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}))

const USER: User = {
  id: 'u1',
  email: 'demo@super-sub.example',
  nickname: '홍길동',
  created_at: '2026-08-30T00:00:00Z',
  teams: [],
}

const CARD: PlayerCard = {
  id: 'c1',
  public_slug: 'hong-gildong',
  og_image_key: 'og/hong-gildong.png',
  user: { id: 'u1', nickname: '홍길동' },
  titles: [],
}

describe('내 프로필 — /me', () => {
  it('닉네임과 이메일을 보여준다', () => {
    render(<MeBody user={USER} card={null} />)
    expect(screen.getByRole('heading', { name: '홍길동' })).toBeInTheDocument()
    expect(screen.getByText('demo@super-sub.example')).toBeInTheDocument()
  })

  // /me/card 를 이 화면으로 합쳤다 — 선수 카드를 보러 다른 데로 보내지 않는다.
  it('선수 카드가 있으면 이 화면에 바로 그리고 공유 링크를 보여준다', () => {
    render(<MeBody user={USER} card={CARD} />)
    expect(screen.getByText('호칭')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '/c/hong-gildong' })).toHaveAttribute(
      'href',
      '/c/hong-gildong',
    )
  })

  it('선수 카드가 없으면 아직 없다고 알려준다', () => {
    render(<MeBody user={USER} card={null} />)
    expect(screen.getByText('아직 선수 카드가 없습니다')).toBeInTheDocument()
  })

  it('선수 카드를 보러 다른 페이지로 보내는 링크가 없다 — 여기가 그 자리다', () => {
    render(<MeBody user={USER} card={CARD} />)
    expect(screen.queryByRole('link', { name: /내 선수 카드 보기/ })).toBeNull()
    const toCard = screen
      .queryAllByRole('link')
      .filter((a) => a.getAttribute('href') === '/me/card')
    expect(toCard).toHaveLength(0)
  })
})
