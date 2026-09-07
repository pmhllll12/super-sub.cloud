import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { PlayerCard } from '@/server/backend'
import { CardStyleProvider, DEFAULT_CARD_STYLE } from './cardStyle'
import { loadCardStyle, saveCardStyle } from './cardStyleStore'
import CardEditor from './CardEditor'

vi.mock('next/navigation', () => ({ useRouter: () => ({ refresh: () => {} }) }))

const CARD: PlayerCard = {
  id: 'c1',
  public_slug: 'hong-gildong-4f2a',
  og_image_key: 'og/hong-gildong.png',
  user: { id: 'u1', nickname: '홍길동' },
  titles: [],
}

function open() {
  return render(
    <CardStyleProvider>
      <CardEditor card={CARD} />
    </CardStyleProvider>,
  )
}

beforeEach(() => localStorage.clear())

describe('카드 꾸미기 — 되돌리기와 저장', () => {
  it('되돌리는 단추 이름은 「초기화」다', () => {
    open()
    expect(screen.getByRole('button', { name: '초기화' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '처음 모습으로' })).toBeNull()
  })

  it('그 옆에 저장 단추가 있다', () => {
    open()
    expect(screen.getByRole('button', { name: '저장' })).toBeInTheDocument()
  })

  it('저장을 누르면 지금 값이 저장된다', async () => {
    const user = userEvent.setup()
    open()
    const text = screen.getByLabelText('카드에 넣을 글자')
    await user.clear(text)
    await user.type(text, '세 개의 폐')
    await user.click(screen.getByRole('button', { name: '저장' }))
    await waitFor(() => expect(loadCardStyle(DEFAULT_CARD_STYLE)?.text).toBe('세 개의 폐'))
  })

  // 저장이 됐는지 화면이 말하지 않으면 눌렀는지조차 알 수 없다.
  it('저장하면 알려 준다', async () => {
    const user = userEvent.setup()
    open()
    await user.click(screen.getByRole('button', { name: '저장' }))
    expect(await screen.findByRole('status')).toHaveTextContent('저장')
  })

  /**
   * 🔴 사진(data URL)이 크면 저장소 한도를 넘는다. **조용히 성공한 척하면**
   * 다시 열었을 때 사라져 있어서 사용자는 이유를 알 수 없다.
   */
  it('저장하지 못하면 그렇게 알려 준다', async () => {
    vi.stubGlobal('localStorage', {
      getItem: () => null,
      setItem() {
        throw new Error('QuotaExceededError')
      },
    })
    const user = userEvent.setup()
    open()
    await user.click(screen.getByRole('button', { name: '저장' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('저장하지')
    vi.unstubAllGlobals()
  })

  // 저장해 둔 것이 있으면 그것으로 시작해야 저장이 뜻을 갖는다.
  it('저장해 둔 값이 있으면 그 값으로 연다', async () => {
    saveCardStyle({ ...DEFAULT_CARD_STYLE, text: '지난번 것' })
    open()
    await waitFor(() =>
      expect(screen.getByLabelText('카드에 넣을 글자')).toHaveValue('지난번 것'),
    )
  })

  // 초기화는 화면의 값만 되돌린다 — 되돌린 뒤 저장해야 저장본도 바뀐다.
  it('초기화해도 저장해 둔 것은 그대로다', async () => {
    saveCardStyle({ ...DEFAULT_CARD_STYLE, text: '지난번 것' })
    const user = userEvent.setup()
    open()
    await waitFor(() =>
      expect(screen.getByLabelText('카드에 넣을 글자')).toHaveValue('지난번 것'),
    )
    await user.click(screen.getByRole('button', { name: '초기화' }))
    expect(screen.getByLabelText('카드에 넣을 글자')).toHaveValue(DEFAULT_CARD_STYLE.text)
    expect(loadCardStyle(DEFAULT_CARD_STYLE)?.text).toBe('지난번 것')
  })
})
