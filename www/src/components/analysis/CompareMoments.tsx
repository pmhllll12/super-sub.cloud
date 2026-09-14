'use client'

import { normalizePose, skeletonPath } from '@/lib/motion/align'
import { metricsAt, sideAt } from '@/lib/motion/angles'
import { MOMENT_KEYS, MOMENT_LABEL, type MomentKey, type Moments, type Motion } from '@/lib/motion/types'

type Analyzed = { motion: Motion; moments: Moments }

/**
 * 영상 칸 아래 **세 순간 카드** — 순간마다 선수(하늘) · 나(초록) 뼈대를 골반 중점과
 * 몸통 길이로 맞춰 겹친다(설계 §3).
 *
 * 🔴 **선수 쪽만 뒤집는다**(`mirrored`). 나는 늘 원래 모습 — 내 영상과 같은 방향이어야
 * 카드와 영상을 오가며 읽힌다.
 */
export default function CompareMoments({
  playerName,
  player,
  user,
  mirrored,
  onToggleMirror,
  selected,
  onSelect,
}: {
  playerName: string
  player: Analyzed
  user: Analyzed
  mirrored: boolean
  onToggleMirror: () => void
  selected: MomentKey | null
  onSelect: (key: MomentKey) => void
}) {
  return (
    <div className="ss-shot-moments" role="group" aria-label="세 순간 비교">
      <div className="ss-shot-moments-cards">
        {MOMENT_KEYS.map((key) => {
          const pSide = sideAt(player.motion, player.moments, key)
          const uSide = sideAt(user.motion, user.moments, key)
          const p = pSide && normalizePose(pSide.pose, pSide.aspect, mirrored)
          const u = uSide && normalizePose(uSide.pose, uSide.aspect, false)
          const pro = p ? skeletonPath(p) : null
          const me = u ? skeletonPath(u) : null
          const first = pSide && uSide ? metricsAt(key, pSide, uSide)[0] : undefined
          const clipped = key === 'after' && (player.moments.afterClipped || user.moments.afterClipped)
          return (
            <button
              key={key}
              type="button"
              className="ss-shot-moment"
              data-moment={key}
              aria-pressed={selected === key}
              onClick={() => onSelect(key)}
            >
              <span className="ss-shot-moment-label">
                {MOMENT_LABEL[key]}
                {clipped ? ' · 영상 끝' : ''}
              </span>
              <svg viewBox="0 0 1000 1000" aria-hidden="true" focusable="false">
                {/* 선수가 먼저 — 내 뼈대가 위에 그려져야 내 자세가 안 묻힌다. */}
                {pro && (
                  <>
                    <path className="ss-shot-moment-pro" d={pro.bones} />
                    <path className="ss-shot-moment-pro-joint" d={pro.joints} />
                  </>
                )}
                {me && (
                  <>
                    <path className="ss-shot-moment-me" d={me.bones} />
                    <path className="ss-shot-moment-me-joint" d={me.joints} />
                  </>
                )}
              </svg>
              {first && (
                <span className="ss-shot-moment-metric">
                  {first.label} {first.player}° / {first.user}°
                </span>
              )}
            </button>
          )
        })}
      </div>
      <div className="ss-shot-moments-foot">
        <span className="ss-shot-moments-legend">
          <i data-who="pro" />
          {playerName}
          <i data-who="me" />나
        </span>
        <button type="button" className="ss-shot-moments-flip" aria-pressed={mirrored} onClick={onToggleMirror}>
          좌우 반전 ⇄
        </button>
        <span>브라우저에서 잰 값 · 데모 영상(Pexels)</span>
      </div>
    </div>
  )
}
