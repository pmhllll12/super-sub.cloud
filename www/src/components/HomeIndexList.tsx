'use client'

import Link from 'next/link'
import type { Destination } from './HomeNav'

/**
 * 홈 우하단의 번호 목록 — 레퍼런스(Nile Travel)의 `Easter Week in Morocco … 01`
 * 자리다. 상단 글자 내비와 **같은 6개**를 번호와 함께 다시 적는다: 위쪽은
 * 눌러 다니는 자리, 이쪽은 무엇이 있는지 한눈에 세어 보는 자리다.
 *
 * 상단과 강조를 맞춘다 — 어느 쪽을 가리키든 `active` 를 부모가 쥐고 양쪽에
 * 내려 주므로 같은 항목이 같이 밝아진다(레퍼런스에서 04 번이 그렇다).
 *
 * 여기서는 글자가 곧 링크다(상단과 다르다) — 여기엔 떠오르는 카드가 없어서
 * 이동을 맡길 다른 자리가 없다. 접근성 이름에 번호가 들어가므로("01 영상
 * 분석") 상단 카드 링크와 이름이 겹치지도 않는다.
 */
export default function HomeIndexList({
  destinations,
  active,
  onActivate,
}: {
  destinations: Destination[]
  active: string | null
  onActivate: (title: string | null) => void
}) {
  return (
    <ul className="ss-home-index" onMouseLeave={() => onActivate(null)}>
      {destinations.map((d, i) => {
        const no = String(i + 1).padStart(2, '0')
        // 레퍼런스와 같은 줄 모양: 제목 ─── 번호. 잇는 선은 장식이라 숨긴다.
        const row = (
          <>
            <span className="ss-home-index-title">{d.title}</span>
            <span aria-hidden="true" className="ss-home-index-rule" />
            <span className="ss-home-index-no">{no}</span>
          </>
        )
        return (
          <li
            key={d.title}
            data-active={active === d.title ? 'true' : undefined}
            onMouseEnter={() => onActivate(d.title)}
          >
            {d.href ? (
              // 잇는 선(빈 span)이 제목과 번호 사이에 있어 그냥 두면 접근성
              // 이름이 "영상 분석01" 로 붙어 읽힌다 — 이름만 따로 준다.
              <Link href={d.href} aria-label={`${d.title} ${no}`} className="ss-home-index-row">
                {row}
              </Link>
            ) : (
              <span className="ss-home-index-row">{row}</span>
            )}
          </li>
        )
      })}
    </ul>
  )
}
