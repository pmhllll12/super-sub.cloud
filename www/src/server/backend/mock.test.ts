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
})
