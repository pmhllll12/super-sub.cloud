'use client'

import { useRef, useState } from 'react'
import PlayerCardView from '@/components/PlayerCardView'
import type { PublicPlayerCard } from '@/server/backend'
import { TEXT_MIN_Y, useCardStyle } from './cardStyle'

/**
 * 편집 중인 설정을 입은 카드.
 *
 * 🔴 **미리보기를 따로 두지 않는다.** 신원 줄의 그 카드가 곧 미리보기다 —
 * 두 장을 두면 어느 것이 진짜인지 헷갈리고, 편집기를 닫았을 때 보이던 것과
 * 다른 카드가 남을 수 있다.
 *
 * 🔴 여기서 **글자를 끌어 옮긴다**(사용자 요청). 슬라이더 둘로 x · y 를
 * 미는 것보다 카드 위에서 직접 옮기는 편이 훨씬 빠르고, 결과가 눈앞에 있다.
 */
export default function StyledCard({ card }: { card: PublicPlayerCard }) {
  const { style, set } = useCardStyle()
  const ref = useRef<HTMLSpanElement>(null)
  const [dragging, setDragging] = useState(false)

  /** 포인터 자리 → 카드 안의 백분율. 카드가 작게 줄어 있어도(scale) 화면상
   *  크기로 재므로 그대로 맞는다. */
  function place(clientX: number, clientY: number) {
    const box = ref.current?.querySelector('.ss-pcard')?.getBoundingClientRect()
    if (!box || box.width === 0) return
    const x = ((clientX - box.left) / box.width) * 100
    const y = ((clientY - box.top) / box.height) * 100
    set({
      // 🔴 가장자리에 붙어 잘리지 않게 안쪽으로 물린다. 위쪽은 로고와
      // 머리글의 자리라 더 세게 막는다(TEXT_MIN_Y).
      textX: Math.min(94, Math.max(6, x)),
      textY: Math.min(94, Math.max(TEXT_MIN_Y, y)),
    })
  }

  return (
    /* 🔴 감싸지 않고 **그 상자 자체**를 그린다. `.ss-pcard-mini > .ss-pcard`
       가 직계 자식을 찾는 규칙이라, 사이에 상자를 하나 끼우면 축소가 통째로
       풀린다(실측: 260 이던 카드가 92 로 튀었다). */
    <span
      ref={ref}
      className="ss-pcard-mini ss-profile-face ss-card-stage"
      onPointerDown={(e) => {
        // 글자를 집었을 때만 끈다 — 카드 아무 데나 눌러도 글자가 튀어오면
        // 다른 것을 누르려던 사람에게 사고가 된다.
        if (!(e.target as HTMLElement).closest('.ss-pcard-alias')) return
        e.preventDefault()
        ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
        setDragging(true)
        place(e.clientX, e.clientY)
      }}
      onPointerMove={(e) => {
        if (!dragging) return
        place(e.clientX, e.clientY)
      }}
      onPointerUp={(e) => {
        if (!dragging) return
        ;(e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId)
        setDragging(false)
      }}
      onPointerCancel={() => setDragging(false)}
      data-dragging={dragging ? 'true' : undefined}
    >
      <PlayerCardView card={card} look={style} />
    </span>
  )
}
