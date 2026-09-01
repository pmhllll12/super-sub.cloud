'use client'

import { useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'
import FigureBackground from '@/components/FigureBackground'
import { useLeaving, useLeavingTo } from '@/lib/pageTransition'

/**
 * 로그인 뒤 모든 화면에 깔리는 배경 사진 — **화면이 바뀌면 사진도 바뀐다.**
 *
 * ## 🔴 제자리에서 녹지 않고 **밀려난다**
 *
 * 처음에는 두 장을 겹쳐 두고 불투명도만 바꿨다(크로스페이드). 그런데 이 앱은
 * 이미 **"들어온 방향 그대로 되나간다"** 는 문법을 갖고 있다 — 내용은 옆으로
 * 밀려 나가는데 배경만 제자리에서 녹으면 두 층이 따로 논다(사용자 지적).
 *
 * 그래서 배경도 같이 흐른다:
 *
 * ```
 *   누른 순간            지금 사진이 왼쪽으로 밀려 나간다   (LEAVE_MS 동안)
 *   화면이 갈리는 순간    새 사진이 오른쪽에서 밀고 들어온다
 * ```
 *
 * 🔴 **갈 곳의 배경이 지금과 같으면 아무것도 안 한다.** 같은 사진이 나갔다
 * 들어오면 이유 없이 깜빡인 것으로 보인다. 그래서 목적지를 알아야 하고,
 * 그것만을 위해 전환 provider 가 `leavingTo` 를 내놓는다.
 *
 * 🔴 **나가는 표시는 상태로 들고 있는다**(`leaving` 에서 파생하지 않는다).
 * 화면이 갈리는 순간 `leaving` 은 거짓이 되는데, 그때 파생값으로 두면 나가던
 * 사진이 **제자리로 튕겨 돌아와** 새 사진 옆에 잠깐 비친다.
 *
 * 🔴 **루트 레이아웃에서 딱 한 번 그린다.** 홈과 `(app)` 이 각자 그리던 때는
 * 화면이 갈릴 때 이 컴포넌트가 **새로 태어나서**, 태어날 때 이미 제자리인
 * 사진에 들어오는 연출이 붙지 않았다 — 나가는 쪽만 밀리고 들어오는 쪽은 그냥
 * 나타났다(사용자 지적). 한 번만 그리면 라우팅을 건너 살아남아 두 쪽이 다 산다.
 *
 * 🔴 다 지나간 장은 **걷어낸다.** 안 걷으면 화면을 옮겨 다닐수록 장이 쌓여서
 * 같은 사진을 몇 겹씩 그리게 된다.
 */

/**
 * 사진이 들어오고 나가는 데 걸리는 시간.
 *
 * 🔴 나가는 쪽은 `pageTransition` 의 `LEAVE_MS`(900) 와 **같아야 한다** —
 * 내용이 다 빠져나간 순간에 배경도 다 빠져나가 있어야 한 동작으로 읽힌다.
 */
const MOVE_MS = 900

/**
 * 사진이 다 지나간 **뒤에도** 이 층을 얼마나 더 붙들고 있는가.
 *
 * 🔴 배경 글자가 한 자씩 차례로 날아 들어오느라(FigureBackground) 사진보다
 * 늦게 끝난다. 사진 시간에 맞춰 걷어 버리면 마지막 글자들이 **가다 말고 제자리로
 * 튕긴다** — 부드럽게 오다가 휙 꽂히는 것으로 보인다(사용자 지적).
 * 사진 쪽 연출은 `both` 로 채워져 있어 더 붙들고 있어도 달라지는 것이 없다.
 */
const MARK_TAIL_MS = 560

type Phase = 'idle' | 'in' | 'out'
type Figure = {
  src: string
  position?: string
  /** 사람만 오려 낸 그림 — 큰 글자를 사람 **뒤로** 보내려면 필요하다. */
  cutout?: string
  /** 배경에 크게 깔리는 글자. */
  mark?: string[]
  /** 화면 끝까지 채운다 — 아래를 검게 잦아들게 하지 않는다. */
  bleed?: boolean
  phase: Phase
}

const DEFAULT_FIGURE = { src: '/home_figure.jpg' }

/**
 * 경로 앞머리로 고른다. 🔴 **여기 한 곳에서만 정한다** — 페이지마다 배경을
 * 심으면 새 페이지를 만들 때마다 빠뜨린다.
 */
const BY_PREFIX: { prefix: string; figure: Omit<Figure, 'phase'> }[] = [
  // 레슨 · 상점. 인물이 가운데에서 오른쪽에 있어 그만큼 밀어 둔다.
  {
    prefix: '/market',
    figure: {
      src: '/market_figure.jpg',
      /**
       * 🔴 세로는 **위에 맞춘다**(`top`). 사진 비율(1.4:1)이 화면 상자
       * (2:1 남짓)보다 세로로 길어서 `cover` 가 위아래를 잘라내는데,
       * `center` 로 두면 **머리가 잘렸다**. 위에 맞추면 잘리는 것은 늘
       * 아래쪽이고, 아래는 어차피 검게 잦아드는 자리다.
       *
       * 사진과 누끼 원본에 머리 위 여백을 260px 붙여 두었다 — 그래야
       * 헤더(워드마크 · 목적지 글자) 밑으로 머리가 들어온다.
       */
      position: '58% top',
      /**
       * 🔴 **손으로 딴 누끼다**(일러스트레이터). 자동 분리
       * (`scripts/cutout.swift`, macOS Vision)도 만들어 봤는데 머리카락을
       * 뭉텅 잘라내 가장자리가 부자연스러웠다 — 화면 위쪽에 크게 깔리는
       * 그림이라 그 가장자리가 곧 품질이다.
       *
       * `.ai` 는 PDF 호환이라 `scripts/ai-to-png.swift` 로 투명도를 살려
       * 뽑았고, 배경 사진과 **같은 비율 · 같은 자리**가 되게 위 여백을
       * 똑같이 얹었다(사진 70px 기준). 한쪽만 어긋나면 오려 낸 사람이
       * 원본에서 유령처럼 겹쳐 보인다.
       */
      cutout: '/market_cutout.webp',
      // 🔴 **한 줄**이다. 화면 폭보다 길게 잡아 양끝이 잘려 나가는 것이 이
      // 연출의 핵심이다(레퍼런스: ELITE COURT SUPPLIES) — 다 읽히는 글자는
      // 배경이 아니라 제목이 되어 본문과 다툰다.
      mark: ['TRAIN & GEAR UP'],
      // 🔴 아래를 검게 잦아들게 하지 않는다(사용자 요청). 이 사진은 아랫부분이
      // 인물의 몸이라, 막을 씌우면 화면 아래에 검은 띠가 앉은 것으로 보였다.
      bleed: true,
    },
  },
]

/**
 * 배경 층을 **깔지 않는** 화면들.
 *
 * 🔴 로그인 · 회원가입(`AuthShell`)은 자기 배경을 `-z-10` 에 따로 깐다. 이
 * 층은 `-1` 이라 그 위에 놓여 **그 화면의 배경을 덮어 버린다.** 공유 카드와
 * 관리자 화면도 배경 사진을 쓰지 않는다.
 */
const NO_FIGURE = ['/login', '/signup', '/c/', '/admin']

export function figureFor(pathname: string): Omit<Figure, 'phase'> | null {
  if (NO_FIGURE.some((p) => pathname.startsWith(p))) return null
  return BY_PREFIX.find((r) => pathname.startsWith(r.prefix))?.figure ?? DEFAULT_FIGURE
}

export default function AppFigure() {
  const pathname = usePathname()
  const leaving = useLeaving()
  const leavingTo = useLeavingTo()
  const target = figureFor(pathname)

  /** 겹쳐 둔 장들. 마지막이 맨 위다. 배경이 없는 화면에서는 비어 있다. */
  const [layers, setLayers] = useState<Figure[]>(target ? [{ ...target, phase: 'idle' }] : [])
  const [shownSrc, setShownSrc] = useState<string | null>(target?.src ?? null)
  /** 이미 내보내기 시작한 목적지 — 같은 클릭에 두 번 내보내지 않는다. */
  const [sentFor, setSentFor] = useState<string | null>(null)

  /**
   * 🔴 상태를 맞추는 것은 **렌더 중**에 한다(effect 가 아니라).
   *
   * 바깥 값이 바뀌었을 때 상태를 따라가게 하는 React 의 정석 방식이다 —
   * effect 에서 setState 하면 한 번 그린 뒤 또 그리게 되고, 그 사이 한
   * 프레임 동안 아직 안 맞은 화면이 스친다.
   */

  // ① 누른 순간 — 갈 곳의 배경이 다르면 지금 사진을 내보내기 시작한다.
  //    배경이 **없는** 화면으로 가는 것도 "다름" 이다.
  const nextSrc = leavingTo !== null ? (figureFor(leavingTo)?.src ?? null) : null
  const goingElsewhere = leaving && leavingTo !== null && nextSrc !== shownSrc
  if (goingElsewhere && sentFor !== leavingTo) {
    setSentFor(leavingTo)
    setLayers((prev) => prev.map((l, i) => (i === prev.length - 1 ? { ...l, phase: 'out' } : l)))
  }

  // ② 화면이 갈린 순간 — 새 사진이 오른쪽에서 밀고 들어온다.
  if (shownSrc !== (target?.src ?? null)) {
    setShownSrc(target?.src ?? null)
    setSentFor(null)
    if (target) setLayers((prev) => [...prev, { ...target, phase: 'in' }])
  }

  // ③ 다 지나가면 맨 위 한 장만 남긴다(위 주석). 배경이 없는 화면이면 다 걷는다.
  useEffect(() => {
    const t = setTimeout(
      () =>
        setLayers((prev) =>
          shownSrc === null ? [] : prev.slice(-1).map((l) => ({ ...l, phase: 'idle' })),
        ),
      MOVE_MS + MARK_TAIL_MS,
    )
    return () => clearTimeout(t)
  }, [shownSrc])

  return (
    <>
      {layers.map((f) => (
        <FigureBackground
          key={f.src}
          src={f.src}
          position={f.position}
          cutout={f.cutout}
          mark={f.mark}
          bleed={f.bleed}
          className={`ss-app-figure ss-app-figure-${f.phase}`}
        />
      ))}
    </>
  )
}
