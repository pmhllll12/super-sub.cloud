import fs from 'node:fs'
import path from 'node:path'

/**
 * 🔴 **선택자와 `{` 사이에 주석이 끼면 안 된다.** CSS 는 그것을 오류로 안 보고
 * 다음 `{` 까지 선택자를 이어 붙인다 — 앞 규칙의 선택자가 **뒤 규칙에 붙고**,
 * 원래 규칙의 몸통은 범위 없이 떨어져 나간다. 콘솔에도 안 남는다.
 *
 * 이 파일에서 두 번 밟았다:
 *   · 2026-09-08 `.ss-profile-id-main,` 뒤에 절 주석 → 연출이 사흘 죽어 있었다
 *   · 2026-09-11 `.ss-shot[data-picked='true']` 뒤에 「선수와 비교하기」 절 주석 →
 *     영상 틀의 키 규칙이 기본 규칙(38vh)에 져서 **분석 화면 영상이 반으로 줄었다**
 *
 * 둘 다 절을 **선택자와 몸통 사이에** 끼워 넣다가 생겼다. 눈으로는 안 보이고
 * jsdom 은 CSS 를 안 그리므로 파일을 직접 읽어 잡는다.
 */
const CSS = fs.readFileSync(path.resolve(__dirname, 'globals.css'), 'utf8')

/**
 * 선택자를 쓰다 말고 **절이 시작된** 자리의 줄 번호.
 *
 * ⚠️ 목록 중간의 주석 자체는 괜찮다 — `.a,\n/* 왜 *\/\n.b {` 는 목록이 이어지므로
 * 뜻대로 된다(이 파일에 그렇게 쓴 곳이 넷 있다). 망가진 두 번은 모두 주석이
 * **절 머리**(`/* ──`)이거나 **뒤에 빈 줄**이 있었다 — 「여기서 끊긴다」고 쓴
 * 사람이 믿은 모양이다. 그 둘만 잡는다.
 */
function commentsInsideSelectors(css: string): number[] {
  const hits: number[] = []
  let pending = ''
  let line = 1
  for (let i = 0; i < css.length; i++) {
    const ch = css[i]
    if (ch === '/' && css[i + 1] === '*') {
      const end = css.indexOf('*/', i + 2)
      const stop = end === -1 ? css.length : end + 2
      const header = /^\/\*\s*──/.test(css.slice(i, i + 12))
      const blankAfter = /^[ \t]*\n[ \t]*\n/.test(css.slice(stop))
      if (pending.trim() !== '' && (header || blankAfter)) hits.push(line)
      line += (css.slice(i, stop).match(/\n/g) ?? []).length
      i = stop - 1
      continue
    }
    if (ch === '\n') line++
    if (ch === '{' || ch === '}' || ch === ';') pending = ''
    else pending += ch
  }
  return hits
}

describe('globals.css', () => {
  /* 🔴 **절대배치 격자 자식은 끝 줄을 꼭 적는다**(2026-09-15, 사용자 지적 — 세 순간
     카드가 서면 초록 박스 · 뼈대가 영상과 같이 안 올라가고 카드 위에 남았다).
     `grid-row: 1` 은 `1 / auto` 인데, 절대배치에서 `auto` 끝 줄은 **격자 상자의
     가장자리**다 — 그래서 판이 윗줄(55%)이 아니라 상자 전체 키를 덮었고,
     `toViewBox` 가 그 키로 셈해 뼈대가 아래로 늘어졌다. 헤드리스 크롬 실측:
     `grid-row: 1` → 키 200px, `1 / 2` → 110px(55fr 행). */
  it('비교 칸의 뼈대 판은 윗줄 · 오른쪽 칸 하나만 덮는다', () => {
    const rule = CSS.match(
      /\.ss-shot-frame-body\[data-compare='true'\] > \.ss-shot-track,[^{]*\{([^}]*)\}/,
    )?.[1]
    expect(rule).toBeDefined()
    expect(rule).toMatch(/grid-row:\s*1\s*\/\s*2\s*;/)
    expect(rule).toMatch(/grid-column:\s*2\s*\/\s*3\s*;/)
  })

  it('선택자와 { 사이에 주석이 끼어 있지 않다', () => {
    expect(commentsInsideSelectors(CSS)).toEqual([])
  })

  // 검사 자체가 판별이 되는지 — 실제로 밟았던 두 모양을 넣어 본다.
  it('검사가 실제로 밟았던 모양을 잡는다', () => {
    // 2026-09-11 — 선택자 뒤에 절 머리
    expect(commentsInsideSelectors('.a /* ── 절 */\n\n.b {\n  color: red;\n}')).toEqual([1])
    // 2026-09-08 — 목록 쉼표 뒤에 절 주석, 빈 줄
    expect(commentsInsideSelectors('.a,\n/* 절 */\n\n.b {\n}')).toEqual([2])
    // 뜻대로 되는 것은 안 잡는다 — 목록 중간의 설명 · 몸통 안의 주석
    expect(commentsInsideSelectors('.a,\n/* 왜 */\n.b {\n}')).toEqual([])
    expect(commentsInsideSelectors('/* ── 절 */\n\n.a {\n  /* 값 */\n  color: red;\n}')).toEqual([])
  })

  /**
   * 🔴 **홈의 두 판은 화면 아래를 안 넘는다** (2026-09-17, 사용자 제보 —
   * 「맥북은 안 그런데 PC 에서는 저 판에서 스크롤하면 내려간다」).
   *
   * 판은 스쿼드 판 상자에 매달려 있고 그 상자는 **경기장 높이라 어느 창에서나
   * 702px 고정**이다. 헤드리스 크롬 실측(고치기 전 → 뒤):
   *   · 맥북 14" 1512×857  화면 밖 **9px** → −16
   *   · PC 1366×768        화면 밖 **72px** → −16
   *   · PC 1280×720        화면 밖 **108px** → −17
   *   · 1024×768           화면 밖 **117px** → −17
   * 맥북만 거의 0 이라 우리 눈에는 멀쩡해 보였다.
   *
   * 🔴 **그리고 잘린 부분은 스크롤로 못 되찾는다** — `body` 의
   * `overflow-x: clip` 이 세로까지 `clip` 으로 만든다(한 축이 `clip` 이면
   * 다른 축의 `visible` 도 `clip` 이 되는 규칙). `clip` 을 모르는 브라우저에서는
   * 반대로 페이지가 통째로 내려간다 — 증상이 갈릴 뿐 뿌리는 하나다.
   */
  it('홈의 두 판에 화면 높이 상한이 걸려 있다', () => {
    for (const sel of ['\\.ss-teams', '\\.ss-tm']) {
      const rule = CSS.match(new RegExp(`^${sel} \\{([^}]*)\\}`, 'm'))?.[1]
      expect(rule, sel).toBeDefined()
      // 값은 `useFitToViewport` 가 잰다 — 판의 화면 위 자리를 CSS 는 못 읽는다.
      expect(rule, sel).toMatch(/max-height:\s*var\(--ss-fit-h/)
    }
  })

  /**
   * 🔴 **판 위에서 굴린 휠이 페이지로 새지 않는다.** 안쪽 목록·폼에만 걸면
   * 그것들이 꽉 안 찼을 때 그대로 문서로 넘어간다 — 그래서 **판 자신**
   * (`.ss-teams`, `overflow: hidden` 이라 그 자체로 스크롤 상자다)에도 건다.
   */
  it('판과 판 안의 구르는 영역이 스크롤을 페이지로 넘기지 않는다', () => {
    const areas = ['\\.ss-teams', '\\.ss-teams-list', '\\.ss-tm-list', '\\.ss-prefs']
    for (const sel of areas) {
      const rule = CSS.match(new RegExp(`^${sel} \\{([^}]*)\\}`, 'm'))?.[1]
      expect(rule, sel).toBeDefined()
      expect(rule, sel).toMatch(/overscroll-behavior:\s*contain\s*;/)
    }
  })

  /**
   * 🔴 **「수락 대기중」 알약의 규칙이 살아 있다** (2026-09-17).
   *
   * 이 블록을 **두 번 날렸다** — 09-16 에 「나」 핀 규칙을 다시 쓰면서 그 밑의
   * 것을 슬라이스로 같이 지웠고, 09-17 에 그 핀 CSS 를 걷으면서 **또** 같이
   * 지웠다. 요소는 그려지는데 스타일만 없어서 알약이 카드 아래 **큰 글자**로
   * 떨어진다 — 콘솔에도 안 남고 시험도 안 잡았다. 이제 여기서 잡는다.
   */
  it('수락 대기중 알약이 카드 위에 걸치는 규칙을 갖는다', () => {
    const rule = CSS.match(/^\.ss-squad-pending \{([^}]*)\}/m)?.[1]
    expect(rule).toBeDefined()
    // 카드 **위쪽에 걸친다** — 흐름에 두면 카드 아래로 떨어진다.
    expect(rule).toMatch(/position:\s*absolute\s*;/)
    expect(rule).toMatch(/top:\s*-11px\s*;/)
    // 알약 모양 · 어두운 바탕 위 빨간 글자.
    expect(rule).toMatch(/border-radius:\s*999px\s*;/)
    expect(rule).toMatch(/color:\s*var\(--ss-error\)/)
  })
})

/**
 * 🔴 **초대 판의 카드 폭 규칙은 `.ss-mini` 규칙보다 뒤에 있어야 한다.**
 *
 * 둘 다 `.<조상> .ss-squad` 라 특이도가 같다(0,2,0) — 같으면 **파일에 나중에
 * 적힌 것이 이긴다.** 초대 판 규칙을 앞(560줄쯤)에 뒀다가 13,000줄 뒤의
 * `.ss-mini .ss-squad { --ss-pcard-mini-w: 92 }` 에 져서, 알림 판(230px)에
 * 92px 카드 3열이 들어가 **판이 화면을 통째로 넘었다**(2026-09-17, 사용자가
 * 화면으로 잡았다).
 *
 * 1.11 회차가 `.ss-profile-tab--danger` 로 똑같이 밟고 「CSS 변형은 기본 규칙
 * *뒤*에 둔다」고 적어 둔 그 함정이다. 눈으로는 안 보이므로 순서를 시험이 붙든다.
 */
describe('CSS 규칙 순서 — 같은 특이도는 순서로만 이긴다', () => {
  it('초대 판의 카드 폭이 `.ss-mini` 기본값보다 뒤에 온다', () => {
    const base = CSS.indexOf('.ss-mini .ss-squad {')
    const override = CSS.indexOf('.ss-notify-squad .ss-squad {')

    expect(base).toBeGreaterThan(-1)
    expect(override).toBeGreaterThan(-1)
    expect(override).toBeGreaterThan(base)
  })

  /* 판이 줄 안에 들어가면 **아래 알림들을 화면 밖으로 밀어낸다** — 알림은
     여럿일 수 있다. 흐름에서 빼는 것이 이 판의 요점이다. */
  it('초대 판은 흐름에서 빠져 줄 왼쪽에 선다', () => {
    const block = CSS.slice(
      CSS.indexOf('.ss-notify-squad {'),
      CSS.indexOf('@keyframes ss-notify-squad-in'),
    )
    expect(block).toMatch(/position:\s*absolute/)
    expect(block).toMatch(/right:\s*calc\(100% \+/)
  })

  /* `.ss-mini` 는 대기 팝업에서 옆으로 날아드는 판이라 760ms 지연이 걸려
     있다 — 안 끄면 「판 보기」를 누른 뒤 0.76초 동안 아무것도 안 나타난다. */
  it('대기 팝업의 760ms 지연 연출을 끈다', () => {
    const i = CSS.indexOf('.ss-notify-squad .ss-mini {')
    expect(i).toBeGreaterThan(-1)
    expect(CSS.slice(i, i + 120)).toMatch(/animation:\s*none/)
  })
})

/**
 * **로그아웃과 회원 탈퇴가 안 붙어 있다** (사용자 지적, 2026-09-18: 「너무
 * 붙어있어」).
 *
 * 🔴 알약은 테두리가 둥글어 **가장자리끼리 가까워 보이는 거리가 실제 간격보다
 * 짧다** — 네모 단추와 같은 값을 주면 한 덩어리로 읽히고, 그러면 탈퇴를
 * 누르려다 로그아웃을 누른다. 눈으로만 맞춘 값이라 시험이 붙든다.
 */
describe('계정 판의 단추 두 개', () => {
  const block = () =>
    CSS.slice(
      CSS.indexOf('.ss-profile-account-foot {'),
      CSS.indexOf('.ss-profile-account-foot {') + 200,
    )

  /* 🔴 **양쪽 끝이 다 틀렸던 값이다.** 좁으면 한 덩어리로 읽히고(4px),
     넓히면 오른쪽 정렬이라 **로그아웃만 왼쪽으로 밀려난다**(18px). 둘 다
     사용자가 화면으로 잡아 줬으므로 범위로 붙든다. */
  it('로그아웃과 회원 탈퇴 사이를 살짝만 띄운다', () => {
    const gap = /gap:\s*(\d+)px/.exec(block())
    expect(gap).not.toBeNull()
    expect(Number(gap![1])).toBeGreaterThanOrEqual(10)
    expect(Number(gap![1])).toBeLessThanOrEqual(14)
  })

  /* 오른쪽 정렬이라 줄을 안 바꾸면 **왼쪽 것(로그아웃)이 판 밖으로** 밀린다. */
  it('좁은 화면에서는 줄을 바꾼다', () => {
    expect(block()).toMatch(/flex-wrap:\s*wrap/)
  })
})

/**
 * **팀 줄의 「수정」·「팀 나가기」** (사용자 지적, 2026-09-18).
 *
 * 두 번 되돌아온 자리다 — 처음엔 줄 간격(14px)만 있어 **너무 떨어져** 있었고,
 * 상자를 넣고 `gap` 을 안 써서 이번엔 **완전히 맞붙었다.**
 */
describe('팀 줄의 단추 두 개', () => {
  const acts = () =>
    CSS.slice(
      CSS.indexOf('.ss-profile-team-acts {'),
      CSS.indexOf('.ss-profile-team-acts {') + 160,
    )

  it('붙지도 멀지도 않게 띄운다', () => {
    const gap = /gap:\s*(\d+)px/.exec(acts())
    expect(gap).not.toBeNull()
    // 0 이면 맞붙고, 줄 간격(14px) 이상이면 묶은 뜻이 없다.
    expect(Number(gap![1])).toBeGreaterThanOrEqual(6)
    expect(Number(gap![1])).toBeLessThan(14)
  })

  /* 🔴 같은 특이도(0,1,0)라 **뒤에 적힌 것이 이긴다.** 앞에 두면 흰색이
     한 번도 안 먹는다 — 이 저장소가 두 번 밟은 함정이다. */
  it('흰색 「수정」 규칙이 빨간 기본 규칙보다 뒤에 온다', () => {
    const base = CSS.indexOf('.ss-profile-team-leave {')
    const edit = CSS.indexOf('.ss-profile-team-edit {')
    expect(base).toBeGreaterThan(-1)
    expect(edit).toBeGreaterThan(base)
  })

  /* 빨강은 되돌릴 수 없는 손짓의 색이다 — 수정이 그 색을 쓰면 안 된다. */
  it('「수정」은 위험 색을 안 쓴다', () => {
    const block = CSS.slice(
      CSS.indexOf('.ss-profile-team-edit {'),
      CSS.indexOf('.ss-profile-team-edit:not('),
    )
    expect(block).toMatch(/color:\s*#fff/)
    expect(block).not.toMatch(/--ss-danger/)
  })
})

/**
 * **카드 그림이 끌려 나오지 않는다** (사용자 지적, 2026-09-18).
 *
 * 🔴 `PlayerCardView` 의 `draggable={false}` 가 본 막음이고, 이 규칙은 그
 * 속성을 빠뜨린 `<img>` 가 새로 생겨도 같은 일이 안 나게 하는 그물이다.
 * `user-select: none` 은 **글자 선택만** 막아서 여기에 쓸 수 없다.
 */
describe('카드 사진은 브라우저가 끌어가지 못한다', () => {
  it('`.ss-pcard-figure img` 가 네이티브 드래그를 끈다', () => {
    const i = CSS.indexOf('.ss-pcard-figure img {')
    expect(i).toBeGreaterThan(-1)
    /* 🔴 **`}` 로 끝을 찾으면 안 된다** — 이 규칙의 주석 안에
       `draggable={false}` 가 들어 있어 거기서 잘린다. 줄머리의 `}` 가
       블록의 끝이다. */
    expect(CSS.slice(i, CSS.indexOf('\n}', i))).toMatch(/-webkit-user-drag:\s*none/)
  })
})

/**
 * 🔴 **미결 `paik` 48번** (2026-09-22 해소).
 *
 * `data-photo='full'` 은 「인물 칸이 **카드 전체**를 덮는다」고 주석에 적혀
 * 있었는데, `top`·`bottom` 만 0 으로 풀고 기본 규칙의 `inset-inline: 16%` 를
 * 안 풀어서 실제로는 **폭 68% 짜리 띠**였다. 키우거나 옮겨도 그 띠 안에서만
 * 움직였다 — 앱 실기기에서 사용자가 잡아 줬다(앱이 이 CSS 를 픽셀 동일로
 * 옮겨 왔다).
 *
 * 🔴 **앱과 짝이다** — `flutter/.../player_card_style_test.dart` 의
 * 「full 은 카드 전체를 덮는다」가 같은 것을 반대편에서 붙든다.
 */
describe('사진을 통째로 까는 모드는 카드 전체를 덮는다', () => {
  const rule = CSS.match(
    /\.ss-pcard\[data-photo='full'\]\s+\.ss-pcard-figure\s*\{([^}]*)\}/,
  )

  it('그 규칙이 있다', () => {
    expect(rule).not.toBeNull()
  })

  it.each(['top', 'bottom', 'inset-inline'])('%s 를 0 으로 푼다', (prop) => {
    expect(rule![1]).toMatch(new RegExp(`${prop}:\\s*0`))
  })

  /* 기본 규칙은 여전히 16% 여야 한다 — cutout 은 **일부러 좁다**(글자가
     위에 앉을 자리). 같이 0 으로 밀면 사진이 별명·머리글을 덮는다. */
  it('기본(cutout) 칸은 좌우 16% 그대로다', () => {
    const base = CSS.match(/\n\.ss-pcard-figure\s*\{([^}]*)\}/)
    expect(base![1]).toMatch(/inset-inline:\s*16%/)
  })
})
