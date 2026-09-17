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

/**
 * **추천 카드의 설명 칸** (미결 `ho` 50번, 2026-09-17).
 *
 * 🔴 **재는 것이 없는 문장은 안 싣는다.** 여기 붙박이로 있던 불릿
 * (「1대1에서 잘 밀리지 않습니다」·「수비 가담이 성실합니다」)은 **경기 행동**
 * 이라 한 편의 자세 분석으로는 못 잰다(정상호). 그런데 그 표는 **닉네임으로**
 * 붙어서, 후보가 진짜 사용자가 된 지금 이름이 겹치면 **지어낸 문장이 그 사람의
 * 진짜 등급 옆에** 걸린다 — 대표 영상으로 한 번 데인 자리다.
 */
describe('추천 판 — 카드에 적히는 말', () => {
  /** mock 표에 있는 이름으로 후보를 세운다 — 있었다면 문구가 붙었을 자리다. */
  const FLAVOR_ROWS = [
    { user_id: 'u1', nickname: '김선우', card_public_slug: 'c', grade: 'A', provisional: false },
  ]

  /**
   * 🔴 **분석이 낸 불릿은 서버가 준 것만 그린다**(CCC 56, 2026-09-17).
   * 같은 날 아침에 붙박이를 걷었고, 오후에 정어진이 진짜 값을 냈다 —
   * 후보 목록 응답에 실려 온다(후보마다 `/grade` 를 다시 안 부른다).
   */
  it('서버가 준 불릿을 그대로 그린다', async () => {
    stubMedia()
    stubCandidates([
      {
        user_id: 'u1',
        nickname: '최유진',
        card_public_slug: 'c',
        grade: 'A',
        provisional: false,
        notes: ['차는 다리를 끝까지 뻗습니다', '디딤발을 공 옆에 붙입니다'],
      },
    ])
    render(
      <SquadSuggest position="MF" me={null} teamId="t1" closing={false} onClose={() => {}} onPick={() => {}} />,
    )
    expect(await screen.findByText('차는 다리를 끝까지 뻗습니다')).toBeInTheDocument()
    expect(screen.getByText('디딤발을 공 옆에 붙입니다')).toBeInTheDocument()
  })

  /* 🔴 **한 줄도 정상이다** — 두 줄을 채우려고 지어내지 않는 것이 규칙이라,
     화면이 「늘 두 줄」로 짜여 있으면 안 된다. */
  it('한 줄만 와도 그대로 그린다', async () => {
    stubMedia()
    stubCandidates([
      { user_id: 'u1', nickname: '최유진', card_public_slug: 'c', grade: 'A', provisional: false, notes: ['상체를 공 위로 덮습니다'] },
    ])
    const { container } = render(
      <SquadSuggest position="MF" me={null} teamId="t1" closing={false} onClose={() => {}} onPick={() => {}} />,
    )
    expect(await screen.findByText('상체를 공 위로 덮습니다')).toBeInTheDocument()
    expect(container.querySelectorAll('.ss-suggest-notes > span')).toHaveLength(1)
  })

  /* 🔴 **`null` 도 정상이다**(옛 봉투거나 분석 전) — 그 칸을 아예 안 그린다.
     화면에서 문장을 짓지 않는다. */
  it('불릿이 없으면 그 칸을 안 그린다', async () => {
    stubMedia()
    stubCandidates([
      { user_id: 'u1', nickname: '최유진', card_public_slug: 'c', grade: 'A', provisional: false, notes: null },
    ])
    const { container } = render(
      <SquadSuggest position="MF" me={null} teamId="t1" closing={false} onClose={() => {}} onPick={() => {}} />,
    )
    expect(await screen.findByText('최유진')).toBeInTheDocument()
    expect(container.querySelector('.ss-suggest-notes')).toBeNull()
  })

  it('재는 것이 없는 불릿은 안 그린다', async () => {
    stubMedia()
    stubCandidates(FLAVOR_ROWS)
    render(
      <SquadSuggest position="GK" me={null} teamId="t1" closing={false} onClose={() => {}} onPick={() => {}} />,
    )
    expect(await screen.findByText('김선우')).toBeInTheDocument()
    // 붙박이 표에 이 사람 앞으로 적혀 있던 문장들 — 다시 들어오면 여기서 걸린다.
    expect(screen.queryByText(/가까운 거리 슈팅 대응이 빠릅니다/)).toBeNull()
    expect(screen.queryByText(/골문 앞을 넓게 씁니다/)).toBeNull()
  })

  /* 🔴 **출처 표식을 화면에 적지 않는다**(2026-09-17, 사용자 판단). 제품
     화면에 「본인이 적음」·「AI가 적음」이 붙으면 읽는 사람에게 이상한 말이다 —
     카드는 선수를 소개하는 자리다. 한 번 붙였다가 걷었으므로 시험으로 막는다. */
  it('출처 표식을 적지 않는다', async () => {
    stubMedia()
    stubCandidates(FLAVOR_ROWS)
    render(
      <SquadSuggest position="GK" me={null} teamId="t1" closing={false} onClose={() => {}} onPick={() => {}} />,
    )
    expect(await screen.findByText('김선우')).toBeInTheDocument()
    expect(screen.queryByText(/본인이 적음|AI가 적음|분석이 적음/)).toBeNull()
  })
})
