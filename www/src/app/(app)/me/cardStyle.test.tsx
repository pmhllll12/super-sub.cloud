import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { PlayerCard } from '@/server/backend'
import { CardStyleProvider, useCardStyle } from './cardStyle'

const CARD: PlayerCard = {
  id: 'c1',
  public_slug: 'hong-gildong',
  og_image_key: 'og/hong.png',
  user: { id: 'u1', nickname: '홍길동' },
  titles: [],
  tagline: null,
  style: null,
}

/** 저장만 눌러 보는 껍데기 — provider 밖 동작은 `useCardStyle` 이 맡는다. */
function SaveButton() {
  const { save } = useCardStyle()
  return (
    <button type="button" onClick={() => void save()}>
      저장
    </button>
  )
}

/**
 * **배포 순서에 안 기대게 한다** (2026-09-18).
 *
 * 🔴 **옛 서버는 사진 칸을 받으면 422 다.** `CardStyleSchema` 가
 * `extra="forbid"` 라, 새 화면이 보내는 `photo_key`·`mode` 를 아직 배포 안 된
 * 서버가 받으면 **카드 저장이 통째로 막힌다** — 사진뿐 아니라 한 줄·색·
 * 붓자국까지.
 *
 * 배포는 「백엔드 먼저」가 맞지만 **자동으로 그렇게 되지 않는다**: main 에
 * 머지하면 `www`(Vercel)는 바로 나가고, 백엔드는 이미지만 빌드된 뒤 사람이
 * k3s 에 롤아웃한다(`.github/workflows/backend-docker-build.yml` 에 `kubectl`
 * 이 없다). 그 사이 몇 분을 이 폴백이 버틴다.
 *
 * 🔴 배포가 끝나면 **이 길은 아예 안 탄다**(422 가 안 나므로).
 */
describe('카드 꾸미기 저장 — 옛 서버도 견딘다', () => {
  function serve(firstStatus: number) {
    const bodies: unknown[] = []
    let n = 0
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((_input: RequestInfo | URL, init?: RequestInit) => {
        bodies.push(JSON.parse(String(init?.body)))
        n += 1
        if (n === 1 && firstStatus !== 200) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                error: { code: 'VALIDATION_ERROR', message: '요청 값이 올바르지 않습니다.' },
              }),
              { status: firstStatus },
            ),
          )
        }
        return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }))
      }),
    )
    return bodies
  }

  afterEach(() => vi.unstubAllGlobals())

  const open = () =>
    render(
      <CardStyleProvider card={CARD}>
        <SaveButton />
      </CardStyleProvider>,
    )

  it('평소에는 사진 칸을 실어 한 번에 보낸다', async () => {
    const bodies = serve(200)
    const user = userEvent.setup()
    open()
    await user.click(screen.getByRole('button', { name: '저장' }))

    expect(bodies).toHaveLength(1)
    expect((bodies[0] as { style: Record<string, unknown> }).style).toHaveProperty('photo_key')
  })

  /* 🔴 **한 줄·색까지 같이 막히는 것이 이 폴백의 이유다.** 사진은 못 담아도
     나머지는 저장돼야 한다. */
  it('422 면 사진 칸을 빼고 한 번 더 보낸다', async () => {
    const bodies = serve(422)
    const user = userEvent.setup()
    open()
    await user.click(screen.getByRole('button', { name: '저장' }))

    expect(bodies).toHaveLength(2)
    const retried = (bodies[1] as { style: Record<string, unknown> }).style
    expect(retried).not.toHaveProperty('photo_key')
    expect(retried).not.toHaveProperty('mode')
    // 나머지는 그대로 간다 — 빼는 것은 사진 칸 다섯뿐이다.
    expect(retried).toHaveProperty('bg')
  })

  /* 🔴 **422 만 다시 보낸다.** 401·403·500 은 사진과 무관한 실패라, 다시
     보내면 같은 실패를 두 번 겪고 사용자만 기다린다. */
  it('422 가 아니면 다시 보내지 않는다', async () => {
    const bodies = serve(500)
    const user = userEvent.setup()
    open()
    await user.click(screen.getByRole('button', { name: '저장' }))

    expect(bodies).toHaveLength(1)
  })
})
