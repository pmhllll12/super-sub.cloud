import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SquadSuggest from './SquadSuggest'

/**
 * 🔴 jsdom 은 `HTMLMediaElement.play` · `pause` 를 **안 깔아 준다**(부르면
 * "not implemented" 로 터진다). 실제 브라우저에는 있으므로 시험만 다른 세상이
 * 되지 않도록 세워 두고, 불렸는지를 여기서 센다.
 */
function stubMedia() {
  const play = vi.fn(() => Promise.resolve())
  const pause = vi.fn()
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockImplementation(play)
  vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(pause)
  return { play, pause }
}

afterEach(() => vi.restoreAllMocks())

/**
 * 후보는 **서버에서 온다**(2026-09-16, 계약 3-16절). 이 파일이 보는 것은
 * 「장면이 어떻게 도는가」라 목록은 짧게 세우고, 문구·클립은 여전히 화면의
 * mock(`FLAVOR`)에서 온다(계약 44번이 그은 범위).
 */
const MF_ROWS = [
  { user_id: 'u1', nickname: '최유진', card_public_slug: 'c', grade: 'A', provisional: true },
  { user_id: 'u2', nickname: '강태원', card_public_slug: 'd', grade: 'B', provisional: false },
  { user_id: 'u3', nickname: '윤서준', card_public_slug: 'e', grade: 'C', provisional: true },
]

function stubCandidates(rows: unknown[] = MF_ROWS) {
  vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
    Promise.resolve(new Response(JSON.stringify(rows), { status: 200 })),
  )
}

async function open(props: Partial<React.ComponentProps<typeof SquadSuggest>> = {}) {
  stubCandidates()
  const r = render(
    <SquadSuggest
      position="MF"
      teamId="team-mine"
      closing={false}
      onPick={() => {}}
      onClose={() => {}}
      {...props}
    />,
  )
  // 서버에서 오므로 **떠야 볼 수 있다**.
  await screen.findByText('최유진')
  return r
}

/** 후보 줄 — 손짓의 과녁은 단추가 아니라 줄(li)이다. */
function rows() {
  return screen.getAllByRole('listitem')
}

describe('추천 판 — 후보마다 대표 장면이 돈다', () => {
  it('빈 카드가 아니라 영상이 있다', async () => {
    stubMedia()
    const { container } = await open()

    // MF 는 셋이다 — 사람 수만큼 영상이 있어야 한다.
    expect(rows()).toHaveLength(3)
    expect(container.querySelectorAll('video')).toHaveLength(3)
  })

  it('판이 나올 때는 멈춰 있다', async () => {
    const { play } = stubMedia()
    const { container } = await open()

    // 🔴 `autoPlay` 를 주면 판이 열리자마자 셋이 한꺼번에 돈다 — 훑어보기
    //    전에 이미 다 움직이면 "가져다 대면 돈다"가 성립하지 않는다.
    expect(play).not.toHaveBeenCalled()
    for (const v of container.querySelectorAll('video')) {
      expect(v).not.toHaveAttribute('autoplay')
    }
  })

  it('가져다 대면 돌고, 떼면 멈추고 처음으로 돌아간다', async () => {
    const { play, pause } = stubMedia()
    const user = userEvent.setup()
    await open()

    await user.hover(rows()[0])
    expect(play).toHaveBeenCalledTimes(1)

    const video = rows()[0].querySelector('video')!
    video.currentTime = 5

    await user.unhover(rows()[0])
    expect(pause).toHaveBeenCalledTimes(1)
    // 다음에 가져다 댔을 때 늘 같은 자리에서 시작해야 "그 사람의 대표
    // 장면"으로 읽힌다.
    expect(video.currentTime).toBe(0)
  })

  it('멈춰 있는 동안에도 그림이 보이도록 첫 칸을 집어 준다', async () => {
    stubMedia()
    const { container } = await open()

    // 🔴 `#t=0.1` 이 없으면 `preload="metadata"` 만 보고 그림을 안 그려서
    //    칸이 검게만 남는다(코치 목록에서 겪은 것).
    for (const v of container.querySelectorAll('video')) {
      expect(v.getAttribute('src')).toMatch(/#t=0\.1$/)
      // 소리 없이 · 되풀이 · 전체 화면으로 튀어나오지 않게.
      expect(v).toHaveAttribute('loop')
      expect((v as HTMLVideoElement).muted || v.hasAttribute('muted')).toBe(true)
      expect(v).toHaveAttribute('playsinline')
    }
  })

  /* 🔴 사람마다 자기 `/me` 에서 고른 **대표 영상**이 이 판에서 돈다
     (사용자 요청, 2026-09-08). ⚠️ 지금 실제로 갈리는 것은 **내 것뿐**이다 —
     후보 응답의 `card_public_slug` 로 남의 대표 영상도 읽을 수 있지만
     (계약 3-6절) 계약 44번이 「지금은 mock 클립 그대로」로 범위를 그었다. */
  it('목록에 내가 있으면 내가 고른 대표 영상을 튼다', async () => {
    stubMedia()
    const { container } = await open({ me: { nickname: '최유진', clip: '/my-featured.mp4' } })
    const srcs = [...container.querySelectorAll('video')].map((v) => v.getAttribute('src'))
    expect(srcs[0]).toBe('/my-featured.mp4#t=0.1')
    // 나머지는 자리 표시 그대로다.
    expect(srcs[1]).not.toContain('my-featured')
  })

  it('내가 고른 것이 없으면 자리 표시를 그대로 쓴다', async () => {
    stubMedia()
    const { container } = await open({ me: { nickname: '최유진', clip: null } })
    expect(container.querySelector('video')!.getAttribute('src')).toMatch(/coach-c00\d\.mp4#t=0\.1/)
  })

  it('고르는 것은 여전히 누르는 일이다 — 가져다 대는 것과 갈라져 있다', async () => {
    stubMedia()
    const picked: string[] = []
    const user = userEvent.setup()
    await open({ onPick: (n: string) => picked.push(n) })

    await user.hover(rows()[0])
    expect(picked).toEqual([])

    await user.click(screen.getByRole('button', { name: /최유진/ }))
    expect(picked).toEqual(['최유진'])
  })
})

/**
 * 🔴 **모르는 사람에게 아무 영상이나 붙이지 않는다**(2026-09-16).
 *
 * 후보가 진짜 사용자로 바뀌면서 `FLAVOR`(화면 mock)에 없는 이름이 대부분이
 * 된다. 전에는 자리 표시 클립 하나로 떨어뜨렸는데, 그러면 **이름과 등급이
 * 진짜인 옆에 남의 영상이 「그 사람 대표 장면」으로** 붙는다.
 */
describe('추천 판 — 대표 영상이 없는 사람', () => {
  it('아는 클립이 없으면 영상 대신 없다고 적는다', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      Promise.resolve(
        new Response(
          JSON.stringify([
            {
              user_id: 'u9',
              nickname: '처음보는사람',
              card_public_slug: null,
              grade: 'B',
              provisional: false,
            },
          ]),
          { status: 200 },
        ),
      ),
    )
    const { container } = render(
      <SquadSuggest
        position="MF"
        teamId="team-mine"
        closing={false}
        onPick={() => {}}
        onClose={() => {}}
      />,
    )
    expect(await screen.findByText('처음보는사람')).toBeInTheDocument()
    // 🔴 남의 영상이 붙으면 안 된다.
    expect(container.querySelector('video')).toBeNull()
    expect(screen.getByText('아직 대표 영상이 없습니다')).toBeInTheDocument()
    // 이름과 등급은 진짜라 그대로 나온다.
    // ⚠️ 거르개 알약에도 「B」가 있어서 줄 안으로 좁혀서 본다.
    const line = screen.getByText('처음보는사람').closest('.ss-suggest-nameline')
    expect(line?.querySelector('.ss-suggest-grade')).toHaveTextContent('B')
  })
})

/**
 * 🔴 **대표 영상은 따로 물어서 채운다**(2026-09-16, 계약 3-6절).
 *
 * 후보 응답(3-16절)에는 영상이 없다 — `card_public_slug` 로 한 사람씩
 * `GET /cards/{slug}/featured-video` 를 부른다. 그래서 목록이 먼저 서고
 * 영상이 뒤따라 채워진다.
 */
describe('추천 판 — 대표 영상을 따라 받는다', () => {
  const ROW = {
    user_id: 'u1',
    nickname: '처음보는사람',
    card_public_slug: 'someone-card',
    grade: 'B',
    provisional: false,
  }

  function stub(featured: { ok: boolean; url?: string }) {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/featured-video')) {
        return Promise.resolve(
          featured.ok
            ? new Response(JSON.stringify({ url: featured.url, expires_in: 900 }), { status: 200 })
            : new Response(
                JSON.stringify({ error: { code: 'NO_FEATURED_VIDEO', message: '없습니다.' } }),
                { status: 404 },
              ),
        )
      }
      return Promise.resolve(new Response(JSON.stringify([ROW]), { status: 200 }))
    })
  }

  const open = () =>
    render(
      <SquadSuggest
        position="MF"
        teamId="team-mine"
        closing={false}
        onPick={() => {}}
        onClose={() => {}}
      />,
    )

  it('대표 영상이 있으면 그 사람 영상을 튼다', async () => {
    stub({ ok: true, url: '/their-featured.mp4' })
    const { container } = open()
    await screen.findByText('처음보는사람')
    await waitFor(() =>
      expect(container.querySelector('video')?.getAttribute('src')).toBe(
        '/their-featured.mp4#t=0.1',
      ),
    )
  })

  /* 🔴 **404 는 오류가 아니다** — 아직 안 고른 사람이다. 남의 영상을 대신
     틀지 않는다. */
  it('대표 영상이 없으면(404) 영상 없이 그대로 둔다', async () => {
    stub({ ok: false })
    const { container } = open()
    await screen.findByText('처음보는사람')
    expect(container.querySelector('video')).toBeNull()
    expect(screen.getByText('아직 대표 영상이 없습니다')).toBeInTheDocument()
  })
})
