import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import NotifyPanel from './NotifyPanel'
import type { InboxItem } from '@/lib/useNotifyInbox'

/**
 * 「알림」 글자 아래로 떠오르는 판 (사용자 요청, 2026-09-16).
 *
 * 🔴 요청의 핵심은 **별도 화면을 만들지 않는 것**이다 — 상대 팀 정보와 수락
 * 단추가 같은 줄에 있어야 하고, 가리키기만 하면 나와야 한다. 그래서 이 시험은
 * "줄 안에 둘이 같이 있는가"를 붙든다.
 */
const MATCH: InboxItem = {
  kind: 'team-match',
  id: 'tmr1',
  teamId: 'team-mine',
  opponentTeamId: 'mt-2',
  name: '망원 유나이티드',
  region: '서울 마포구',
  playedAt: '2026-09-19T09:00:00+09:00',
  place: '망원 실내구장 A',
}

describe('알림 판', () => {
  it('받은 경기 신청에 상대 팀 정보와 수락 단추가 같이 있다', () => {
    render(
      <NotifyPanel
        items={[MATCH]}
        onAcceptMatch={vi.fn()}
        onRejectMatch={vi.fn()}
        onAcceptContact={vi.fn()}
      />,
    )
    const row = screen.getByText('망원 유나이티드').closest('.ss-notify-row')
    expect(row).not.toBeNull()
    expect(row).toHaveTextContent('서울 마포구')
    expect(row).toHaveTextContent('망원 실내구장 A')
    // 🔴 **같은 줄 안에** 있어야 한다 — 눌러 들어가는 화면을 만들지 않는 것이
    //    요청이라, 단추가 다른 곳에 있으면 그 요청을 안 지킨 것이다.
    expect(row?.querySelector('button')).toHaveTextContent('수락하기')
  })

  it('수락하면 그 줄을 넘겨 부른다', async () => {
    const user = userEvent.setup()
    const onAcceptMatch = vi.fn().mockResolvedValue(undefined)
    render(
      <NotifyPanel
        items={[MATCH]}
        onAcceptMatch={onAcceptMatch}
        onRejectMatch={vi.fn()}
        onAcceptContact={vi.fn()}
      />,
    )
    await user.click(screen.getByRole('button', { name: '수락하기' }))
    expect(onAcceptMatch).toHaveBeenCalledWith(MATCH)
  })

  /* 🔴 **이름을 지어내지 않는다.** 계약이 팀 이름을 안 줘서(3-15절은 id 만
     준다) 진짜 백엔드에서는 자주 `null` 이다 — 그때 빈 줄이 되면 안 된다. */
  it('상대 팀 이름을 모르면 「상대 팀」으로 적는다', () => {
    render(
      <NotifyPanel
        items={[{ ...MATCH, name: null, region: null }]}
        onAcceptMatch={vi.fn()}
        onRejectMatch={vi.fn()}
        onAcceptContact={vi.fn()}
      />,
    )
    expect(screen.getByText('상대 팀')).toBeInTheDocument()
  })

  it('받은 것이 없으면 그렇게 적는다', () => {
    render(
      <NotifyPanel
        items={[]}
        onAcceptMatch={vi.fn()}
        onRejectMatch={vi.fn()}
        onAcceptContact={vi.fn()}
      />,
    )
    expect(screen.getByText('새 알림이 없습니다')).toBeInTheDocument()
  })
})
