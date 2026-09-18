import {
  forgetInviteSeat,
  inviteSeat,
  pruneInviteSeats,
  rememberInviteSeat,
} from './inviteSeats'

describe('초대로 고른 칸', () => {
  beforeEach(() => globalThis.localStorage?.clear())

  it('적어 둔 칸을 그대로 돌려준다', () => {
    rememberInviteSeat('inv-1', { col: 2, row: 1 })
    expect(inviteSeat('inv-1')).toEqual({ col: 2, row: 1 })
  })

  it('적은 적 없으면 null 이다', () => {
    expect(inviteSeat('inv-없음')).toBeNull()
  })

  it('지우면 없어진다', () => {
    rememberInviteSeat('inv-1', { col: 2, row: 1 })
    forgetInviteSeat('inv-1')
    expect(inviteSeat('inv-1')).toBeNull()
  })

  /* 🔴 사람이 고칠 수 있는 값이다 — 그대로 쓰면 `gridColumn: NaN` 이 된다. */
  it('모양이 깨진 값은 없는 것으로 친다', () => {
    globalThis.localStorage.setItem('ss-invite-seats', '{"inv-1":{"col":"왼쪽","row":1}}')
    expect(inviteSeat('inv-1')).toBeNull()
  })

  it('저장소에 아무 글자나 들어 있어도 안 던진다', () => {
    globalThis.localStorage.setItem('ss-invite-seats', 'not json')
    expect(inviteSeat('inv-1')).toBeNull()
  })

  /* 🔴 **끝난 초대만 쓸어 낸다** — 안 그러면 저장소가 영영 자란다. */
  it('이번에 본 목록에서 사라진 초대의 칸을 버린다', () => {
    rememberInviteSeat('inv-1', { col: 0, row: 1 })
    rememberInviteSeat('inv-2', { col: 2, row: 1 })
    pruneInviteSeats(['inv-1', 'inv-2'], ['inv-2'])
    expect(inviteSeat('inv-1')).toBeNull()
    expect(inviteSeat('inv-2')).toEqual({ col: 2, row: 1 })
  })

  /* ⚠️ 목록은 **한 팀의 것**이다 — 못 본 id 는 남의 팀 것일 수 있어 안 건드린다. */
  it('이번 목록에 아예 없던 초대는 남겨 둔다', () => {
    rememberInviteSeat('inv-남의팀', { col: 1, row: 0 })
    pruneInviteSeats(['inv-1'], [])
    expect(inviteSeat('inv-남의팀')).toEqual({ col: 1, row: 0 })
  })
})
