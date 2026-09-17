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

  /**
   * 🔴 **모르는 종목은 서버처럼 거절한다**(2026-09-16).
   *
   * 서버의 `sport` 참조 테이블에는 `football`·`baseball`·`basketball` 셋뿐이다 —
   * 마이그레이션 `20260901_sport_and_position.py` 가 `futsal` 을 **폐기**하고
   * `football` 로 옮겼다. 그런데 팀 만들기 경로가 `futsal` 을 보내고 있었고,
   * mock 이 무엇이든 받아 줘서 **개발에서만 돌고 배포에서 `422 UNKNOWN_SPORT`
   * (「등록되지 않은 종목 코드입니다」)로 죽었다**(사용자가 겪음).
   *
   * 🔴 이 시험이 붙드는 것은 팀 만들기 화면이 아니라 **mock 이 계약보다
   * 너그러워지지 않는 것**이다. 너그러우면 그 차이는 늘 배포에서만 드러난다.
   */
  it('모르는 종목으로 팀을 만들면 UNKNOWN_SPORT 다', async () => {
    const t = await mockBackend.login({
      email: 'demo@super-sub.example',
      password: 'supersub2026',
    })
    await expect(
      mockBackend.createTeam(t.access_token, {
        name: '강남 FC',
        region: '서울 강남',
        sport_code: 'futsal',
      }),
    ).rejects.toMatchObject({ status: 422, code: 'UNKNOWN_SPORT' })
  })

  it('있는 종목으로는 팀이 만들어진다', async () => {
    const t = await mockBackend.login({
      email: 'demo@super-sub.example',
      password: 'supersub2026',
    })
    const team = await mockBackend.createTeam(t.access_token, {
      name: '강남 FC',
      region: '서울 강남',
      sport_code: 'football',
    })
    expect(team).toMatchObject({ name: '강남 FC', sport_code: 'football' })
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

  describe('searchMercenaryCandidates — 흐름 D(용병 후보 검색) 챗봇이 부르는 자리', () => {
    const DEMO_TOKEN = 'mock-access-token-demo'

    it('포지션에 맞는 후보를 돌려준다', async () => {
      const candidates = await mockBackend.searchMercenaryCandidates(DEMO_TOKEN, {
        sport_code: 'football',
        position_code: 'GK',
        query_text: '주말 저녁 가능한 골키퍼',
      })
      expect(candidates.length).toBeGreaterThan(0)
      expect(candidates[0].nickname).toBeTruthy()
    })

    it('맞는 후보가 없으면 빈 배열이다 — 에러가 아니다', async () => {
      const candidates = await mockBackend.searchMercenaryCandidates(DEMO_TOKEN, {
        sport_code: 'baseball',
        position_code: 'C',
        query_text: '아무나',
      })
      expect(candidates).toEqual([])
    })

    it('limit 만큼만 돌려준다', async () => {
      const candidates = await mockBackend.searchMercenaryCandidates(DEMO_TOKEN, {
        sport_code: 'football',
        position_code: 'GK',
        query_text: '아무나',
        limit: 0,
      })
      expect(candidates).toEqual([])
    })
  })
})

/**
 * **`PATCH /teams/{id}` — mock 이 계약만큼 엄한가** (CCC 52번, 2026-09-17).
 *
 * 🔴 **mock 이 실서버보다 너그러우면 배포에서만 터진다.** 2026-09-16 에 같은
 * 원인으로 세 번 데였다(지인 검색 스위치 · 팀 만들기 종목 · 호칭 저장). 특히
 * 마지막 것은 서버가 모르는 필드를 **조용히 버리고 200** 을 줘서 **실패가
 * 성공처럼** 보였다 — 붙드는 것은 화면이 아니라 **mock 이 다시 너그러워지지
 * 않는 것**이라 여기서 잠근다.
 */
describe('mock — 팀 이름·지역 수정', () => {
  async function owner() {
    const t = await mockBackend.login({
      email: 'demo@super-sub.example',
      password: 'supersub2026',
    })
    const team = await mockBackend.createTeam(t.access_token, {
      name: '강남 FC',
      region: '서울 강남구',
      sport_code: 'football',
    })
    return { token: t.access_token, teamId: team.id }
  }

  it('주장은 이름·지역을 고친다', async () => {
    const { token, teamId } = await owner()
    const after = await mockBackend.updateTeam(token, teamId, { region: '부산 해운대구' })
    expect(after).toMatchObject({ id: teamId, name: '강남 FC', region: '부산 해운대구' })
  })

  it('보낸 칸만 바뀐다 — 뺀 칸은 그대로다', async () => {
    const { token, teamId } = await owner()
    const after = await mockBackend.updateTeam(token, teamId, { name: '천둥FC' })
    expect(after).toMatchObject({ name: '천둥FC', region: '서울 강남구' })
  })

  it('아무것도 안 보내면 아무것도 안 바뀐다', async () => {
    const { token, teamId } = await owner()
    const after = await mockBackend.updateTeam(token, teamId, {})
    expect(after).toMatchObject({ name: '강남 FC', region: '서울 강남구' })
  })

  /* 🔴 **`null` 은 지우기가 아니라 422 다** — 둘 다 NOT NULL 이라 「안 정한
     상태」가 없다. 조용히 건너뛰면 화면이 200 을 성공으로 읽는다. */
  it('null 을 보내면 422 다 — 조용히 무시하지 않는다', async () => {
    const { token, teamId } = await owner()
    await expect(
      mockBackend.updateTeam(token, teamId, { region: null } as unknown as { region?: string }),
    ).rejects.toMatchObject({ status: 422, code: 'VALIDATION_ERROR' })
  })

  it('빈 글자도 422 다', async () => {
    const { token, teamId } = await owner()
    await expect(mockBackend.updateTeam(token, teamId, { name: '   ' })).rejects.toMatchObject({
      status: 422,
    })
  })

  /* 🔴 **주장만**(계약) — 구성원은 403, 없는 팀은 404. */
  it('구성원이면 403 이다', async () => {
    const t = await mockBackend.login({
      email: 'demo@super-sub.example',
      password: 'supersub2026',
    })
    const me = await mockBackend.getMe(t.access_token)
    const asMember = me.teams.find((x) => x.role !== 'owner')
    if (!asMember) return // 데모 계정이 전부 주장이면 이 갈래는 여기서 못 밟는다
    await expect(
      mockBackend.updateTeam(t.access_token, asMember.team_id, { name: '아무거나' }),
    ).rejects.toMatchObject({ status: 403, code: 'FORBIDDEN' })
  })

  it('없는 팀이면 404 다', async () => {
    const { token } = await owner()
    await expect(mockBackend.updateTeam(token, '없는팀', { name: 'x' })).rejects.toMatchObject({
      status: 404,
    })
  })
})

/**
 * **`DELETE /matches/{id}` — 확정 경기 무르기** (계약 3-4절, 미결 `paik` 34번,
 * 2026-09-17).
 *
 * 🔴 **취소는 행 삭제다** — `match` 에 상태 컬럼이 없다. 그래서 지난 경기·
 * 주장 아님은 서버가 막고, 지원이 붙은 경기는 DB 의 RESTRICT 가 막는다
 * (`409`, mock 에는 지원 개념이 없어 여기서는 못 밟는다 — `cancelMatch` 머리말).
 */
describe('mock — 확정 경기 무르기', () => {
  async function ownerWithMatch() {
    const t = await mockBackend.login({
      email: 'demo@super-sub.example',
      password: 'supersub2026',
    })
    const me = await mockBackend.getMe(t.access_token)
    const mine = me.teams.find((x) => x.role === 'owner')!
    const when = new Date(Date.now() + 7 * 24 * 3600_000).toISOString()
    const match = await mockBackend.createTeamMatch(t.access_token, mine.team_id, {
      played_at: when,
      place: '망원 풋살장',
      needs: [{ position_code: 'GK', head_count: 1 }],
    })
    return { token: t.access_token, teamId: mine.team_id, matchId: match.id }
  }

  it('주장은 무를 수 있고, 무르면 목록에서 사라진다', async () => {
    const { token, teamId, matchId } = await ownerWithMatch()
    expect((await mockBackend.listTeamMatches(token, teamId)).some((m) => m.id === matchId)).toBe(
      true,
    )
    await mockBackend.cancelMatch(token, matchId)
    expect((await mockBackend.listTeamMatches(token, teamId)).some((m) => m.id === matchId)).toBe(
      false,
    )
  })

  it('없는 경기면 404 다', async () => {
    const { token } = await ownerWithMatch()
    await expect(mockBackend.cancelMatch(token, '없는경기')).rejects.toMatchObject({
      status: 404,
      code: 'MATCH_NOT_FOUND',
    })
  })

  /* 🔴 두 번 무르면 두 번째는 404 다 — 행이 사라졌기 때문이다(상태 컬럼이 없다). */
  it('두 번 무르면 두 번째는 404 다', async () => {
    const { token, matchId } = await ownerWithMatch()
    await mockBackend.cancelMatch(token, matchId)
    await expect(mockBackend.cancelMatch(token, matchId)).rejects.toMatchObject({ status: 404 })
  })
})

/**
 * **로컬에서 받은 초대를 실제로 볼 수 있는가** (미결 `paik` 37번).
 *
 * 🔴 mock 의 초대 Map 은 원래 **비어 있었다** — 거기 들어가려면 누군가 나를
 * 초대해야 하는데, 데모 계정은 제 팀의 **주장**이라 남을 초대할 수만 있었다.
 * 그래서 `USE_MOCK=1` 로 띄워도 초대 줄이 **영영 안 떴다.** 씨앗을 하나 둔다.
 */
describe('mock — 받은 팀 초대 씨앗', () => {
  const TOKEN = 'mock-access-token-demo'

  it('데모 계정에게 받은 초대가 하나 있다 — 안 그러면 화면을 못 본다', async () => {
    const rows = await mockBackend.listMyInvitations(TOKEN)
    expect(rows.length).toBeGreaterThan(0)
    expect(rows[0].status).toBe('pending')
  })

  /* 🔴 **내 팀이 나를 부르는 모양이면 안 된다** — 데모 계정은 번개FC 주장이라
     자기가 자기를 초대한 꼴이 된다. 초대는 **다른 팀**에서 와야 말이 된다. */
  it('초대한 팀은 내 팀이 아니다 — 자기가 자기를 부르지 않는다', async () => {
    const rows = await mockBackend.listMyInvitations(TOKEN)
    expect(rows[0].team_name).not.toBe('번개FC')
    expect(rows[0].team_name).toBeTruthy()
    expect(rows[0].team_region).toBeTruthy()
  })

  it('판을 볼 수 있게 슬러그가 실린다', async () => {
    const rows = await mockBackend.listMyInvitations(TOKEN)
    expect(rows[0].squad_public_slug).toBeTruthy()
    // 그 슬러그로 실제 판이 읽혀야 한다 — 「판 보기」가 그걸 부른다.
    const squad = await mockBackend.getSquadBySlug(rows[0].squad_public_slug as string)
    expect(squad.members.length).toBeGreaterThan(0)
  })
})
