'use client'

import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

/** 안내가 떠 있는 시간(아무도 안 누르면). 로그인 화면의 「시연영상을 참고해 주세요」와 같다. */
export const NUDGE_MS = 5000
/** 다 나오는 시간 — 이 전에 누른 것은 걷지 않는다. CSS `ss-demo-in` 길이와 같다. */
export const NUDGE_IN_MS = 600
/** 걷히는 시간 — CSS `ss-demo-out` 길이와 같다. */
const NUDGE_OUT_MS = 600
type Hole = { top: number; left: number; width: number; height: number; r: number }

/**
 * 요소 하나가 **실제로 칠한 자리**. 글자만 든 요소(「내 프로필」)는 상자가 아니라
 * **글자가 차지한 폭**만 — 상자로 뚫으면 글자 둘레의 배경까지 밝게 남는다.
 * 모서리는 그 요소의 둥글기를 따르되 축소(transform)만큼 줄인다.
 */
function holeOf(el: Element): Hole | null {
  const box = el.getBoundingClientRect()
  if (box.width <= 0) return null
  // 글자 폭으로 뚫는 것은 **맨 글자**일 때만 — 테두리나 바탕이 있는 상자(프로필의
  // 빈 얼굴 「홍」, 「프로필 카드 수정」 단추)는 글자만 든 요소여도 상자째 뚫는다.
  const cs = getComputedStyle(el)
  const bare =
    (parseFloat(cs.borderTopWidth) || 0) === 0 &&
    (cs.backgroundColor === 'transparent' || cs.backgroundColor === 'rgba(0, 0, 0, 0)') &&
    (cs.backgroundImage === 'none' || cs.backgroundImage === '')
  if (bare && el.children.length === 0 && el.textContent?.trim()) {
    const range = document.createRange()
    range.selectNodeContents(el)
    // jsdom 등 Range 의 상자를 못 재는 곳에서는 요소 상자로 떨어진다.
    const t = typeof range.getBoundingClientRect === 'function' ? range.getBoundingClientRect() : null
    if (t && t.width > 0) return { top: t.top, left: t.left, width: t.width, height: t.height, r: 2 }
  }
  const css = parseFloat(cs.borderTopLeftRadius) || 0
  const scale = el instanceof HTMLElement && el.offsetWidth ? box.width / el.offsetWidth : 1
  // 🔴 **둥글기는 짧은 변의 절반까지만.** 알약 단추는 `border-radius: 999px` 라
  // 그대로 SVG 의 rx 로 주면 브라우저가 가로·세로를 **따로** 줄여 구멍이 알약이
  // 아니라 **타원**이 됐다(「프로필 카드 수정」 안쪽에 타원이 비침 — 사용자 지적).
  const r = Math.min(css * scale, box.width / 2, box.height / 2)
  return { top: box.top, left: box.left, width: box.width, height: box.height, r }
}

/**
 * 한 곳만 밝게 두고 나머지를 어둡게 하며 그 밑에 한 줄을 띄운다 — 로그인
 * 화면의 「시연영상을 참고해 주세요」와 **같은 동작**(사용자 요청, 2026-09-19).
 * 스르르 나오고, 다 나온 뒤 어디든 한 번 누르거나 5초가 지나면 함께 걷힌다.
 *
 * - 어둠은 **구멍 뚫린 판**(SVG 마스크)이다. 과녁을 어둠 위로 끌어올리는
 *   방식(z-index)은 못 쓴다 — 과녁이 헤더의 쌓임 맥락 안에 있어서 밖의 판보다
 *   위로 못 나온다
 * - 🔴 **구멍은 과녁마다 따로, 딱 그 모양만**(사용자 정정). 처음엔 카드와 글자를
 *   감싸는 상자 하나를 넉넉히 뚫어서 **카드 둘레의 배경까지 밝은 네모**로 남았다.
 *   카드는 카드 모양(둥근 모서리 그대로), 글자는 글자가 칠한 폭만 뚫는다
 * - 판은 **누르는 것을 가로채지 않는다** — 밝게 남긴 「내 프로필」을 누르면 그대로
 *   간다. 걷는 것은 창에서 듣기만 한다
 * - 과녁이 움직여도(등장 연출) 따라가게 프레임마다 잰다
 * - `document.body` 로 옮겨 그린다 — 부른 쪽(스쿼드 판)의 transform·쌓임에 안 묶인다
 */
export default function SpotNudge({
  targets,
  message,
  onDone,
  note = 'below',
}: {
  /** 밝게 남길 요소들의 CSS 선택자. 하나도 못 찾으면 가운데에 문장만 띄운다. */
  targets: string[]
  message: string
  onDone: () => void
  /**
   * 문장 자리 — `below` 는 구멍들 밑 가운데, `right` 는 **마지막 과녁의 오른쪽**
   * 세로 가운데(프로필의 「프로필 카드 수정」 옆, 사용자 요청).
   */
  note?: 'below' | 'right'
}) {
  const [state, setState] = useState<'in' | 'on' | 'out'>('in')
  const [holes, setHoles] = useState<Hole[]>([])
  const [notePos, setNotePos] = useState<{ top: number; left: number } | null>(null)
  const noteRef = useRef<HTMLParagraphElement>(null)
  const doneRef = useRef(onDone)
  useEffect(() => {
    doneRef.current = onDone
  })

  useEffect(() => {
    if (state === 'in') {
      const t = setTimeout(() => setState('on'), NUDGE_IN_MS)
      return () => clearTimeout(t)
    }
    if (state === 'on') {
      const t = setTimeout(() => setState('out'), NUDGE_MS - NUDGE_IN_MS)
      const dismiss = () => setState('out')
      window.addEventListener('pointerdown', dismiss, true)
      return () => {
        clearTimeout(t)
        window.removeEventListener('pointerdown', dismiss, true)
      }
    }
    const t = setTimeout(() => doneRef.current(), NUDGE_OUT_MS)
    return () => clearTimeout(t)
  }, [state])

  const key = targets.join(',')
  useLayoutEffect(() => {
    let raf = 0
    let last = ''
    const measure = () => {
      const next = key
        .split(',')
        .map((sel) => document.querySelector(sel))
        .map((el) => (el ? holeOf(el) : null))
        .filter((h): h is Hole => h !== null)
      // 문장은 구멍들 밑 가운데 — 단 창 밖으로 안 나가게 양옆 16px 안으로 밀어 넣는다
      // (「내 프로필」은 오른쪽 끝이라 그대로 두면 문장 반이 잘린다).
      const w = noteRef.current?.offsetWidth ?? 0
      const nh = noteRef.current?.offsetHeight ?? 0
      let pos: { top: number; left: number }
      const tail = next[next.length - 1]
      if (note === 'right' && tail) {
        // 문장의 **가운데**가 left 에 오도록(CSS 가 -50% 로 당긴다) 반 폭을 더한다.
        pos = { top: tail.top + tail.height / 2 - nh / 2, left: tail.left + tail.width + 16 + w / 2 }
      } else {
        const lo = Math.min(...next.map((h) => h.left))
        const hi = Math.max(...next.map((h) => h.left + h.width))
        const center = next.length ? (lo + hi) / 2 : window.innerWidth / 2
        const bottom = next.length ? Math.max(...next.map((h) => h.top + h.height)) + 14 : window.innerHeight / 2
        pos = { top: bottom, left: center }
      }
      pos.left = Math.min(Math.max(pos.left, w / 2 + 16), window.innerWidth - w / 2 - 16)
      const sig = next.map((h) => `${h.top}|${h.left}|${h.width}|${h.height}`).join(';') + `#${pos.top}|${pos.left}`
      if (sig !== last) {
        last = sig
        setHoles(next)
        setNotePos(pos)
      }
      raf = requestAnimationFrame(measure)
    }
    measure()
    return () => cancelAnimationFrame(raf)
  }, [key, note])

  return createPortal(
    <>
      <svg aria-hidden="true" className="ss-nudge-dim" data-state={state} width="100%" height="100%">
        <defs>
          <mask id="ss-nudge-mask">
            <rect width="100%" height="100%" fill="white" />
            {holes.map((h, i) => (
              <rect key={i} x={h.left} y={h.top} width={h.width} height={h.height} rx={h.r} ry={h.r} fill="black" />
            ))}
          </mask>
        </defs>
        <rect width="100%" height="100%" className="ss-nudge-shade" mask="url(#ss-nudge-mask)" />
      </svg>
      <p
        ref={noteRef}
        role="status"
        className="ss-nudge-note"
        data-state={state}
        style={{ top: notePos?.top ?? '50%', left: notePos?.left ?? '50%' }}
      >
        {message}
      </p>
    </>,
    document.body,
  )
}
