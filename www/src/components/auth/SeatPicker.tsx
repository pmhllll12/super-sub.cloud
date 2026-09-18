'use client'

import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

/** 판이 닫히며 걷히는 시간 — CSS `ss-seat-out` 길이와 같아야 한다. */
const CLOSE_MS = 220

/**
 * 테스트 번호 고르기 — 작은 알약 하나, 누르면 **오른쪽으로** 번호 판이 스르르
 * 펼쳐진다(1~5 / 6~10 두 줄). 사용자 요청(2026-09-18).
 *
 * 🔴 **브라우저 기본 `<select>` 를 쓰지 않는다.** 맥에서는 운영체제 메뉴가 떠서
 * 알약 위에 겹쳐 덮이고 모양을 못 바꾼다(「겹치기도 하고 안 예쁘다」).
 *
 * 🔴 **판은 `document.body` 로 옮겨(portal) `position: fixed` 로 알약 옆에 띄운다.**
 * - 폼 칸이 `overflow-y: auto` 라 그 안에 `absolute` 로 두면 옆으로 넘치는 판이
 *   **잘린다**(overflow-y 를 주면 가로도 잘린다)
 * - 폼 칸 안에 `fixed` 로 두어도 안 된다 — 폼 칸의 `backdrop-filter` 가 `fixed`
 *   의 기준 상자를 **그 칸으로** 바꿔서 판이 화면 밖(x 1943)으로 갔다(헤드리스로 잼)
 * 열 때·창이 바뀔 때 알약 자리를 재서 옮긴다.
 */
export default function SeatPicker({
  seat,
  seats,
  onPick,
  label,
}: {
  seat: number | null
  seats: number[]
  onPick: (n: number) => void
  label: string
}) {
  const [state, setState] = useState<'closed' | 'open' | 'closing'>('closed')
  const [at, setAt] = useState<{ top: number; left: number } | null>(null)
  const pillRef = useRef<HTMLButtonElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const open = state === 'open'

  const close = () => setState((s) => (s === 'open' ? 'closing' : s))

  useEffect(() => {
    if (state !== 'closing') return
    const t = setTimeout(() => setState('closed'), CLOSE_MS)
    return () => clearTimeout(t)
  }, [state])

  // 알약 오른쪽 가운데에 판의 왼쪽 가운데를 맞춘다.
  useLayoutEffect(() => {
    if (state === 'closed') return
    const place = () => {
      const r = pillRef.current?.getBoundingClientRect()
      if (r) setAt({ top: r.top + r.height / 2, left: r.right + 8 })
    }
    place()
    window.addEventListener('resize', place)
    window.addEventListener('scroll', place, true)
    return () => {
      window.removeEventListener('resize', place)
      window.removeEventListener('scroll', place, true)
    }
  }, [state])

  // 바깥을 누르거나 Esc 면 닫는다.
  useEffect(() => {
    if (!open) return
    const onDown = (e: PointerEvent) => {
      const t = e.target as Node
      if (pillRef.current?.contains(t) || panelRef.current?.contains(t)) return
      close()
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        close()
        pillRef.current?.focus()
      }
    }
    window.addEventListener('pointerdown', onDown, true)
    window.addEventListener('keydown', onKey)
    return () => {
      window.removeEventListener('pointerdown', onDown, true)
      window.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div className="ss-seat">
      <span>{label}</span>
      <button
        ref={pillRef}
        type="button"
        className="ss-seat-pill"
        aria-label={`${label} ${seat === null ? '자동' : `${seat}번`}`}
        aria-expanded={open}
        onClick={() => (open ? close() : setState('open'))}
      >
        {seat === null ? '자동' : `${seat}번`}
        <svg aria-hidden="true" viewBox="0 0 12 12" className="ss-seat-caret">
          <path d="M4.5 3 7.5 6l-3 3" />
        </svg>
      </button>
      {state !== 'closed' &&
        at &&
        createPortal(
          <div
            ref={panelRef}
            role="group"
            aria-label={`${label} 고르기`}
            className="ss-seat-panel"
            data-state={state}
            style={{ top: at.top, left: at.left }}
          >
            {seats.map((n) => (
              <button
                key={n}
                type="button"
                className="ss-seat-num"
                aria-pressed={n === seat}
                onClick={() => {
                  onPick(n)
                  close()
                }}
              >
                {n}번
              </button>
            ))}
          </div>,
          document.body,
        )}
    </div>
  )
}
