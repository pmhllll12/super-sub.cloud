import { mockBackend } from './mock'

describe('mockBackend', () => {
  it('데모 계정으로 로그인하면 토큰을 준다', async () => {
    const t = await mockBackend.login({
      email: 'demo@super-sub.example',
      password: 'supersub2026',
    })
    expect(t.access_token).toBeTruthy()
    expect(t.token_type).toBe('bearer')
    expect(t.expires_in).toBe(604800)
  })

  it('비밀번호가 틀리면 INVALID_CREDENTIALS 를 던진다', async () => {
    await expect(
      mockBackend.login({ email: 'demo@super-sub.example', password: '틀림' }),
    ).rejects.toMatchObject({ status: 401, code: 'INVALID_CREDENTIALS' })
  })

  it('없는 이메일도 INVALID_CREDENTIALS 다 — 가입 여부를 흘리지 않는다', async () => {
    await expect(
      mockBackend.login({ email: '없는사람@example.com', password: 'supersub2026' }),
    ).rejects.toMatchObject({ status: 401, code: 'INVALID_CREDENTIALS' })
  })

  it('가입하면 teams 없이 사용자를 돌려준다', async () => {
    const u = await mockBackend.signup({
      email: '새사람@example.com',
      password: 'supersub2026',
      nickname: '새사람',
    })
    expect(u.nickname).toBe('새사람')
    expect(u).not.toHaveProperty('teams')
  })

  it('이미 있는 이메일로 가입하면 EMAIL_ALREADY_EXISTS 다', async () => {
    await expect(
      mockBackend.signup({
        email: 'demo@super-sub.example',
        password: 'supersub2026',
        nickname: '중복',
      }),
    ).rejects.toMatchObject({ status: 409, code: 'EMAIL_ALREADY_EXISTS' })
  })

  it('가입한 계정은 맞는 비밀번호로만 로그인된다 — 8자 이상이어도 틀리면 거부한다', async () => {
    await mockBackend.signup({
      email: '비번확인@example.com',
      password: 'correct-password',
      nickname: '비번확인',
    })

    await expect(
      mockBackend.login({ email: '비번확인@example.com', password: 'wrong-password' }),
    ).rejects.toMatchObject({ status: 401, code: 'INVALID_CREDENTIALS' })

    const t = await mockBackend.login({
      email: '비번확인@example.com',
      password: 'correct-password',
    })
    expect(t.access_token).toBeTruthy()
  })

  it('토큰이 유효하지 않으면 getMe 가 INVALID_TOKEN 을 던진다', async () => {
    await expect(mockBackend.getMe('가짜토큰')).rejects.toMatchObject({
      status: 401,
      code: 'INVALID_TOKEN',
    })
  })

  it('닉네임을 바꾸면 GET /me 와 같은 형태를 돌려준다', async () => {
    const t = await mockBackend.login({
      email: 'demo@super-sub.example',
      password: 'supersub2026',
    })
    const u = await mockBackend.updateMe(t.access_token, { nickname: '바뀐이름' })
    expect(u.nickname).toBe('바뀐이름')
    expect(Array.isArray(u.teams)).toBe(true)
  })

  it('공개 카드는 인증 없이 조회된다', async () => {
    const c = await mockBackend.getPublicCard('hong-gildong-4f2a')
    expect(c.public_slug).toBe('hong-gildong-4f2a')
    expect(c).not.toHaveProperty('id')
  })

  it('없는 슬러그는 CARD_NOT_FOUND 다', async () => {
    await expect(mockBackend.getPublicCard('없는슬러그')).rejects.toMatchObject({
      status: 404,
      code: 'CARD_NOT_FOUND',
    })
  })

  it('카드에 수치 필드를 넣지 않는다', async () => {
    const c = await mockBackend.getPublicCard('hong-gildong-4f2a')
    const keys = Object.keys(c)
    expect(keys).not.toContain('score')
    expect(keys).not.toContain('rating')
    expect(keys).not.toContain('grade')
    for (const t of c.titles) {
      expect(t).not.toHaveProperty('earned')
    }
  })

  describe('createTeamMatch — 흐름 B(모집 등록 돕기) 챗봇이 부르는 자리', () => {
    const DEMO_TOKEN = 'mock-access-token-demo'
    const DEMO_TEAM_ID = '9a2e0000-0000-4000-8000-000000000002'
    const future = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString()
    const past = new Date(Date.now() - 60 * 60 * 1000).toISOString()

    it('주장이면 등록되고, 포지션 라벨이 붙어 돌아온다', async () => {
      const m = await mockBackend.createTeamMatch(DEMO_TOKEN, DEMO_TEAM_ID, {
        played_at: future,
        place: '테스트 구장',
        needs: [{ position_code: 'GK', head_count: 1 }],
      })
      expect(m.team_id).toBe(DEMO_TEAM_ID)
      expect(m.needs).toEqual([{ position_code: 'GK', position_label: '골키퍼', head_count: 1 }])
    })

    it('모르는 팀이면 TEAM_NOT_FOUND 다', async () => {
      await expect(
        mockBackend.createTeamMatch(DEMO_TOKEN, '없는팀', {
          played_at: future,
          place: '어딘가',
          needs: [{ position_code: 'GK', head_count: 1 }],
        }),
      ).rejects.toMatchObject({ status: 404, code: 'TEAM_NOT_FOUND' })
    })

    it('지난 시각이면 PAST_MATCH 다', async () => {
      await expect(
        mockBackend.createTeamMatch(DEMO_TOKEN, DEMO_TEAM_ID, {
          played_at: past,
          place: '어딘가',
          needs: [{ position_code: 'GK', head_count: 1 }],
        }),
      ).rejects.toMatchObject({ status: 422, code: 'PAST_MATCH' })
    })

    it('needs 가 비어 있으면 VALIDATION_ERROR 다', async () => {
      await expect(
        mockBackend.createTeamMatch(DEMO_TOKEN, DEMO_TEAM_ID, {
          played_at: future,
          place: '어딘가',
          needs: [],
        }),
      ).rejects.toMatchObject({ status: 422, code: 'VALIDATION_ERROR' })
    })

    it('이 팀 종목에 없는 포지션이면 UNKNOWN_POSITION 이다', async () => {
      await expect(
        mockBackend.createTeamMatch(DEMO_TOKEN, DEMO_TEAM_ID, {
          played_at: future,
          place: '어딘가',
          // 야구 포지션을 축구 팀에 적었다.
          needs: [{ position_code: 'P', head_count: 1 }],
        }),
      ).rejects.toMatchObject({ status: 422, code: 'UNKNOWN_POSITION' })
    })

    it('같은 포지션을 두 번 적으면 DUPLICATE_POSITION 이다', async () => {
      await expect(
        mockBackend.createTeamMatch(DEMO_TOKEN, DEMO_TEAM_ID, {
          played_at: future,
          place: '어딘가',
          needs: [
            { position_code: 'GK', head_count: 1 },
            { position_code: 'GK', head_count: 1 },
          ],
        }),
      ).rejects.toMatchObject({ status: 422, code: 'DUPLICATE_POSITION' })
    })
  })
})
