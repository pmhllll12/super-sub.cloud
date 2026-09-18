import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { PlayerCard } from '@/server/backend'
import { CardStyleProvider, DEFAULT_CARD_STYLE } from './cardStyle'
import CardEditor from './CardEditor'

vi.mock('next/navigation', () => ({ useRouter: () => ({ refresh: () => {} }) }))

const CARD: PlayerCard = {
  id: 'c1',
  public_slug: 'hong-gildong-4f2a',
  og_image_key: 'og/hong-gildong.png',
  user: { id: 'u1', nickname: '홍길동' },
  titles: [],
  tagline: null,
  style: null,
}

function open(card: PlayerCard = CARD) {
  return render(
    <CardStyleProvider card={card}>
      <CardEditor card={card} />
    </CardStyleProvider>,
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('카드 꾸미기 — 되돌리기와 저장', () => {
  /* 🔴 **글자를 안 쓰고 싶은 사람이 있다** (2026-09-18 사용자 요청). 지우고
     저장하면 지운 채로 남아야 하는데, 예전엔 다시 열 때마다 자리 표시가
     도로 채워져 **지울 방법이 없었다.** 칸에 적힌 `비우면 글자 없이` 가
     이미 그렇게 약속하고 있었고 동작만 안 따라갔다. */
  const SAVED = {
    bg: '#111111',
    logo: '#222222',
    text_color: '#333333',
    text_x: 50,
    text_y: 34,
    brush: 0,
    brush_color: '#0b0b0b',
    brush_scale: 1,
    brush_x: 0,
    brush_y: 0,
  }

  it('일부러 비워 둔 카드를 다시 열면 빈 칸으로 시작한다', () => {
    open({ ...CARD, tagline: null, style: SAVED })
    expect(screen.getByLabelText('카드에 넣을 글자')).toHaveValue('')
  })

  it('한 번도 안 꾸민 카드는 자리 표시로 시작한다', () => {
    open({ ...CARD, tagline: null, style: null })
    expect(screen.getByLabelText('카드에 넣을 글자')).toHaveValue('THREE LUNGS')
  })

  it('글자를 지우고 저장하면 tagline 을 null 로 보낸다', async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        new Response(JSON.stringify({ ...CARD, tagline: null }), { status: 200 }),
    )
    vi.stubGlobal('fetch', fetchMock)
    open({ ...CARD, tagline: '지난번 것', style: SAVED })

    await userEvent.clear(screen.getByLabelText('카드에 넣을 글자'))
    await userEvent.click(screen.getByRole('button', { name: '저장' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    const body = JSON.parse(String(fetchMock.mock.calls[0][1]!.body))
    // 🔴 빈 문자열이 아니라 `null` 이다 — 계약이 공백을 「안 정한 상태」로 본다.
    expect(body.tagline).toBeNull()
  })

  it('되돌리는 단추 이름은 「초기화」다', () => {
    open()
    expect(screen.getByRole('button', { name: '초기화' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '처음 모습으로' })).toBeNull()
  })

  it('그 옆에 저장 단추가 있다', () => {
    open()
    expect(screen.getByRole('button', { name: '저장' })).toBeInTheDocument()
  })

  // ✅ CCC 35 — 저장이 이제 서버로 간다(`PATCH /me/card`).
  it('저장을 누르면 tagline·style을 실어 PATCH /me/card 를 부른다', async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        new Response(JSON.stringify({ ...CARD, tagline: '세 개의 폐' }), { status: 200 }),
    )
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    open()
    const text = screen.getByLabelText('카드에 넣을 글자')
    await user.clear(text)
    await user.type(text, '세 개의 폐')
    await user.click(screen.getByRole('button', { name: '저장' }))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    const [url, init] = fetchMock.mock.calls[0]!
    expect(url).toBe('/api/me/card')
    expect((init as RequestInit).method).toBe('PATCH')
    const body = JSON.parse((init as RequestInit).body as string)
    expect(body.tagline).toBe('세 개의 폐')
    expect(body.style).toMatchObject({ bg: DEFAULT_CARD_STYLE.bg })
  })

  // 저장이 됐는지 화면이 말하지 않으면 눌렀는지조차 알 수 없다.
  it('저장하면 알려 준다', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(CARD), { status: 200 })))
    const user = userEvent.setup()
    open()
    await user.click(screen.getByRole('button', { name: '저장' }))
    expect(await screen.findByRole('status')).toHaveTextContent('저장')
  })

  it('저장하지 못하면 그렇게 알려 준다', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(
            JSON.stringify({ error: { code: 'SERVER_ERROR', message: '문제가 생겼습니다.' } }),
            { status: 500 },
          ),
      ),
    )
    const user = userEvent.setup()
    open()
    await user.click(screen.getByRole('button', { name: '저장' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('저장하지')
  })

  // 카드에 이미 담겨 있던 값(서버가 준 것)으로 열려야 한다.
  it('카드에 저장된 값이 있으면 그 값으로 연다', () => {
    open({ ...CARD, tagline: '지난번 것' })
    expect(screen.getByLabelText('카드에 넣을 글자')).toHaveValue('지난번 것')
  })

  it('20자를 넘겨 입력할 수 없다', () => {
    open()
    expect(screen.getByLabelText('카드에 넣을 글자')).toHaveAttribute('maxLength', '20')
  })

  // 초기화는 화면의 값만 공장 기본값으로 되돌린다 — 저장을 눌러야 서버도 바뀐다.
  it('초기화하면 화면이 공장 기본값으로 돌아간다', async () => {
    const user = userEvent.setup()
    open({ ...CARD, tagline: '지난번 것' })
    expect(screen.getByLabelText('카드에 넣을 글자')).toHaveValue('지난번 것')

    await user.click(screen.getByRole('button', { name: '초기화' }))
    expect(screen.getByLabelText('카드에 넣을 글자')).toHaveValue('THREE LUNGS')
  })
})
