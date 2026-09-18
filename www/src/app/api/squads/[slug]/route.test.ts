import { NextRequest } from 'next/server'
import { GET } from './route'

/**
 * 공개 슬러그로 **남의 스쿼드**를 읽는 경로 (계약 3-7절
 * `GET /squads/{public_slug}`, 미결 `paik` 37번 · CCC 53번).
 *
 * 🔴 **인증하지 않는다.** 슬러그가 96비트 난수라 그 자체가 접근 통제다
 * (SEC-005 — 공개 카드 `/cards/{slug}` 와 같은 결). 초대받은 사람은 **아직
 * 그 팀 소속이 아니라서** 소속을 요구하면 판을 볼 수가 없다 — 판을 보고
 * 수락 여부를 정하라는 것이 이 기능의 요점이다.
 */

beforeAll(() => {
  process.env.USE_MOCK = '1'
})

function ctx(slug: string) {
  return { params: Promise.resolve({ slug }) }
}

/** mock 의 데모 스쿼드 슬러그. */
const SLUG = 'aB3xK9mQ2pL7vN4t'

describe('GET /api/squads/[slug] — 공개 슬러그로 남의 판 읽기', () => {
  it('🔴 로그인 쿠키가 없어도 판을 준다 — 초대받은 사람은 아직 소속이 아니다', async () => {
    const res = await GET(new NextRequest('http://t/api/squads/' + SLUG), ctx(SLUG))

    expect(res.status).toBe(200)
    const body = await res.json()
    expect(body.public_slug).toBe(SLUG)
    // 판을 그리려면 구성원이 칸과 함께 와야 한다(`MiniPitch` 가 읽는 값).
    expect(body.members.length).toBeGreaterThan(0)
    expect(body.members[0]).toHaveProperty('grid_col')
    expect(body.members[0]).toHaveProperty('position_label')
  })

  it('모르는 슬러그면 404 다 — 빈 판을 지어내지 않는다', async () => {
    const res = await GET(new NextRequest('http://t/api/squads/nope'), ctx('nope'))

    expect(res.status).toBe(404)
    expect((await res.json()).error.code).toBe('SQUAD_NOT_FOUND')
  })
})
