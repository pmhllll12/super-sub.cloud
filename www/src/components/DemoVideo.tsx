'use client'

import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { usePathname } from 'next/navigation'
import { useIntroDone } from '@/lib/useIntroDone'

/** 사용법 안내 영상. `public/` 에 있는 21MB 원본이다(`demo.mp4` 는 업로드가 깨진 2바이트라 안 쓴다). */
export const DEMO_VIDEO_SRC = '/SUPER_SUB_2min_demo_KR_subtitled.mp4'

/** 로그인 화면이 영상 자리로 내놓는 표식. `AuthShell` 이 단다. */
export const DEMO_SLOT_ATTR = 'data-demo-slot'

type Box = { top: number; left: number; width: number; height: number }

/**
 * 사용법 영상 — 해커톤 제출용(2026-09-18, 사용자 요청).
 *
 * 제출 사이트에 영상을 못 붙이고 **링크와 이미지만** 붙일 수 있어서, 처음 온
 * 사람이 무엇을 해야 하는지를 사이트 안에서 바로 보여 준다.
 *
 * - **인트로가 끝난 뒤에** 나타나 바로 재생된다(무한 반복). 인트로를 안 도는
 *   경로면 곧바로 나온다 — 판단은 홈 등장 연출과 같은 `useIntroDone` 이다
 * - **눌러야 멈춘다**(다시 누르면 이어서). 자동 재생은 브라우저가 소리 없는
 *   영상에만 허락하므로 `muted` 다 — 자막이 입혀진 영상이라 소리 없이도 읽힌다
 * - 로그인 화면에서는 `AuthShell` 의 자리(`[data-demo-slot]`)에 맞춰 앉고,
 *   그 자리가 없는 화면에서는 왼쪽 아래 구석에 작게 뜬다
 *
 * 🔴 **루트 레이아웃에 하나만 둔다.** 화면마다 따로 그리면 페이지를 옮길 때마다
 * `<video>` 가 새로 태어나 **처음부터 다시** 재생된다. 한 벌을 살려 두고 자리만
 * 옮기므로 로그인 → 홈으로 가도 보던 데서 이어진다.
 *
 * 🔴 **`PageTransitionProvider` 밖에 둔다.** 그 안은 화면 전환 때 `transform` 이
 * 걸리는데, `transform` 이 걸린 조상 안의 `position: fixed` 는 화면이 아니라
 * 그 조상을 기준으로 잡혀 엉뚱한 데로 간다.
 */
export default function DemoVideo() {
  const pathname = usePathname()
  const introDone = useIntroDone()
  const videoRef = useRef<HTMLVideoElement>(null)
  const [box, setBox] = useState<Box | null>(null)
  const [paused, setPaused] = useState(false)

  // 자리 재기 — 로그인 화면의 자리를 따라가고, 없으면 구석으로.
  //
  // 🔴 **프레임마다 잰다.** `resize`·`scroll` 만 들으면 화면 전환 연출(카드가
  // 밀려 들어오는 `transform`)과 창 크기 변화 없는 재배치를 놓쳐 영상이 자리에서
  // 떨어져 뜬다. 한 프레임에 `getBoundingClientRect` 한 번이고, 값이 **바뀔 때만**
  // 상태를 고치므로 가만있을 때는 다시 그리지 않는다.
  useLayoutEffect(() => {
    let raf = 0
    let last = ''
    const measure = () => {
      const slot = document.querySelector<HTMLElement>(`[${DEMO_SLOT_ATTR}]`)
      const r = slot?.getBoundingClientRect()
      // 좁은 화면에서는 자리가 든 사진 칸이 통째로 숨는다(폭 0) — 그때는 구석으로.
      const next = r && r.width > 0 ? { top: r.top, left: r.left, width: r.width, height: r.height } : null
      const key = next ? `${next.top}|${next.left}|${next.width}|${next.height}` : ''
      if (key !== last) {
        last = key
        setBox(next)
      }
      raf = requestAnimationFrame(measure)
    }
    measure()
    return () => cancelAnimationFrame(raf)
  }, [pathname])

  // 인트로가 끝나면 튼다. `autoPlay` 속성에 맡기면 인트로 밑에서 이미 돌기 시작해
  // 걷혔을 때는 중간부터 보인다.
  useEffect(() => {
    const v = videoRef.current
    if (!introDone || !v) return
    v.play().catch(() => setPaused(true)) // 막히면 「눌러서 재생」 상태로 남긴다
  }, [introDone])

  const toggle = () => {
    const v = videoRef.current
    if (!v) return
    if (v.paused) v.play().catch(() => {})
    else v.pause()
  }

  return (
    <div
      className="ss-demo-video"
      data-slotted={box ? 'true' : 'false'}
      hidden={!introDone}
      style={box ? { top: box.top, left: box.left, width: box.width, height: box.height } : undefined}
    >
      <video
        ref={videoRef}
        src={DEMO_VIDEO_SRC}
        muted
        loop
        playsInline
        preload="auto"
        onPlay={() => setPaused(false)}
        onPause={() => setPaused(true)}
      />
      <button
        type="button"
        className="ss-demo-video-toggle"
        aria-label={paused ? '사용법 영상 재생' : '사용법 영상 멈춤'}
        aria-pressed={paused}
        onClick={toggle}
      >
        {paused && <span aria-hidden="true" className="ss-demo-video-play" />}
      </button>
    </div>
  )
}
