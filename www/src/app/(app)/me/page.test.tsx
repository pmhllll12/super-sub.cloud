import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { Match, MyVideo, PlayerCard, User } from '@/server/backend'
import { MeBody } from './page'

// NicknameForm 이 useRouter 를 쓴다.
vi.mock('next/navigation', () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}))

const USER: User = {
  id: 'u1',
  email: 'demo@super-sub.example',
  nickname: '홍길동',
  created_at: '2026-08-30T00:00:00Z',
  teams: [],
}

const CARD: PlayerCard = {
  id: 'c1',
  public_slug: 'hong-gildong',
  og_image_key: 'og/hong-gildong.png',
  user: { id: 'u1', nickname: '홍길동' },
  titles: [],
}

/** 호칭이 실제로 달린 카드 — 알약을 보려면 필요하다. */
const CARD_WITH_TITLES: PlayerCard = {
  ...CARD,
  titles: [
    { code: 'sharp_shooter', label: '슈팅이 매서운', category: '강점', granted_at: '2026-08-20T12:00:00Z' },
  ],
}

/** 상태 넷을 한 줄씩 — 화면이 구분해서 그려야 하는 것이 그것이다. */
const VIDEOS: MyVideo[] = [
  {
    id: 'v1',
    sport_code: 'football',
    storage_key: '/a.mp4',
    duration_ms: 10200,
    side: 'right',
    created_at: '2026-09-03T09:00:00Z',
    passed: true,
    reject_reason: null,
    analysis_job_id: 'j1',
    analysis_status: 'succeeded',
  },
  {
    id: 'v2',
    sport_code: 'futsal',
    storage_key: '/b.mp4',
    duration_ms: 15600,
    side: null,
    created_at: '2026-09-01T11:05:00Z',
    passed: true,
    reject_reason: null,
    analysis_job_id: null,
    analysis_status: null,
  },
  {
    id: 'v3',
    sport_code: 'baseball',
    storage_key: '/c.mp4',
    duration_ms: 42000,
    side: null,
    created_at: '2026-08-30T08:10:00Z',
    passed: false,
    reject_reason: '해상도가 상한을 넘습니다: 3840x2160 (상한 1920x1080)',
    analysis_job_id: null,
    analysis_status: null,
  },
]

describe('내 프로필 — /me', () => {
  it('닉네임과 이메일을 보여준다', () => {
    render(<MeBody user={USER} card={null} videos={[]} matches={[]} />)
    expect(screen.getByRole('heading', { name: '홍길동' })).toBeInTheDocument()
    expect(screen.getByText('demo@super-sub.example')).toBeInTheDocument()
  })

  // /me/card 를 이 화면으로 합쳤다 — 선수 카드를 보러 다른 데로 보내지 않는다.
  it('선수 카드가 있으면 이 화면에 바로 그린다', () => {
    render(<MeBody user={USER} card={CARD} videos={[]} matches={[]} />)
    // 🔴 카드는 이제 **신원 줄의 한 곳뿐**이다. 오른쪽 칸이 내 영상으로
    // 바뀌면서 그 자리에 있던 큰 카드를 걷어냈다.
    expect(screen.getAllByRole('article', { name: '홍길동' })).toHaveLength(1)
  })

  // ⚠️ 신원 줄에 있던 '공유'는 걷어냈다(사용자 요청) — 그 링크는 2026-08-28
  // 부터 로그인해야 열려서, 밖으로 공유하는 길이 아니었다.
  // 🔴 편집기 **안에는** 있다. 다만 접혀 있는 동안은 `inert` 로 잠겨 있어
  // 탭으로도 닿지 않는다 — 그래서 여기서는 편집기 밖만 본다.
  it('공유 링크를 두지 않는다', () => {
    render(<MeBody user={USER} card={CARD} videos={[]} matches={[]} />)
    const toCard = screen
      .queryAllByRole('link')
      .filter((a) => a.getAttribute('href')?.startsWith('/c/'))
    expect(toCard).toHaveLength(0)
  })

  it('선수 카드가 없으면 아직 없다고 알려준다', () => {
    render(<MeBody user={USER} card={null} videos={[]} matches={[]} />)
    // 🔴 "분석되면 만들어진다" 고 적어 두지 않는다 — 사실이 아니다.
    // 카드는 분석과 무관하게 부탁할 때 생긴다(계약 3장).
    expect(screen.getByText(/아직 선수 카드가 없습니다/)).toBeInTheDocument()
    expect(screen.queryByText(/분석되면 만들어집니다/)).toBeNull()
  })

  it('선수 카드를 보러 다른 페이지로 보내는 링크가 없다 — 여기가 그 자리다', () => {
    render(<MeBody user={USER} card={CARD} videos={[]} matches={[]} />)
    expect(screen.queryByRole('link', { name: /내 선수 카드 보기/ })).toBeNull()
    const toCard = screen
      .queryAllByRole('link')
      .filter((a) => a.getAttribute('href') === '/me/card')
    expect(toCard).toHaveLength(0)
  })

  // 🔴 카드는 호칭을 sr-only 로만 들고 있다(PlayerCardView). 눈에 보이는
  // 자리는 여기 하나뿐이라, 이게 없어지면 호칭은 화면에서 사라진다.
  it('받은 호칭을 분류와 함께 알약으로 보여준다', () => {
    const { container } = render(
      <MeBody user={USER} card={CARD_WITH_TITLES} videos={[]} matches={[]} />,
    )
    // 🔴 `정보` 절 안에서 찾는다 — 접힌 편집기에도 같은 알약이 있어서,
    // 화면 전체에서 세면 어느 쪽을 본 것인지 알 수 없다.
    const info = container.querySelector('.ss-profile-info')!
    expect(info.textContent).toContain('슈팅이 매서운')
    expect(info.textContent).toContain('강점')
  })

  // 개수를 적던 '호칭 2' 배지는 걷어냈다(공유와 함께) — 남은 자리는
  // 정보 절 하나뿐이라, 비었을 때 알려 주는 것도 거기다.
  it('호칭이 없으면 정보 절에서 그렇게 알려준다', () => {
    render(<MeBody user={USER} card={CARD} videos={[]} matches={[]} />)
    expect(screen.getByText('아직 받은 호칭이 없습니다.')).toBeInTheDocument()
  })

  it('소속 팀이 없으면 그렇게 알려준다', () => {
    render(<MeBody user={USER} card={CARD} videos={[]} matches={[]} />)
    expect(screen.getByText('아직 소속된 팀이 없습니다.')).toBeInTheDocument()
  })

  // 프로필은 '보여주는' 화면이다 — 입력칸이 늘 떠 있으면 설정 화면이 된다.
  it('평소에는 입력칸이 없고, 편집을 눌러야 열린다', () => {
    render(<MeBody user={USER} card={CARD} videos={[]} matches={[]} />)
    expect(screen.queryByRole('textbox', { name: '닉네임' })).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: /닉네임 편집/ }))

    expect(screen.getByRole('textbox', { name: '닉네임' })).toHaveValue('홍길동')
    // 편집 중에는 이름과 입력칸이 같이 뜨지 않는다 — 같은 자리다.
    expect(screen.queryByRole('heading', { name: '홍길동' })).toBeNull()
  })

  // 🔴 사용자 요청의 핵심 — 분석 영상과 그냥 올린 영상이 알약으로 갈린다.
  it('두 갈래를 알약으로 나누고 각각 몇 편인지 적는다', () => {
    render(<MeBody user={USER} card={CARD} videos={VIDEOS} matches={[]} />)
    const analyzed = screen.getByRole('tab', { name: /분석 영상/ })
    const uploaded = screen.getByRole('tab', { name: /업로드 영상/ })
    // VIDEOS: 분석 작업이 걸린 것 1편(v1), 걸리지 않은 것 2편(v2 · 반려 v3).
    expect(analyzed).toHaveTextContent('1')
    expect(uploaded).toHaveTextContent('2')
    expect(analyzed).toHaveAttribute('aria-selected', 'true')
  })

  /**
   * 지금 **크게** 보이는 영상의 주소.
   * 🔴 `video` 를 통째로 세지 않는다 — 선 아래 목록에도 표지용 `video` 가
   * 하나씩 들어 있어서, 그러면 목록 길이까지 함께 세게 된다.
   */
  function shownVideo(c: HTMLElement): string | null {
    const els = c.querySelectorAll('.ss-profile-video-player')
    expect(els).toHaveLength(1)
    return els[0].getAttribute('src')
  }

  // 🔴 한 번에 한 편만 그린다 — 목록이 아니다.
  it('한 편만 보이고, 알약을 바꾸면 그 갈래의 영상이 나온다', () => {
    const { container } = render(<MeBody user={USER} card={CARD} videos={VIDEOS} matches={[]} />)
    // 분석 영상 갈래에는 v1 하나뿐이다.
    expect(shownVideo(container)).toBe('/a.mp4')

    fireEvent.click(screen.getByRole('tab', { name: /업로드 영상/ }))

    expect(shownVideo(container)).toBe('/b.mp4')
  })

  it('다음 · 이전 단추로 같은 갈래의 영상을 넘긴다', () => {
    const { container } = render(<MeBody user={USER} card={CARD} videos={VIDEOS} matches={[]} />)
    fireEvent.click(screen.getByRole('tab', { name: /업로드 영상/ }))

    expect(screen.getByText('1 / 2')).toBeInTheDocument()
    expect(shownVideo(container)).toBe('/b.mp4')

    fireEvent.click(screen.getByRole('button', { name: '다음 영상' }))

    expect(screen.getByText('2 / 2')).toBeInTheDocument()
    expect(shownVideo(container)).toBe('/c.mp4')

    // 끝에서 한 번 더 누르면 처음으로 돈다.
    fireEvent.click(screen.getByRole('button', { name: '다음 영상' }))
    expect(screen.getByText('1 / 2')).toBeInTheDocument()
    expect(shownVideo(container)).toBe('/b.mp4')
  })

  // 🔴 넘기는 단추가 앞뒤로만 가는 데 비해, 목록은 바로 고르게 한다.
  it('선 아래 목록에서 영상을 바로 고른다', () => {
    const { container } = render(<MeBody user={USER} card={CARD} videos={VIDEOS} matches={[]} />)
    fireEvent.click(screen.getByRole('tab', { name: /업로드 영상/ }))
    expect(shownVideo(container)).toBe('/b.mp4')

    fireEvent.click(screen.getByRole('button', { name: '2번째 영상' }))

    expect(shownVideo(container)).toBe('/c.mp4')
    expect(screen.getByText('2 / 2')).toBeInTheDocument()
  })

  // 🔴 한 편뿐이어도 줄과 목록은 그대로 있다 — 갈래를 오갈 때 이것들이
  // 생겼다 없어지면 아래 것들이 그때마다 들썩인다. 대신 넘길 데가 없으니
  // 두 단추는 잠근다.
  it('한 편뿐이면 1 / 1 로 적고 넘기는 단추를 잠근다', () => {
    render(<MeBody user={USER} card={CARD} videos={VIDEOS} matches={[]} />)
    // 분석 갈래에는 한 편뿐이다.
    expect(screen.getByText('1 / 1')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '다음 영상' })).toBeDisabled()
    expect(screen.getByRole('button', { name: '이전 영상' })).toBeDisabled()
    expect(screen.getByRole('button', { name: '1번째 영상' })).toBeInTheDocument()
  })

  // 규격에 걸린 클립은 분석 자체를 하지 않는다(계약 3-6절) — 분석 상태가
  // null 이라고 '분석 안 함' 으로 읽으면 안 된다.
  // 반려된 클립은 분석을 아예 하지 않으므로(계약 3-6절) 업로드 갈래에 남는다.
  // 상태 배지는 걷어냈지만 **사유는 남는다** — 알약이 대신해 줄 수 없는 정보다.
  it('반려된 클립은 업로드 갈래에 남고 사유를 편 채로 보여준다', () => {
    render(<MeBody user={USER} card={CARD} videos={[VIDEOS[2]]} matches={[]} />)
    expect(screen.getByRole('tab', { name: /업로드 영상/ })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(screen.getByText(/해상도가 상한을 넘습니다/)).toBeInTheDocument()
  })

  it('갈래가 비어 있으면 그 갈래에 맞게 알려준다', () => {
    render(<MeBody user={USER} card={CARD} videos={[]} matches={[]} />)
    expect(screen.getByText('아직 업로드한 영상이 없습니다.')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('tab', { name: /분석 영상/ }))
    expect(screen.getByText('아직 분석한 영상이 없습니다.')).toBeInTheDocument()
  })

  const MATCHES: Match[] = [
    {
      id: 'm1',
      team_id: 't1',
      played_at: '2026-09-10T10:00:00Z',
      place: '강남 풋살장 2구장',
      needs: [{ position_code: 'FW', position_label: '공격수', head_count: 2 }],
    },
  ]

  it('다가오는 경기를 장소와 필요 자리까지 보여준다', () => {
    render(<MeBody user={USER} card={CARD} videos={[]} matches={MATCHES} />)
    expect(screen.getByText('강남 풋살장 2구장')).toBeInTheDocument()
    expect(screen.getByText('공격수 2')).toBeInTheDocument()
  })

  // ⚠️ 계약이 지난 경기를 목록에서 빼므로(3-4절), 비었다고 "경기가 없다" 로
  // 적으면 안 된다 — 지난 경기가 있어도 여기는 비어 있을 수 있다.
  it('경기가 비면 "다가오는" 것이 없다고 적는다', () => {
    render(<MeBody user={USER} card={CARD} videos={[]} matches={[]} />)
    expect(screen.getByText('다가오는 경기가 없습니다.')).toBeInTheDocument()
  })

  // 되돌릴 수 없는 동작이라 단추를 눌러야 폼이 열린다.
  it('탈퇴는 접혀 있다가 눌러야 열린다', () => {
    render(<MeBody user={USER} card={CARD} videos={[]} matches={[]} />)
    expect(screen.queryByLabelText('비밀번호')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: '회원 탈퇴' }))

    expect(screen.getByLabelText('비밀번호')).toBeInTheDocument()
    expect(screen.getByText(/되돌릴 수 없습니다/)).toBeInTheDocument()
  })

  // 🔴 미결 jin-7 — 카드는 **부탁해야** 생긴다(POST /me/card). 그전에는
  // 화면이 "영상이 분석되면 만들어집니다" 라고 **거짓말을 하고 있었다.**
  it('카드가 없으면 편집 모드에서 만들 수 있다', () => {
    const { container } = render(
      <MeBody user={USER} card={null} videos={[]} matches={[]} editing />,
    )
    expect(container.querySelector('.ss-profile-editor-fold')!.getAttribute('data-open')).toBe(
      'true',
    )
    expect(screen.getByRole('button', { name: '카드 만들기' })).toBeInTheDocument()
  })

  // 편집기는 **고치는 자리**다 — 공유 주소 · 호칭 같은 읽을거리는 두지 않는다.
  it('카드가 있으면 꾸미개만 보여준다', () => {
    render(<MeBody user={USER} card={CARD} videos={[]} matches={[]} editing />)
    // 갈래 셋 — 한 번에 하나만 편다.
    expect(screen.getByRole('tab', { name: '카드' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: '사진' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: '붓' })).toBeInTheDocument()
    expect(screen.queryByText('카드에 담긴 것')).toBeNull()
    expect(screen.queryByRole('button', { name: '카드 만들기' })).toBeNull()
  })

  // 🔴 고른 갈래만 편다 — 다 쌓으면 아래로 길어져 판을 넘친다.
  it('갈래를 고르면 그 설정만 나온다', () => {
    render(<MeBody user={USER} card={CARD} videos={[]} matches={[]} editing />)
    expect(screen.getByLabelText('카드에 넣을 글자')).toBeInTheDocument()
    expect(screen.queryByLabelText('사진 고르기')).toBeNull()

    fireEvent.click(screen.getByRole('tab', { name: '사진' }))

    expect(screen.getByLabelText('사진 고르기')).toBeInTheDocument()
    expect(screen.queryByLabelText('카드에 넣을 글자')).toBeNull()
  })

  // 🔴 편집을 열어도 **원래 붓칠이 그대로 있어야 한다.** 한때 기본을 '없음'
  // 으로 두어, 고치기도 전에 카드가 달라져 버렸다.
  it('편집을 열면 원래 붓칠이 그대로 있다', () => {
    const { container } = render(
      <MeBody user={USER} card={CARD} videos={[]} matches={[]} editing />,
    )
    expect(container.querySelector('.ss-card-stage .ss-pcard-brush')).not.toBeNull()
  })

  // 열 가지 자국 중 하나를 고른다 — 이름만으로는 구별이 안 되므로 모양을 보여준다.
  it('붓 갈래에서 자국을 고르면 카드에 깔린다', () => {
    const { container } = render(
      <MeBody user={USER} card={CARD} videos={[]} matches={[]} editing />,
    )
    fireEvent.click(screen.getByRole('tab', { name: '붓' }))
    fireEvent.click(screen.getByRole('button', { name: '겹원' }))

    const inCard = container.querySelector('.ss-card-stage .ss-pcard .ss-card-mark')
    expect(inCard).not.toBeNull()
    // 고른 자국이 원래 붓칠을 **대신한다** — 둘이 겹치면 무엇을 고른 것인지 모른다.
    expect(container.querySelector('.ss-card-stage .ss-pcard-brush')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: '없음' }))
    expect(container.querySelector('.ss-card-stage .ss-pcard .ss-card-mark')).toBeNull()
  })

  // 🔴 꾸민 값이 **그 자리의 카드**에 바로 실린다 — 미리보기를 따로 두지 않는다.
  it('꾸미개를 바꾸면 카드가 따라 바뀐다', () => {
    const { container } = render(
      <MeBody user={USER} card={CARD} videos={[]} matches={[]} editing />,
    )
    const text = screen.getByLabelText('카드에 넣을 글자')
    fireEvent.change(text, { target: { value: 'ONE LUNG' } })
    expect(container.querySelector('.ss-pcard-alias')!.textContent).toBe('ONE LUNG')

    // 비우면 글자를 아예 그리지 않는다(빈 자리가 남으면 인물이 밀린다).
    fireEvent.change(text, { target: { value: '' } })
    expect(container.querySelector('.ss-pcard-alias')).toBeNull()
  })

  // 🔴 사용자 요청 — 오려 내지 않은 사진으로도 카드를 만들 수 있어야 한다.
  it('사진 놓는 방법을 고르면 카드가 그 방식으로 그려진다', () => {
    const { container } = render(
      <MeBody user={USER} card={CARD} videos={[]} matches={[]} editing />,
    )
    const pcard = container.querySelector('.ss-pcard')!
    expect(pcard.getAttribute('data-photo')).toBeNull()

    fireEvent.click(screen.getByRole('tab', { name: '사진' }))
    fireEvent.click(screen.getByRole('button', { name: '사진 그대로' }))

    expect(pcard.getAttribute('data-photo')).toBe('full')
    // 🔴 사진 위에 **기본 붓칠**은 얹지 않는다 — 그림이 더러워 보인다.
    expect(container.querySelector('.ss-card-stage .ss-pcard-brush')).toBeNull()

    // 다만 일부러 고른 자국은 그린다 — 말없이 지우지 않는다.
    fireEvent.click(screen.getByRole('tab', { name: '붓' }))
    fireEvent.click(screen.getByRole('button', { name: '겹원' }))
    expect(container.querySelector('.ss-card-stage .ss-pcard .ss-card-mark')).not.toBeNull()
  })

  it('사진을 고르면 바로 카드에 들어가고 크기 · 위치를 조정할 수 있다', async () => {
    const { container } = render(
      <MeBody user={USER} card={CARD} videos={[]} matches={[]} editing />,
    )
    fireEvent.click(screen.getByRole('tab', { name: '사진' }))
    // 사진이 없는 동안은 조정할 것도 없다.
    expect(container.querySelectorAll('input[type="range"]')).toHaveLength(0)

    const file = new File(['x'], 'me.png', { type: 'image/png' })
    fireEvent.change(screen.getByLabelText('사진 고르기'), { target: { files: [file] } })

    // FileReader 는 비동기다 — 읽기가 끝나야 카드에 실린다.
    await waitFor(() => {
      expect(container.querySelector('.ss-pcard-figure img')!.getAttribute('src')).toMatch(
        /^data:/,
      )
    })
    expect(container.querySelectorAll('input[type="range"]')).toHaveLength(3)
  })

  // 🔴 사용자 요청 — 글자를 카드 위에서 끌어 놓는다. 다만 `PLAYER CARD`
  // 머리글 위로는 못 간다(로고와 머리글의 자리다).
  it('카드 글자를 끌어 옮길 수 있고, 머리글 위로는 못 올라간다', () => {
    const { container } = render(
      <MeBody user={USER} card={CARD} videos={[]} matches={[]} editing />,
    )
    const stage = container.querySelector('.ss-card-stage') as HTMLElement
    const alias = container.querySelector('.ss-card-stage .ss-pcard-alias') as HTMLElement
    const pcard = container.querySelector('.ss-card-stage .ss-pcard') as HTMLElement

    // jsdom 은 크기를 재지 않는다 — 카드 상자를 우리가 정해 준다.
    pcard.getBoundingClientRect = () =>
      ({ left: 0, top: 0, width: 200, height: 280 }) as DOMRect

    // 🔴 `fireEvent` 로 보낸다 — 직접 `dispatchEvent` 하면 리액트가 상태를
    // 반영하기 전에 다음 줄이 실행돼 옛 값을 읽는다(실측: 34% 가 나왔다).
    stage.setPointerCapture = () => {}
    stage.releasePointerCapture = () => {}

    fireEvent.pointerDown(alias, { clientX: 100, clientY: 95, pointerId: 1 })
    fireEvent.pointerMove(stage, { clientX: 60, clientY: 224, pointerId: 1 }) // 아래쪽 80%
    expect(pcard.style.getPropertyValue('--ss-pcard-text-y')).toBe('80%')

    // 로고 자리로 밀어도 하한에서 멈춘다.
    fireEvent.pointerMove(stage, { clientX: 100, clientY: 0, pointerId: 1 })
    expect(pcard.style.getPropertyValue('--ss-pcard-text-y')).toBe('24%')
  })

  it('처음 모습으로 되돌릴 수 있다', () => {
    const { container } = render(
      <MeBody user={USER} card={CARD} videos={[]} matches={[]} editing />,
    )
    fireEvent.change(screen.getByLabelText('카드에 넣을 글자'), { target: { value: '바뀜' } })
    fireEvent.click(screen.getByRole('button', { name: '처음 모습으로' }))
    expect(container.querySelector('.ss-pcard-alias')!.textContent).toBe('THREE LUNGS')
  })

  // 🔴 편집기는 **늘 그려 두고 접는다** — 열 때만 그리면 닫을 때 뚝 사라진다.
  // 대신 접혀 있는 동안은 `inert` 로 잠근다.
  it('평소에는 편집기가 접혀 있고, 여는 링크만 있다', () => {
    const { container } = render(<MeBody user={USER} card={CARD} videos={[]} matches={[]} />)
    const fold = container.querySelector('.ss-profile-editor-fold')!
    expect(fold.getAttribute('data-open')).toBe('false')
    expect(fold.hasAttribute('inert')).toBe(true)
    expect(screen.getByRole('link', { name: '프로필 카드 수정' })).toHaveAttribute(
      'href',
      '/me?edit=1',
    )
  })

  it('편집을 취소하면 고치던 값을 버린다', () => {
    render(<MeBody user={USER} card={CARD} videos={[]} matches={[]} />)
    fireEvent.click(screen.getByRole('button', { name: /닉네임 편집/ }))
    fireEvent.change(screen.getByRole('textbox', { name: '닉네임' }), {
      target: { value: '임꺽정' },
    })
    fireEvent.click(screen.getByRole('button', { name: '취소' }))

    expect(screen.getByRole('heading', { name: '홍길동' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /닉네임 편집/ }))
    expect(screen.getByRole('textbox', { name: '닉네임' })).toHaveValue('홍길동')
  })
})
