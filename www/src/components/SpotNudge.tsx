'use client'

import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

/** 안내가 떠 있는 시간(아무도 안 누르면). 로그인 화면의 「시연영상을 참고해 주세요」와 같다. */
export const NUDGE_MS = 5000
/** 다 나오는 시간 — 이 전에 누른 것은 걷지 않는다. CSS `ss-demo-in` 길이와 같다. */
export const NUDGE_IN_MS = 600
/** 걷히는 시간 — CSS `ss-demo-out` 길이와 같다. */
const NUDGE_OUT_MS = 600
/** 밝게 남기는 구멍이 과녁보다 이만큼 넉넉하다. */
const HOLE_PAD = 8

type Box = { top: number; left: number; width: number; height: number }

/**
 * 한 곳만 밝게 두고 나머지를 어둡게 하며 그 밑에 한 줄을 띄운다 — 로그인
 * 화면의 「시연영상을 참고해 주세요」와 **같은 동작**(사용자 요청, 2026-09-19).
 * 스르르 나오고, 다 나온 뒤 어디든 한 번 누르거나 5초가 지나면 함께 걷힌다.
 *
 * - 어둠은 과녁 둘레에 **구멍을 뚫은 판**이다(구멍 상자의 큰 그림자). 과녁을
 *   어둠 위로 끌어올리는 방식(z-index)은 못 쓴다 — 과녁이 헤더의 쌓임 맥락 안에
 *   있어서 밖의 판보다 위로 못 나온다
 * - 판은 **누르는 것을 가로채지 않는다** — 밝게 남긴 「내 프로필」을 누르면 그대로
 *   간다. 걷는 것은 창에서 듣기만 한다
 * - 과녁이 움직여도(등장 연출) 따라가게 프레임마다 잰다
 * - `document.body` 로 옮겨 그린다 — 부른 쪽(스쿼드 판)의 transform·쌓임에 안 묶인다
 */
export default function SpotNudge({
  target,
  message,
  onDone,
}: {
  /** 밝게 남길 요소를 찾는 CSS 선택자. 못 찾으면 가운데에 문장만 띄운다. */
  target: string
  message: string
  onDone: () => void
}) {
  const [state, setState] = useState<'in' | 'on' | 'out'>('in')
  const [hole, setHole] = useState<Box | null>(null)
  const [noteLeft, setNoteLeft] = useState<number | null>(null)
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

  useLayoutEffect(() => {
    let raf = 0
    let last = ''
    const measure = () => {
      const r = document.querySelector(target)?.getBoundingClientRect()
      const next =
        r && r.width > 0
          ? {
              top: r.top - HOLE_PAD,
              left: r.left - HOLE_PAD,
              width: r.width + HOLE_PAD * 2,
              height: r.height + HOLE_PAD * 2,
            }
          : null
      // 문장은 구멍 밑 가운데 — 단 창 밖으로 안 나가게 양옆 16px 안으로 밀어 넣는다
      // (「내 프로필」은 오른쪽 끝이라 그대로 두면 문장 반이 잘린다).
      const w = noteRef.current?.offsetWidth ?? 0
      const center = next ? next.left + next.width / 2 : window.innerWidth / 2
      const left = Math.min(Math.max(center, w / 2 + 16), window.innerWidth - w / 2 - 16)
      const key = next ? `${next.top}|${next.left}|${next.width}|${next.height}|${left}` : `-|${left}`
      if (key !== last) {
        last = key
        setHole(next)
        setNoteLeft(left)
      }
      raf = requestAnimationFrame(measure)
    }
    measure()
    return () => cancelAnimationFrame(raf)
  }, [target])

  return createPortal(
    <>
      <div
        aria-hidden="true"
        className="ss-nudge-dim"
        data-state={state}
        style={
          hole
            ? { top: hole.top, left: hole.left, width: hole.width, height: hole.height }
            : { top: '50%', left: '50%', width: 0, height: 0 }
        }
      />
      <p
        ref={noteRef}
        role="status"
        className="ss-nudge-note"
        data-state={state}
        style={{
          top: hole ? hole.top + hole.height + 12 : '50%',
          left: noteLeft ?? '50%',
        }}
      >
        {message}
      </p>
    </>,
    document.body,
  )
}
