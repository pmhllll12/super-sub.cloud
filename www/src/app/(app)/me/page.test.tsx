import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { Match, MyVideo, PlayerCard, User } from '@/server/backend'
import { HIDDEN_MARKS, MARKS } from '@/components/CardMark'
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
  tagline: null,
  style: null,
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
    is_featured: false,
    is_public: false,
    title: null,
    description: null,
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
    is_featured: false,
    is_public: false,
    title: null,
    description: null,
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
    is_featured: false,
    is_public: false,
    title: null,
    description: null,
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
  /* 🔴 **분류(강점·활동)를 더는 안 적는다**(2026-09-16 결정, 미결 `paik` 36번).
     호칭을 사람이 직접 적게 되면서 그 글에 분류를 매길 사람이 없어졌다. */
  it('정한 호칭을 알약으로 보여준다 — 분류는 안 적는다', () => {
    const { container } = render(
      <MeBody user={USER} card={CARD_WITH_TITLES} videos={[]} matches={[]} />,
    )
    // 🔴 `정보` 절 안에서 찾는다 — 접힌 편집기에도 같은 알약이 있어서,
    // 화면 전체에서 세면 어느 쪽을 본 것인지 알 수 없다.
    const info = container.querySelector('.ss-profile-info')!
    expect(info.textContent).toContain('슈팅이 매서운')
    expect(info.textContent).not.toContain('강점')
  })

  // 개수를 적던 '호칭 2' 배지는 걷어냈다(공유와 함께) — 남은 자리는
  // 정보 절 하나뿐이라, 비었을 때 알려 주는 것도 거기다.
  /* 🔴 **정정 (2026-09-16, 사용자 요청)**: 빈 호칭을 말로 알리던 것을 걷었다 —
     바로 옆 「호칭 정하기」 단추가 이미 그 말을 한다. 미달 표식을 대신 두지
     않는 것(계약 4장)은 그대로다. */
  it('호칭이 없으면 정하는 자리만 내고 빈 것을 말하지 않는다', () => {
    render(<MeBody user={USER} card={CARD} videos={[]} matches={[]} />)
    expect(screen.getByRole('button', { name: '호칭 정하기' })).toBeInTheDocument()
    expect(screen.queryByText(/호칭이 없습니다/)).toBeNull()
  })

  it('소속 팀이 없으면 한 줄로만 알려준다', () => {
    render(<MeBody user={USER} card={CARD} videos={[]} matches={[]} />)
    // 🔴 여기서도 「팀 만들기」 단추가 바로 아래에 있어 같은 말을 두 번 안 한다.
    expect(screen.getByText('아직 소속된 팀이 없습니다.')).toBeInTheDocument()
    expect(screen.queryByText(/팀을 만들어야/)).toBeNull()
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
  it('두 갈래를 알약으로 나눈다', () => {
    render(<MeBody user={USER} card={CARD} videos={VIDEOS} matches={[]} />)
    const analyzed = screen.getByRole('tab', { name: /분석 영상/ })
    expect(screen.getByRole('tab', { name: /업로드 영상/ })).toBeInTheDocument()
    expect(analyzed).toHaveAttribute('aria-selected', 'true')
  })

  /* 🔴 알약에 편수를 **안 적는다**(사용자 요청). 몇 편인지는 영상 아래
     `1 / N` 이 이미 말하고 있어서 같은 말을 두 번 하던 자리였다. */
  it('알약에 편수를 적지 않는다', () => {
    render(<MeBody user={USER} card={CARD} videos={VIDEOS} matches={[]} />)
    expect(screen.getByRole('tab', { name: '분석 영상' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: '업로드 영상' })).toBeInTheDocument()
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

  /**
   * 갈래를 바꾸고 **다 바뀔 때까지 기다린다**.
   *
   * 🔴 누른 직후에는 아직 **옛 갈래가 그려져 있다**(2026-09-16, 사용자 요청으로
   * 넣은 연출). 판이 오른쪽으로 물러난 뒤에 내용이 갈리기 때문이다 — 알약만
   * 먼저 켜진다. 물러남이 끝났다는 신호(`data-leaving` 이 지워짐)를 기다린다.
   */
  async function toTab(name: RegExp | string) {
    fireEvent.click(screen.getByRole('tab', { name }))
    await waitFor(() =>
      expect(document.querySelector('.ss-profile-swap')).not.toHaveAttribute('data-leaving'),
    )
  }

  // 🔴 한 번에 한 편만 그린다 — 목록이 아니다.
  it('한 편만 보이고, 알약을 바꾸면 그 갈래의 영상이 나온다', async () => {
    const { container } = render(<MeBody user={USER} card={CARD} videos={VIDEOS} matches={[]} />)
    // 분석 영상 갈래에는 v1 하나뿐이다.
    expect(shownVideo(container)).toBe('/a.mp4')

    await toTab(/업로드 영상/)

    expect(shownVideo(container)).toBe('/b.mp4')
  })

  /* 🔴 **먼저 물러나고 그 뒤에 갈린다**(2026-09-16, 사용자 요청: "두개 왔다
     갔다 클릭할 때 너무 사라지고 나오는게 부자연스러워"). 누르자마자 갈아
     끼우면 옛 내용이 그 자리에서 사라지고 새것이 툭 나타난다 — 그 툭을
     없애려고 넣었다.

     🔴 **알약은 바로 켜진다.** 내용까지 기다리면 눌러도 반응이 없는 것처럼
     읽힌다 — 누른 자리가 먼저 답하고 내용이 따라온다. */
  it('알약을 누르면 판이 먼저 물러나고, 그 사이 내용은 아직 옛 갈래다', async () => {
    const { container } = render(<MeBody user={USER} card={CARD} videos={VIDEOS} matches={[]} />)

    fireEvent.click(screen.getByRole('tab', { name: /업로드 영상/ }))

    expect(container.querySelector('.ss-profile-swap')).toHaveAttribute('data-leaving', 'true')
    expect(screen.getByRole('tab', { name: /업로드 영상/ })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(shownVideo(container)).toBe('/a.mp4')

    // 다 물러난 뒤에 갈리고, 물러남 표시도 지워진다(그래야 제자리로 돌아온다).
    await waitFor(() => expect(shownVideo(container)).toBe('/b.mp4'))
    expect(container.querySelector('.ss-profile-swap')).not.toHaveAttribute('data-leaving')
  })

  it('다음 · 이전 단추로 같은 갈래의 영상을 넘긴다', async () => {
    const { container } = render(<MeBody user={USER} card={CARD} videos={VIDEOS} matches={[]} />)
    await toTab(/업로드 영상/)

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
  it('선 아래 목록에서 영상을 바로 고른다', async () => {
    const { container } = render(<MeBody user={USER} card={CARD} videos={VIDEOS} matches={[]} />)
    await toTab(/업로드 영상/)
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

  it('갈래가 비어 있으면 그 갈래에 맞게 알려준다', async () => {
    render(<MeBody user={USER} card={CARD} videos={[]} matches={[]} />)
    expect(screen.getByText('아직 업로드한 영상이 없습니다.')).toBeInTheDocument()

    await toTab(/분석 영상/)
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

  /**
   * **로그아웃을 회원 탈퇴 옆에 둔다** (사용자 요청, 2026-09-18).
   *
   * 🔴 여태 로그아웃은 **홈 오른쪽 아래 구석에만** 있었다. 프로필을 보다가
   * 나가려면 홈으로 되돌아가야 했다 — 계정을 다루는 자리에 계정에서 나가는
   * 길이 없던 셈이다.
   *
   * 🔴 **탈퇴와 달리 접지 않는다.** 접는 이유는 되돌릴 수 없어서인데
   * (`AccountActions` 머리말), 로그아웃은 다시 로그인하면 그만이다.
   */
  it('계정 판에 로그아웃이 있다', () => {
    render(<MeBody user={USER} card={CARD} videos={[]} matches={[]} />)
    expect(screen.getByRole('button', { name: '로그아웃' })).toBeInTheDocument()
  })

  /* 🔴 **로그아웃은 빨갛지 않다.** 되돌릴 수 없는 손짓의 색이라(globals.css
     의 `--ss-danger` 주석) 나란히 두면 탈퇴와 같은 무게로 읽힌다. */
  it('로그아웃에는 위험 색을 안 쓴다', () => {
    render(<MeBody user={USER} card={CARD} videos={[]} matches={[]} />)
    expect(
      screen.getByRole('button', { name: '로그아웃' }).className,
    ).not.toContain('ss-profile-tab--danger')
  })

  /* 눌러도 탈퇴 폼이 열리면 안 된다 — 둘은 다른 일이다. */
  it('로그아웃을 눌러도 탈퇴 폼이 안 열린다', () => {
    render(<MeBody user={USER} card={CARD} videos={[]} matches={[]} />)
    fireEvent.click(screen.getByRole('button', { name: '로그아웃' }))
    expect(screen.queryByLabelText('비밀번호')).toBeNull()
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
    // 그림 자국 하나를 고른다 — 이름은 `CardMark.MARKS` 가 정본이다.
    fireEvent.click(screen.getByRole('button', { name: '수채 구름' }))

    const inCard = container.querySelector('.ss-card-stage .ss-pcard .ss-card-mark')
    expect(inCard).not.toBeNull()
    // 고른 자국이 원래 붓칠을 **대신한다** — 둘이 겹치면 무엇을 고른 것인지 모른다.
    expect(container.querySelector('.ss-card-stage .ss-pcard-brush')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: '없음' }))
    expect(container.querySelector('.ss-card-stage .ss-pcard .ss-card-mark')).toBeNull()
  })

  // 🔴 거둔 자국은 **고르는 칸에서만** 사라진다. 배열에서 지우면 뒤 번호가
  //    당겨져 이미 저장된 카드가 말없이 바뀌므로, 자리는 그대로 두고 안 그린다.
  //    (`CardMark.test.tsx` 가 배열 쪽 불변을 붙든다.)
  it('감춘 자국은 고르는 칸에 안 뜬다', () => {
    render(<MeBody user={USER} card={CARD} videos={[]} matches={[]} editing />)
    fireEvent.click(screen.getByRole('tab', { name: '붓' }))

    for (const i of HIDDEN_MARKS) {
      expect(screen.queryByRole('button', { name: MARKS[i] })).toBeNull()
    }
    // 감춘 것 말고는 다 있어야 한다 — 실수로 더 지웠는지 여기서 걸린다.
    const shown = MARKS.filter((_, i) => !HIDDEN_MARKS.has(i)).length
    expect(document.querySelectorAll('.ss-card-mark-pick')).toHaveLength(shown)
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
    // 그림 자국 하나를 고른다 — 이름은 `CardMark.MARKS` 가 정본이다.
    fireEvent.click(screen.getByRole('button', { name: '수채 구름' }))
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

    /* 🔴 **미리보기가 먼저 선다**(2026-09-18). 올리는 동안 카드가 그대로면
       「눌렀는데 아무 일도 안 난다」로 보인다 — 고르는 즉시 `blob:` 으로
       그려 놓고, S3 업로드는 그 뒤에 돈다.
       (앞서 이 시험은 `data:`(FileReader)를 기대했다 — 사진을 브라우저에만
       두던 시절의 값이다.) */
    await waitFor(() => {
      expect(container.querySelector('.ss-pcard-figure img')!.getAttribute('src')).toMatch(
        /^blob:/,
      )
    })
    expect(container.querySelectorAll('input[type="range"]')).toHaveLength(3)
  })

  /**
   * 🔴 **올라가기 전에 저장하면 사진이 안 남는다** — 서버로 가는 값은 S3
   * 키인데 그것이 아직 없기 때문이다. 말 안 해 주면 「저장했는데 사라졌다」가
   * 된다. 여기서는 업로드가 실패하는 상황을 세워 그 자리를 본다.
   */
  it('사진이 안 올라갔으면 그렇다고 적는다', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(null, { status: 500 }),
    )
    const { container } = render(
      <MeBody user={USER} card={CARD} videos={[]} matches={[]} editing />,
    )
    fireEvent.click(screen.getByRole('tab', { name: '사진' }))
    const file = new File(['x'], 'me.png', { type: 'image/png' })
    fireEvent.change(screen.getByLabelText('사진 고르기'), { target: { files: [file] } })

    expect(await screen.findByRole('alert')).toHaveTextContent(/올리지 못했습니다/)
    // 미리보기는 그대로 서 있다 — 고른 것이 사라지면 더 혼란스럽다.
    expect(container.querySelector('.ss-pcard-figure img')!.getAttribute('src')).toMatch(
      /^blob:/,
    )
    vi.restoreAllMocks()
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

  // 🔴 글자 자리를 **슬라이더로도** 옮긴다(2026-09-19) — 끌기와 같은 값이다.
  it('글자 좌우·위아래 슬라이더가 카드의 글자를 옮긴다', () => {
    const { container } = render(
      <MeBody user={USER} card={CARD} videos={[]} matches={[]} editing />,
    )
    const pcard = container.querySelector<HTMLElement>('.ss-card-stage .ss-pcard')!
    fireEvent.change(screen.getByRole('slider', { name: '글자 위아래' }), { target: { value: '70' } })
    fireEvent.change(screen.getByRole('slider', { name: '글자 좌우' }), { target: { value: '30' } })
    expect(pcard.style.getPropertyValue('--ss-pcard-text-y')).toBe('70%')
    expect(pcard.style.getPropertyValue('--ss-pcard-text-x')).toBe('30%')
    // 위로는 로고 자리까지만 — 끌기와 같은 하한
    expect(screen.getByRole('slider', { name: '글자 위아래' })).toHaveAttribute('min', '24')
  })

  // 초기화는 이제 카드를 지운다(묻고 나서) — 화면 값도 먼저 기본값으로 돌린다.
  it('초기화로 되돌릴 수 있다', () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 204 }))
    const { container } = render(
      <MeBody user={USER} card={CARD} videos={[]} matches={[]} editing />,
    )
    fireEvent.change(screen.getByLabelText('카드에 넣을 글자'), { target: { value: '바뀜' } })
    fireEvent.click(screen.getByRole('button', { name: '초기화' }))
    expect(container.querySelector('.ss-pcard-alias')!.textContent).toBe('THREE LUNGS')
    vi.restoreAllMocks()
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


/* 할 일이 남은 사람이 프로필에 오면 그 단추를 가리킨다(2026-09-19) — 카드 먼저, 그다음 팀. */
describe('프로필 안내', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('카드가 없으면 연출이 끝난 뒤 「먼저 내 카드를 만들어주세요.」', () => {
    render(<MeBody user={USER} card={null} videos={[]} matches={[]} />)
    expect(screen.queryByText('먼저 내 카드를 만들어주세요.')).toBeNull()
    act(() => vi.advanceTimersByTime(1700))
    expect(screen.getByText('먼저 내 카드를 만들어주세요.')).toBeInTheDocument()
  })

  it('카드는 있는데 팀이 없으면 「먼저 팀을 만들어주세요.」', () => {
    render(<MeBody user={{ ...USER, teams: [] }} card={CARD} videos={[]} matches={[]} />)
    act(() => vi.advanceTimersByTime(1700))
    expect(screen.getByText('먼저 팀을 만들어주세요.')).toBeInTheDocument()
  })

  it('카드도 팀도 있으면 아무것도 안 띄운다', () => {
    const teamed = { ...USER, teams: [{ team_id: 't1', name: '번개FC', region: '서울', sport_code: 'football', role: 'owner', joined_at: '2026-07-01T00:00:00Z' }] }
    render(<MeBody user={teamed as typeof USER} card={CARD} videos={[]} matches={[]} />)
    act(() => vi.advanceTimersByTime(1700))
    expect(screen.queryByRole('status', { name: '' })).toBeNull()
    expect(screen.queryByText(/먼저 .*만들어주세요/)).toBeNull()
  })
})
