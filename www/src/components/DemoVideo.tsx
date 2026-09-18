'use client'

import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { usePathname } from 'next/navigation'
import { useIntroDone } from '@/lib/useIntroDone'

/**
 * 사용법 안내 영상(1902×952, 17MB). 🔴 **원본 녹화에서 브라우저 머리칸(탭·주소창, 위
 * 88px)과 스크롤바(오른쪽 18px)를 잘라 낸 것이다** — 우리 사이트만 보이게(사용자 요청).
 * 원본은 120초 내내 같은 자리에 머리칸이 있어 한 번에 잘랐다:
 * `ffmpeg -i 원본.mp4 -vf crop=1902:952:0:88 -c:v libx264 -crf 22 -an -movflags +faststart`
 * 영상을 바꾸면 자리 비율(`AuthShell` 의 `aspect-[…]`, `.ss-demo-video`)도 같이 고친다.
 * (`demo.mp4` 는 업로드가 깨진 2바이트라 안 쓴다.)
 */
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
  const [time, setTime] = useState(0)
  const [duration, setDuration] = useState(0)

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

  // 🔴 길이는 마운트 때 **직접 한 번 읽는다.** `<video>` 는 서버 HTML 에 실려 와
  // React 가 붙기 전에 이미 메타데이터를 받아 버린다 — 그러면 `loadedmetadata` 를
  // 놓쳐 길이가 0 으로 남고 막대가 통째로 죽는다(헤드리스 크롬에서 실제로 겪었다).
  useEffect(() => {
    const v = videoRef.current
    if (v && v.readyState >= 1 && Number.isFinite(v.duration)) setDuration(v.duration)
  }, [])

  // 진행 막대 — 재생 중에는 프레임마다 읽는다. `timeupdate` 는 초당 네 번쯤이라
  // 막대가 뚝뚝 끊겨 움직인다(유튜브처럼 매끄럽게 가야 한다).
  useEffect(() => {
    const v = videoRef.current
    if (!v || paused) return
    let raf = 0
    const tick = () => {
      setTime(v.currentTime)
      raf = requestAnimationFrame(tick)
    }
    tick()
    return () => cancelAnimationFrame(raf)
  }, [paused])

  const seekTo = (t: number) => {
    const v = videoRef.current
    if (!v || !duration) return
    const next = Math.min(Math.max(t, 0), duration)
    v.currentTime = next
    setTime(next)
  }

  // 막대 위 가로 위치 → 시각. 누른 채 끌면 따라간다(포인터를 붙잡아 막대 밖으로
  // 나가도 놓치지 않는다).
  const seekFromPointer = (e: React.PointerEvent<HTMLDivElement>) => {
    const r = e.currentTarget.getBoundingClientRect()
    if (r.width <= 0) return
    seekTo(((e.clientX - r.left) / r.width) * duration)
  }

  const onSeekKey = (e: React.KeyboardEvent<HTMLDivElement>) => {
    const step = { ArrowLeft: -5, ArrowRight: 5, ArrowDown: -5, ArrowUp: 5 }[e.key]
    if (step !== undefined) seekTo(time + step)
    else if (e.key === 'Home') seekTo(0)
    else if (e.key === 'End') seekTo(duration)
    else return
    e.preventDefault()
  }

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
        onLoadedMetadata={(e) => setDuration(e.currentTarget.duration || 0)}
        onTimeUpdate={(e) => setTime(e.currentTarget.currentTime)}
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
      {/* 유튜브식 되감기 막대(사용자 요청) — 앞부분을 다시 보거나 원하는 데로 건너뛴다.
          🔴 **멈춤 단추(영상 전체) 위에 겹쳐 둔다** — 막대를 누른 것이 멈춤으로
          새지 않게 이 칸은 자기 클릭을 삼킨다. 평소엔 숨고, 가리키거나 멈췄을 때
          뜬다 — 작은 영상이라 늘 떠 있으면 자막을 가린다. */}
      <div className="ss-demo-video-bar" onClick={(e) => e.stopPropagation()}>
        <div
          role="slider"
          tabIndex={0}
          aria-label="사용법 영상 재생 위치"
          aria-valuemin={0}
          aria-valuemax={Math.round(duration)}
          aria-valuenow={Math.round(time)}
          aria-valuetext={`${formatTime(time)} / ${formatTime(duration)}`}
          className="ss-demo-video-seek"
          onPointerDown={(e) => {
            e.currentTarget.setPointerCapture?.(e.pointerId)
            seekFromPointer(e)
          }}
          onPointerMove={(e) => {
            if (e.currentTarget.hasPointerCapture?.(e.pointerId)) seekFromPointer(e)
          }}
          onKeyDown={onSeekKey}
        >
          <span
            className="ss-demo-video-seek-fill"
            style={{ width: `${duration ? (time / duration) * 100 : 0}%` }}
          />
        </div>
        <span className="ss-demo-video-time">
          {formatTime(time)} / {formatTime(duration)}
        </span>
      </div>
    </div>
  )
}

/** 초 → `분:초`(예: 83.4 → `1:23`). 유튜브와 같은 꼴이다. */
export function formatTime(sec: number): string {
  const s = Math.max(0, Math.floor(Number.isFinite(sec) ? sec : 0))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}
