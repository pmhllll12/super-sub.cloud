import { HOME_TEAM_COOKIE, pickTeamId, rememberHomeTeam } from './homeTeam'

/**
 * 🔴 **쿠키 값을 믿지 않는다.** 사람이 고칠 수 있는 값이라, 소속이 아닌 id 를
 * 넣으면 남의 팀을 읽으려 든다 — 여기서 걸러야 화면이 빈 판이 안 된다.
 */
describe('홈에 보일 팀', () => {
  const teams = [{ team_id: 'a' }, { team_id: 'b' }]

  it('고른 것이 내 소속이면 그것을 쓴다', () => {
    expect(pickTeamId(teams, 'b')).toBe('b')
  })

  it('안 골랐으면 첫 팀이다', () => {
    expect(pickTeamId(teams, undefined)).toBe('a')
  })

  it('내 소속이 아닌 id 는 무시하고 첫 팀으로 떨어진다', () => {
    expect(pickTeamId(teams, '남의팀')).toBe('a')
  })

  it('소속이 없으면 아무것도 아니다', () => {
    expect(pickTeamId([], 'a')).toBeUndefined()
  })

  it('고른 것을 쿠키에 적는다', () => {
    rememberHomeTeam('b')
    expect(document.cookie).toContain(`${HOME_TEAM_COOKIE}=b`)
  })
})
