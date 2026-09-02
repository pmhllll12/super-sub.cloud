'use client'

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useLeaving } from '@/lib/pageTransition'
import { type Coach, type Product } from '@/lib/market'
import BlankPlayerCard from '@/components/BlankPlayerCard'
import CoachList from './coaches/CoachList'
import CoachDetail from './coaches/CoachDetail'
import ShopList from './ShopList'

/** 지금 오른쪽 판에 무엇이 펼쳐져 있나. */
type Kind = 'coaches' | 'shop'

/**
 * 흘러가는 강사 카드 줄을 **몇 벌** 늘어놓을 것인가.
 *
 * 🔴 **짝수**여야 한다(`-50%` 로 미는 이음매). 그리고 절반이 판 폭보다 넓어야
 * 한다 — 지금은 코치 3명 × 78px = 한 벌 234px 이라 여섯 벌의 절반이 702px 로,
 * 판이 가장 넓을 때(628px)보다 넉넉하다. **코치가 늘면 벌 수를 줄여도 된다.**
 */
const COACH_ROLL_COPIES = 6

/**
 * 상점의 흰 네모는 몇 벌인가. 조건은 위와 같다(짝수 · 절반이 판보다 넓을 것).
 * 상품 6개 × 78px = 한 벌 468px 이라 **네 벌**의 절반이 936px 이다.
 */
const SHOP_ROLL_COPIES = 4

/**
 * 두 문(왼쪽 판)과 그 옆으로 펼쳐지는 목록 판.
 *
 * 🔴 **'보기' 를 눌러도 화면을 떠나지 않는다**(사용자 요청). 왼쪽 판은 그대로
 * 두고 그 오른쪽 끝에서 화면 오른쪽 끝까지 판이 펼쳐지며, 목록은 거기에 다
 * 들어간다. 화면을 갈아 끼우면 왼쪽 판이 나갔다 다시 들어오느라 "옆칸이
 * 열렸다" 가 아니라 "다른 데로 갔다" 로 읽힌다.
 *
 * 그래서 이 컴포넌트가 클라이언트다 — 열림/닫힘은 화면 안의 상태지 주소가
 * 아니다. 목록에서 **코치 하나를 고르는 것**은 그때야 진짜 이동이라 그쪽은
 * 여전히 링크다(`CoachList`).
 *
 * 🔴 펼치는 연출은 `clip-path` 로 한다(globals.css). `width` 를 늘리면 그 동안
 * 안쪽 글이 계속 다시 접혀 글자가 춤춘다 — 오려내기는 배치를 건드리지 않는다.
 */
export default function MarketGates({
  coaches,
  products,
}: {
  coaches: Coach[]
  products: Product[]
}) {
  /**
   * 화면을 떠나는 중인가(워드마크를 눌러 홈으로 가는 길 등).
   *
   * 🔴 떠날 때 두 판은 **서로 반대쪽으로** 나간다(사용자 요청) — 왼쪽 판은
   * 왼쪽으로, 목록 판은 오른쪽으로. 한쪽으로 같이 나가면 두 판이 겹쳐 지나가고,
   * 그냥 사라지면 화면이 갈리는 것이 아니라 끊긴 것으로 보인다.
   * 다 나간 뒤에 라우팅이 일어난다 — 그 시각은 `pageTransition` 의 `LEAVE_MS`
   * (900ms)이고, 아래 나가는 시간(620ms)은 그 안에 들어와야 한다.
   */
  const leaving = useLeaving()
  const [open, setOpen] = useState<Kind | null>(null)
  /**
   * 🔴 닫히는 **동안에도** 내용이 남아 있어야 한다. `open` 만 보고 그리면 닫는
   * 순간 안이 비어, 펼쳐진 판이 빈 채로 접히는 것이 보인다.
   */
  const [shown, setShown] = useState<Kind>('coaches')

  /**
   * 도는 줄이 **멈춰 있는가.** '보기' 를 한 번이라도 누르면 그때부터 멈추고,
   * 그 자리에서 손으로 굴릴 수 있게 된다(사용자 요청).
   *
   * 목록을 닫으면 **다시 돌기 시작한다**(사용자 요청). 그때 맨 앞으로 튀지
   * 않도록, 손으로 맞춰 둔 자리를 애니메이션의 **시작 시각**으로 옮겨 준다
   * (`resume`). 멈출 때 한 일의 정확한 반대다.
   */
  const [frozen, setFrozen] = useState(false)
  /**
   * 판 안에서 펼쳐 본 코치. 🔴 **주소는 안 바뀐다**(사용자 요청) — 오른쪽 판에서
   * 무엇을 눌러도 그 판 안에서만 바뀌고 왼쪽 판은 그대로 있어야 한다.
   */
  const [coachId, setCoachId] = useState<string | null>(null)
  /** 판 안 굴림 자리. 목록 ↔ 상세를 오갈 때 맨 위에서 시작해야 한다. */
  const body = useRef<HTMLDivElement | null>(null)
  /**
   * 지금 이 화면 안에서 **몇 걸음 들어와 있나**(0 = 아무것도 안 열림).
   *
   * 🔴 판이 열리고 코치를 고르는 것은 주소를 안 바꾼다(사용자 요청). 그래서
   * 브라우저는 그걸 "간 곳"으로 치지 않고, **뒤로 가기를 누르면 화면을 통째로
   * 떠났다**(사용자 지적). 주소는 그대로 두고 **기록만 쌓아**(`pushState`)
   * 뒤로 가기가 이 걸음들을 거꾸로 되짚게 한다.
   *
   * 🔴 걸음 수를 기록 항목 안(`history.state`)에도 같이 넣는다. `ref` 만 믿으면
   * 뒤로 갔다가 다시 앞으로 왔을 때 어긋난다 — 정본은 기록 쪽이다.
   */
  const steps = useRef(0)
  /** 두 줄(레슨 · 상점)의 창. 멈출 때 굴림 자리를 여기에 직접 넣는다. */
  const rolls = useRef<(HTMLSpanElement | null)[]>([])
  /** 멈춘 순간 각 줄이 얼마나 밀려 있었나 — 그만큼을 굴림 자리로 옮겨 준다. */
  const frozenAt = useRef<number[]>([])

  /**
   * 🔴 **멈추기 전에** 지금 밀린 만큼을 읽어 둬야 한다. 멈추는 순간 애니메이션이
   * 사라져 `transform` 이 `none` 이 되므로, 상태를 바꾼 뒤에는 읽을 것이 없다.
   *
   * 밀림(transform)을 굴림 자리(scrollLeft)로 **바꿔 넣는** 것이 요령이다. 밀린
   * 채로 굴리게 두면 보이는 자리와 굴림 자리가 어긋나 끝에서 빈 자리가 나온다.
   */
  const freeze = () => {
    if (frozen) return
    frozenAt.current = rolls.current.map((win) => {
      const track = win?.firstElementChild
      if (!track) return 0
      const t = getComputedStyle(track).transform
      if (!t || t === 'none') return 0
      return -new DOMMatrixReadOnly(t).m41
    })
    setFrozen(true)
  }

  /**
   * 다시 돌리기 — 멈출 때의 반대다. 굴림 자리(scrollLeft)를 **애니메이션의 시작
   * 시각**으로 옮긴다.
   *
   * 🔴 `animation-delay` 를 **음수**로 준다. 그러면 애니메이션이 그만큼 이미
   * 지나간 상태에서 시작하므로, 지금 보이던 자리에서 이어서 흐른다. 그냥 다시
   * 켜면 무조건 처음(밀림 0)부터라 줄이 맨 앞으로 툭 튄다.
   *
   * 🔴 걸리는 시간은 인라인 변수에서 읽는다 — 멈춰 있는 동안에는
   * `animation-duration` 이 계산값으로 `0s` 라(애니메이션 자체가 꺼져 있다)
   * 그걸로 나누면 위상이 무한대가 된다.
   */
  const resume = useCallback(() => {
    if (!frozen) return
    rolls.current.forEach((win) => {
      const track = win?.firstElementChild as HTMLElement | null
      if (!win || !track) return
      const half = track.getBoundingClientRect().width / 2
      const seconds = parseFloat(track.style.getPropertyValue('--ss-roll-s')) || 24
      const phase = half > 0 ? (win.scrollLeft % half) / half : 0
      track.style.animationDelay = `${-phase * seconds}s`
      win.scrollTo({ left: 0, behavior: 'instant' })
    })
    setFrozen(false)
  }, [frozen])

  /**
   * 🔴 판 안의 화살표는 **한 걸음만 돌아간다**(사용자 지적) — 코치 상세에서
   * 누르면 그 코치를 편 걸음만 되짚어 **목록으로** 간다. 왼쪽을 가리키는
   * 화살표가 판을 통째로 닫으면 "돌아가기"가 아니라 "나가기"가 된다.
   *
   * 되돌리기는 직접 하지 않고 **기록을 되감아서** 한다 — 그래야 이 단추와
   * 브라우저 뒤로 가기가 같은 것을 가리킨다(실제 처리는 `popstate`).
   */
  const backOne = useCallback(() => {
    if (steps.current > 0) {
      window.history.back()
      return
    }
    resume()
    setOpen(null)
  }, [resume])

  /**
   * 판을 통째로 닫는다 — Esc 가 여기로 온다(덮는 판은 한 번에 물러날 길이
   * 있어야 한다).
   *
   * 🔴 들어온 걸음 수만큼 **한 번에** 되감는다(코치 상세에서 닫으면 두 걸음).
   * 상태만 바꾸고 기록을 두면, 그 뒤에 뒤로 가기를 눌렀을 때 이미 닫힌 판이
   * 한 번 더 닫히는 셈이 되어 아무 일도 안 일어난다.
   */
  const close = useCallback(() => {
    if (steps.current > 0) {
      window.history.go(-steps.current)
      return
    }
    resume()
    setOpen(null)
  }, [resume])

  /**
   * 🔴 **다시 태어나도 기록에 적힌 자리로 돌아온다.**
   *
   * 뒤로 가기를 받으면 라우터가 이 나무를 통째로 다시 그릴 수 있는데, 그러면 이
   * 컴포넌트의 상태(열림 · 보던 코치)가 처음값으로 돌아가 **판이 통째로 사라진다**
   * (사용자 지적). `popstate` 만으로는 못 막는다 — 다시 태어난 쪽이 이겨서다.
   * 그래서 태어날 때 기록(`history.state`)을 한 번 읽어 제자리를 찾는다.
   *
   * 🔴 첫 그림에서는 못 읽는다(서버에는 기록이 없다) — 그리고 나서 맞춘다.
   */
  useEffect(() => {
    const st = window.history.state as { ssMarket?: number; kind?: Kind; coach?: string | null } | null
    if (!st?.ssMarket) return
    steps.current = st.ssMarket
    /* eslint-disable react-hooks/set-state-in-effect */
    if (st.kind) setShown(st.kind)
    if (st.kind) setOpen(st.kind)
    setCoachId(st.coach ?? null)
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [])

  /**
   * 뒤로 가기(브라우저 · 손짓)를 받아 화면을 그 걸음에 맞춘다.
   *
   * 🔴 걸음이 0 인 항목까지 돌아왔으면 판을 닫는다. **그 아래로 더 누르면
   * 화면을 떠난다** — 그건 막지 않는다(사용자 요청: 뒤로 가기는 왔던 곳을
   * 역순으로 간다).
   */
  useEffect(() => {
    const onPop = (e: PopStateEvent) => {
      const st = (e.state ?? {}) as { ssMarket?: number; kind?: Kind; coach?: string | null }
      const depth = st.ssMarket ?? 0
      steps.current = depth
      if (depth === 0) {
        resume()
        setOpen(null)
        setCoachId(null)
        return
      }
      if (st.kind) {
        setShown(st.kind)
        setOpen(st.kind)
      }
      setCoachId(st.coach ?? null)
    }
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [resume])

  /**
   * 🔴 `useLayoutEffect` 다 — 그려지기 전에 자리를 잡아야 한다. 그린 뒤에 옮기면
   * 줄이 맨 앞으로 튀었다가 제자리로 오는 것이 한 프레임 보인다.
   * 🔴 `behavior: 'instant'` 도 필수다. 멈춘 줄에는 부드러운 굴림이 켜져 있어서
   * (globals.css) 그냥 넣으면 이 첫 자리잡기까지 스르륵 굴러간다.
   */
  useLayoutEffect(() => {
    if (!frozen) return
    rolls.current.forEach((win, i) => {
      win?.scrollTo({ left: frozenAt.current[i] ?? 0, behavior: 'instant' })
    })
  }, [frozen])


  /** 한 걸음 들어간다 — 주소는 그대로 두고 기록에 표시만 남긴다. */
  const step = (kind: Kind, coach: string | null) => {
    steps.current += 1
    window.history.pushState({ ssMarket: steps.current, kind, coach }, '')
  }

  const show = (kind: Kind) => {
    freeze()
    // 이미 열려 있으면 갈래만 갈아 끼우는 것이라 걸음이 늘지 않는다 — 그때
    // 뒤로 가기는 "판을 닫는다"가 되어야지 "아까 보던 갈래로"가 아니다.
    if (open) window.history.replaceState({ ssMarket: steps.current, kind, coach: null }, '')
    else step(kind, null)
    setShown(kind)
    setOpen(kind)
    // 다른 갈래를 열면 보던 코치는 접는다 — 상점을 열었는데 코치가 남아 있으면
    // 머리글과 안이 어긋난다.
    setCoachId(null)
  }

  /** 코치 하나를 편다 — 이것도 한 걸음이다. */
  const pick = (id: string) => {
    step(shown, id)
    setCoachId(id)
  }

  /** 지금 판이 그리는 것. 코치를 고르면 그 코치, 아니면 갈래의 목록이다. */
  const coach = coachId ? coaches.find((c) => c.id === coachId) : undefined

  // 판 안에서 무엇을 보든 **맨 위에서 시작한다** — 목록을 한참 내려가 있다가
  // 상세로 바뀌면 그 코치의 중간부터 보인다.
  useLayoutEffect(() => {
    body.current?.scrollTo({ top: 0, behavior: 'instant' })
  }, [coachId, shown])

  /**
   * 🔴 펼쳐져 있는 동안에는 **굴림이 문지기에게 가지 않는다**(`HeroGate`). 안
   * 그러면 목록을 위로 굴리다가 두 문까지 같이 나가 버린다. 표시로 알린다 —
   * 문지기는 레이아웃 밖 다른 컴포넌트라 상태를 나눠 가질 수가 없다.
   */
  useEffect(() => {
    const el = document.documentElement
    if (open) el.dataset.ssDetail = 'open'
    else delete el.dataset.ssDetail
    return () => {
      delete el.dataset.ssDetail
    }
  }, [open])

  /** 열려 있으면 Esc 로 닫는다 — 덮는 판에는 물러날 길이 늘 있어야 한다. */
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, close])

  return (
    <>
      {/* 🔴 두 문은 표지 글과 **같은 자리에 겹쳐** 있다. 굴러가는 화면이 아니라
          한 화면이므로, 표지 글이 나간 뒤 이 자리에 들어온다(globals.css).
          🔴 **판은 하나**이고 화면 왼쪽을 통째로 감싼다(사용자 요청) — 안에서
          레슨과 상점을 선 하나로 가른다. */}
      <div className="ss-market-gates" data-leaving={leaving}>
        <div
          className="ss-market-gate-wrap"
          style={{
            // 🔴 흐림(backdrop-filter)은 **인라인으로만** 준다. globals.css 에
            // 두면 같은 규칙의 `color-mix()` 탓에 Lightning CSS 가 규칙을
            // 통째로 떨어뜨려 계산값이 `none` 이 된다(작업 현황 §0.4).
            // 세기는 유리 판 기본값(`--ss-glass-blur` 20px)의 **80%**(16px)다 —
            // 절반(10px)으로는 뒤 인물의 결이 글자에 붙어 어수선했다(사용자 요청).
            backdropFilter:
              'blur(calc(var(--ss-glass-blur) * 0.8)) saturate(var(--ss-glass-saturate))',
          }}
        >
          {/* 🔴 갈래 전체는 **누르는 곳이 아니다**(사용자 요청). 누르는 곳은 아래
              '보기' 하나뿐이다 — 판 하나 안에 큰 과녁이 둘이면 어디를 눌러도
              무언가 열려, 판을 훑어보는 것과 고르는 것이 구분되지 않는다. */}
          <div className="ss-market-gate">
            <span className="ss-market-gate-kind">레슨</span>
            <strong>코치와 함께하는 레슨</strong>
            {/* 🔴 제목도 설명도 표지 글(`.ss-market-intro`)의 것을 **그대로**
                쓴다(사용자 요청) — 두 상태가 한 자리를 번갈아 쓰는데 같은 갈래를
                다른 말로 소개하면 자리가 바뀐 것이 아니라 다른 화면으로 읽힌다.
                줄바꿈 자리도 거기서 못 박은 그대로다. **고칠 땐 두 곳을 같이.** */}
            <p>
              유저들과 AI 분석을 통해 인정받은 코치에게
              <br />
              레슨을 신청하고 배워보세요.
            </p>
            {/* 🔴 강사들을 **선수 카드 틀 그대로** 끝없이 흘려보낸다(사용자 요청).
                누르는 곳이 아니라 "이런 사람들이 있다"는 표식이라 `+` 도 링크도
                없다 — 고르는 것은 아래 '코치 보기' 하나뿐이다.

                🔴 이어 붙이기: 같은 목록을 **여러 벌** 늘어놓고 track 을 정확히
                절반(`-50%`)만 밀면 끝과 처음이 맞물려 이음매가 안 보인다. 그래서
                (1) 벌 수는 **짝수**여야 하고 (2) 칸 사이는 `gap` 이 아니라 각
                카드의 **오른쪽 여백**이어야 한다 — `gap` 은 마지막 카드 뒤에는
                안 붙어서 절반이 한 주기와 어긋난다.
                (3) 절반(카드 9장 ≈ 702px)이 판 폭보다 넓어야 빈 자리가 안 생긴다.

                낭독기에는 통째로 감춘다 — 같은 이름을 여섯 번 읽게 된다. 목록은
                '코치 보기' 뒤에 제대로 있다. */}
            <span
              ref={(el) => {
                rolls.current[0] = el
              }}
              className="ss-market-gate-peek ss-market-gate-cards"
              data-frozen={frozen}
              aria-hidden="true"
            >
              <span
                className="ss-market-roll-track"
                style={{ '--ss-roll-s': '24s' } as React.CSSProperties}
              >
                {Array.from({ length: COACH_ROLL_COPIES }).flatMap((_, copy) =>
                  coaches.map((c) => (
                    <span key={`${copy}-${c.id}`} className="ss-market-coach-chip">
                      {/* ⚠️ `.ss-pcard-mini` 는 카드를 **직접 자식**으로 찾으므로
                          (`> .ss-pcard`) 사이에 다른 요소를 끼우면 축소가 풀린다. */}
                      <span
                        className="ss-pcard-mini"
                        style={{ '--ss-pcard-mini-w': 64 } as React.CSSProperties}
                      >
                        <BlankPlayerCard />
                      </span>
                      <b>{c.name}</b>
                    </span>
                  )),
                )}
              </span>
            </span>

            <button
              type="button"
              className="ss-market-gate-go"
              aria-expanded={open === 'coaches'}
              aria-controls="ss-market-detail"
              onClick={() => show('coaches')}
            >
              레슨 찾기
              {/* 닫기와 **같은 화살표**를 좌우만 뒤집어 쓴다(사용자 요청) —
                  글자 `→` 는 글꼴마다 굵기가 달라 옆 글자와 따로 논다. */}
              <span className="material-symbols-outlined" aria-hidden="true">
                chevron_forward
              </span>
            </button>
          </div>

          <hr className="ss-market-gate-rule" />

          <div className="ss-market-gate">
            <span className="ss-market-gate-kind">상점</span>
            <strong>스포츠 브랜드들이 한 곳에</strong>
            {/* 위와 같다 — 표지 글의 제목 · 설명 그대로다. */}
            <p>
              내가 원하는 스포츠 브랜드를 찾아보고
              <br />
              상품을 구매하세요.
            </p>
            {/* 🔴 아직 **자리 표시**다(사용자 요청) — 흰 정사각형만 돈다. 나중에
                브랜드 · 상품 그림이 이 자리에 들어오고, 도는 방식은 레슨 쪽과
                같은 것을 그대로 쓴다(위 이어 붙이기 주석 참고). 빠르기를 맞추려면
                절반 길이에 비례해 시간을 준다 — 936px 이라 24s × 2 다. */}
            <span
              ref={(el) => {
                rolls.current[1] = el
              }}
              className="ss-market-gate-peek ss-market-gate-cards"
              data-frozen={frozen}
              aria-hidden="true"
            >
              <span
                className="ss-market-roll-track"
                style={{ '--ss-roll-s': '32s' } as React.CSSProperties}
              >
                {Array.from({ length: SHOP_ROLL_COPIES }).flatMap((_, copy) =>
                  products.map((p) => (
                    <span key={`${copy}-${p.id}`} className="ss-market-roll-tile" />
                  )),
                )}
              </span>
            </span>
            <button
              type="button"
              className="ss-market-gate-go"
              aria-expanded={open === 'shop'}
              aria-controls="ss-market-detail"
              onClick={() => show('shop')}
            >
              상품 찾기
              {/* 닫기와 **같은 화살표**를 좌우만 뒤집어 쓴다(사용자 요청) —
                  글자 `→` 는 글꼴마다 굵기가 달라 옆 글자와 따로 논다. */}
              <span className="material-symbols-outlined" aria-hidden="true">
                chevron_forward
              </span>
            </button>
          </div>
        </div>
      </div>

      {/* 왼쪽 판의 오른쪽 끝에서 화면 오른쪽 끝까지. 자리는 CSS 가 잡는다
          (`--ss-market-panel-w` 하나가 두 판의 경계다). */}
      <div className="ss-market-detail-window">
        <aside
          id="ss-market-detail"
          className="ss-market-detail"
          data-open={open ? 'true' : 'false'}
          data-leaving={leaving}
          // 코치 상세는 제목이 **왼쪽**에서 시작해 닫기 단추와 같은 자리를 쓴다 —
          // 그때만 글을 단추 아래로 내린다(globals.css).
          data-coach={coach ? 'true' : 'false'}
          // 나가 있는 동안에는 화면 낭독기에도 없는 것이어야 한다 — 창 밖으로
          // 밀어 두는 것은 눈에만 안 보이게 할 뿐이라 낭독기는 다 읽는다.
          aria-hidden={!open}
        >
          <div className="ss-market-detail-body" ref={body}>
            {/* 🔴 돌아가는 단추는 **굴러가는 칸 안**에 있다(사용자 요청) — 밖에
                띄워 두면 글이 그 밑을 지나며 겹친다. 다만 놓는 자리가 갈래마다
                다르다:
                  목록 — 간판과 **같은 줄**(간판이 가운데라 안 겹친다)
                  상세 — 이름이 왼쪽에서 시작해 같은 줄에 못 둔다. 이름 위. */}
            {coach ? (
              /* 🔴 목록 화면(`/market/coaches/{id}`)과 **같은 알맹이**를 쓴다 —
                 다른 것은 머리글과 돌아가는 길뿐이다. 영상 링크는 끈다: 판 안에서
                 누르면 화면이 통째로 갈려 "이 판에서만 바뀐다"가 깨진다. */
              <>
              <button
                type="button"
                className="ss-market-detail-close"
                onClick={backOne}
                // 하는 일이 자리마다 다르므로 이름도 다르다 — 낭독기는 이 말만 읽는다.
                aria-label="코치 목록으로"
              >
                <span className="material-symbols-outlined" aria-hidden="true">
                  chevron_backward
                </span>
              </button>
              <CoachDetail coach={coach} video={false} />
              </>
            ) : (
              <>
                {/* 🔴 꼬리표와 한글 제목을 빼고 **간판 한 줄**만 둔다(사용자 요청).
                    글꼴은 배경 아치(TRAIN & GEAR UP)와 같은 것(`--font-poster`,
                    Shrikhand)이라 두 화면이 한 목소리로 읽힌다. 상점 쪽도 같은
                    짜임이라 짝이 되는 말을 쓴다. */}
                <div className="ss-market-detail-topline">
                  <button
                    type="button"
                    className="ss-market-detail-close"
                    onClick={backOne}
                    aria-label={coach ? '코치 목록으로' : '목록 닫기'}
                  >
                    <span className="material-symbols-outlined" aria-hidden="true">
                      chevron_backward
                    </span>
                  </button>
                  <div className="ss-market-detail-head">
                    {/* ⚠️ 상점 쪽 간판은 **BEST SELLERS**(복수)다 — 목록을 이끄는
                        말이라 한 상품을 가리키는 단수(BEST SELLER)가 아니다.
                        ⚠️ 다만 지금 목록은 **잘 팔린 순이 아니다**(mock 이라 판매
                        수가 없다). 판매 수가 생기면 그 순서로 세워야 이 말이
                        사실이 된다 — 미결로 둔다. */}
                    <h2>{shown === 'shop' ? 'BEST SELLERS' : 'FIND YOUR COACH'}</h2>
                  </div>
                </div>
                {shown === 'shop' ? (
                  <ShopList products={products} />
                ) : (
                  /* 고르면 **이 판 안에서** 상세로 바뀐다 — 화면을 갈지 않는다. */
                  <CoachList coaches={coaches} onPick={pick} />
                )}
              </>
            )}
          </div>
        </aside>
      </div>
    </>
  )
}
