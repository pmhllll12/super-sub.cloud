import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MatchBot from './MatchBot'

describe('MatchBot — 흐름 B(모집 등록 돕기) 챗봇', () => {
  it('닫혀 있으면 아무것도 그리지 않는다', () => {
    render(<MatchBot open={false} onClose={() => {}} />)
    expect(screen.queryByRole('complementary', { name: '용병 찾기' })).toBeNull()
  })

  it('열리면 안내 문구와 입력창이 보인다', () => {
    render(<MatchBot open onClose={() => {}} />)
    expect(screen.getByRole('complementary', { name: '용병 찾기' })).toBeInTheDocument()
    expect(screen.getByLabelText('메시지')).toBeInTheDocument()
    expect(screen.getByText(/어느 팀에 어떤 경기를 등록할지/)).toBeInTheDocument()
  })

  it('닫기를 누르면 onClose 가 불린다', async () => {
    const onClose = vi.fn()
    const user = userEvent.setup()
    render(<MatchBot open onClose={onClose} />)
    await user.click(screen.getByRole('button', { name: '용병 찾기 닫기' }))
    expect(onClose).toHaveBeenCalled()
  })

  it('메시지를 보내면 /api/chat 을 부르고 답을 그린다', async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => {
      return new Response(
        JSON.stringify({ history: [], reply: '어느 구장에서 하나요?', proposal: null }),
        { status: 200 },
      )
    })
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    render(<MatchBot open onClose={() => {}} />)
    await user.type(screen.getByLabelText('메시지'), '토요일에 골키퍼 1명요')
    await user.click(screen.getByRole('button', { name: '보내기' }))

    await screen.findByText('어느 구장에서 하나요?')
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/chat',
      expect.objectContaining({ method: 'POST' }),
    )
    const call = fetchMock.mock.calls[0]!
    expect(JSON.parse(call[1]!.body as string)).toMatchObject({ message: '토요일에 골키퍼 1명요' })
  })

  it('슬롯이 다 차면 확인 카드가 뜨고, 등록을 누르면 경기 등록 API를 부른다', async () => {
    const proposal = {
      team_id: 't1',
      team_name: '번개FC',
      played_at: '2026-09-13T10:00:00Z',
      place: '강남 풋살장 2구장',
      needs: [{ position_code: 'GK', position_label: '골키퍼', head_count: 1 }],
    }
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url === '/api/chat') {
        return new Response(
          JSON.stringify({ history: [], reply: '이대로 등록할까요?', proposal }),
          { status: 200 },
        )
      }
      if (url === '/api/teams/t1/matches') {
        return new Response(JSON.stringify({ id: 'm1', ...proposal }), { status: 201 })
      }
      throw new Error(`예상하지 못한 요청: ${url}`)
    })
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    render(<MatchBot open onClose={() => {}} />)
    await user.type(screen.getByLabelText('메시지'), '네')
    await user.click(screen.getByRole('button', { name: '보내기' }))

    await screen.findByText('번개FC', { exact: false })
    expect(screen.getByText(/골키퍼 1명/)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '등록' }))
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith('/api/teams/t1/matches', expect.objectContaining({ method: 'POST' })),
    )
    await screen.findByText('경기 등록이 완료됐어요!')
  })

  it('등록이 실패하면 에러 문구가 카드 안에 남고 카드는 안 사라진다', async () => {
    const proposal = {
      team_id: 't1',
      team_name: '번개FC',
      played_at: '2026-09-13T10:00:00Z',
      place: '강남 풋살장 2구장',
      needs: [{ position_code: 'GK', position_label: '골키퍼', head_count: 1 }],
    }
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      if (url === '/api/chat') {
        return new Response(JSON.stringify({ history: [], reply: '', proposal }), { status: 200 })
      }
      return new Response(
        JSON.stringify({ error: { code: 'PAST_MATCH', message: '지났습니다' } }),
        { status: 422 },
      )
    })
    vi.stubGlobal('fetch', fetchMock)

    const user = userEvent.setup()
    render(<MatchBot open onClose={() => {}} />)
    await user.type(screen.getByLabelText('메시지'), '네')
    await user.click(screen.getByRole('button', { name: '보내기' }))
    await screen.findByText('번개FC', { exact: false })

    await user.click(screen.getByRole('button', { name: '등록' }))
    await screen.findByText('그 시간은 이미 지났어요, 다른 시간을 알려주세요.')
    expect(screen.getByRole('button', { name: '등록' })).toBeInTheDocument()
  })
})
