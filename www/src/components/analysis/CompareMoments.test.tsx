import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { kickMotion } from '@/lib/motion/kickFixture'
import { detectMoments } from '@/lib/motion/moments'
import CompareMoments from './CompareMoments'

function analyzed(dir: 1 | -1 = 1) {
  const motion = kickMotion({ dir })
  const r = detectMoments(motion)
  if (!r.ok) throw new Error(r.reason)
  return { motion, moments: r.moments }
}

function renderIt(over: Partial<Parameters<typeof CompareMoments>[0]> = {}) {
  const props = {
    playerName: '에스테반 로벨리',
    player: analyzed(),
    user: analyzed(),
    mirrored: false,
    onToggleMirror: vi.fn(),
    selected: null,
    onSelect: vi.fn(),
    ...over,
  }
  render(<CompareMoments {...props} />)
  return props
}

describe('세 순간 카드', () => {
  it('직전 · 임팩트 · +1초 셋을 차례대로 그린다', () => {
    renderIt()
    const group = screen.getByRole('group', { name: '세 순간 비교' })
    const cards = group.querySelectorAll('.ss-shot-moment')
    expect([...cards].map((c) => c.getAttribute('data-moment'))).toEqual(['before', 'impact', 'after'])
  })

  it('카드마다 선수(하늘) · 나(초록) 뼈대를 겹쳐 그린다', () => {
    const { container } = render(
      <CompareMoments
        playerName="에스테반 로벨리"
        player={analyzed()}
        user={analyzed()}
        mirrored={false}
        onToggleMirror={() => {}}
        selected={null}
        onSelect={() => {}}
      />,
    )
    const impact = container.querySelector('[data-moment="impact"]')!
    expect(impact.querySelector('.ss-shot-moment-pro')?.getAttribute('d')).toMatch(/^M/)
    expect(impact.querySelector('.ss-shot-moment-me')?.getAttribute('d')).toMatch(/^M/)
  })

  it('누르면 그 순간을 알리고, 고른 카드는 눌린 상태다', async () => {
    const props = renderIt({ selected: 'impact' })
    expect(screen.getByRole('button', { name: /^임팩트/ })).toHaveAttribute('aria-pressed', 'true')
    await userEvent.click(screen.getByRole('button', { name: /^직전/ }))
    expect(props.onSelect).toHaveBeenCalledWith('before')
  })

  it('첫 항목의 두 값을 선수 / 나 차례로 적는다', () => {
    renderIt()
    expect(screen.getByRole('button', { name: /^임팩트/ })).toHaveTextContent('디딤발 무릎 굽히기 160° / 160°')
  })

  // 「브라우저에서 잰 값」 표기는 뺐다(사용자 요청, 2026-09-15). 데모 영상 출처는 라이선스상 남긴다.
  it('반전 토글과 데모 영상 표기가 있다', async () => {
    const props = renderIt({ mirrored: true })
    const flip = screen.getByRole('button', { name: /좌우 반전/ })
    expect(flip).toHaveAttribute('aria-pressed', 'true')
    await userEvent.click(flip)
    expect(props.onToggleMirror).toHaveBeenCalled()
    expect(screen.getByText('데모 영상(Pexels)')).toBeInTheDocument()
    expect(screen.queryByText(/브라우저에서 잰 값/)).toBeNull()
  })

  it('+1초가 영상 끝으로 대신됐으면 적는다', () => {
    const motion = kickMotion({ frames: 20 })
    const r = detectMoments(motion)
    if (!r.ok) throw new Error(r.reason)
    renderIt({ user: { motion, moments: r.moments } })
    expect(screen.getByRole('button', { name: /^\+1초 · 영상 끝/ })).toBeInTheDocument()
  })
})
