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
  // 기본 자리 — 로그인 화면이면 그 자리, 아니면 왼쪽 아래 구석. 늘 JS 가 잰다
  // (크기 조절 계산이 기준 상자를 알아야 해서 구석도 CSS 에 맡기지 않는다).
  const [base, setBase] = useState<(Box & { slotted: boolean }) | null>(null)
  // 사용자가 모서리를 끌어 바꾼 것 — 기본 자리에서 얼마나 옮기고 키웠나.
  const [adj, setAdj] = useState<Adjust | null>(null)
  const [closed, setClosed] = useState(false)
  // 나오는 연출 — 처음엔 위에서 내려오고(drop), 다 내려오면 **아무 연출 없음**
  // (still), 닫았다 다시 열면 스르르(fade).
  // 🔴 내려온 뒤 곧장 fade 로 바꾸면 애니메이션이 바뀌면서 **새로 돌아 한 번
  // 깜빡인다**(0 → 1). 그래서 가운데에 still 을 둔다.
  // 「시연영상을 참고해 주세요」 — 로그인 화면에서 영상이 처음 다 내려왔을 때만
  // 영상과 닫기 단추만 밝게 두고 나머지를 어둡게 하며 한 줄 띄운다(사용자 요청).
  // on → (어디든 한 번 누르거나 5초) → out(스르르) → off.
  const [spot, setSpot] = useState<'off' | 'on' | 'out'>('off')
  const [unlocked, setUnlocked] = useState(false)
  useEffect(() => {
    if (spot === 'on') {
      const timer = setTimeout(() => setSpot('out'), SPOT_MS)
      return () => clearTimeout(timer)
    }
    if (spot === 'out') {
      const timer = setTimeout(() => setSpot('off'), SPOT_FADE_MS)
      return () => clearTimeout(timer)
    }
  }, [spot])
  // 누르면 걷힌다 — 단 **잠금이 풀린 뒤에만**(잠긴 동안 누른 것은 없던 일이다).
  // 캡처 단계에서 듣기만 하고 막지 않는다 — 누른 것은 원래 하던 일(입력칸
  // 누르기·로그인 단추)을 그대로 한다. 어둠 판은 누르는 것을 가로채지 않는다.
  useEffect(() => {
    if (spot !== 'on' || !unlocked) return
    const dismiss = () => setSpot('out')
    window.addEventListener('pointerdown', dismiss, true)
    return () => window.removeEventListener('pointerdown', dismiss, true)
  }, [spot, unlocked])

  // 🔴 **영상과 안내 문장이 다 제자리에 나오기 전에는 로그인 화면을 못 누른다**
  // (사용자 요청 — 「절대」). 심사위원이 인트로가 끝나자마자 로그인 단추부터 누르면
  // 시연영상을 못 보고 지나간다.
  //
  // 막는 것은 **투명한 판**(`.ss-demo-lock`, 영상 바로 밑)이다. 창에서 클릭을 듣고
  // 막는 식으로는 안 된다 — 구글 로그인 단추는 **다른 출처의 iframe** 이라 그 안의
  // 클릭은 우리 창으로 안 온다. 자판(Enter·Space)과 폼 제출은 따로 막는다.
  //
  // 풀리는 때: 로그인 화면이면 안내 문장이 다 나온 뒤(SPOT_IN_MS), 아니면 자리를
  // 잰 즉시. 🔴 **안전장치 둘** — 영상을 도중에 닫으면(내려오기가 끊겨
  // animationend 가 영영 안 온다) 곧바로, 무슨 일이 있어도 LOCK_MAX_MS 뒤엔 푼다.
  // 이게 없으면 로그인 화면이 영영 안 눌린다.
  useEffect(() => {
    if (unlocked) return
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (closed || (base && !base.slotted)) return setUnlocked(true)
    const safety = setTimeout(() => setUnlocked(true), LOCK_MAX_MS)
    const shown = spot === 'on' ? setTimeout(() => setUnlocked(true), SPOT_IN_MS) : undefined
    return () => {
      clearTimeout(safety)
      clearTimeout(shown)
    }
  }, [unlocked, closed, base, spot])

  useEffect(() => {
    if (unlocked) return
    const inDemo = (t: EventTarget | null) => t instanceof Element && !!t.closest('.ss-demo-video')
    const block = (e: Event) => {
      if (inDemo(e.target)) return
      if (e instanceof KeyboardEvent && e.key !== 'Enter' && e.key !== ' ') return
      e.preventDefault()
      e.stopPropagation()
    }
    window.addEventListener('keydown', block, true)
    window.addEventListener('submit', block, true)
    return () => {
      window.removeEventListener('keydown', block, true)
      window.removeEventListener('submit', block, true)
    }
  }, [unlocked])

  // 다른 화면으로 가거나 닫으면 함께 걷는다.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (closed || !base?.slotted) setSpot((s) => (s === 'on' ? 'out' : s))
  }, [closed, base?.slotted])

  const [entrance, setEntrance] = useState<'drop' | 'still' | 'fade'>('drop')
  // 다시 틀 때 ▶ 를 한 번 띄웠다 사라지게 하는 열쇠 — 바꿀 때마다 새로 돈다.
  const [flash, setFlash] = useState(0)
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
      const next =
        r && r.width > 0
          ? { top: r.top, left: r.left, width: r.width, height: r.height, slotted: true }
          : { ...cornerBox(window.innerWidth, window.innerHeight), slotted: false }
      const key = `${next.top}|${next.left}|${next.width}|${next.height}|${next.slotted}`
      if (key !== last) {
        last = key
        setBase(next)
      }
      raf = requestAnimationFrame(measure)
    }
    measure()
    return () => cancelAnimationFrame(raf)
  }, [pathname])

  // 자리의 **종류**가 바뀌면(로그인 자리 ↔ 구석) 사용자가 바꾼 크기를 버린다 —
  // 로그인 자리에서 키운 배율을 구석에 그대로 얹으면 화면 밖으로 넘친다.
  const slotted = base?.slotted
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setAdj(null)
  }, [slotted])

  // 🔴 **늘 창 안에 둔다**(사용자 요청 — 「사이트 밖으로 넘어가면 안 된다」). 끌어
  // 옮긴 값이든 창을 줄인 뒤든, 그리기 직전에 한 번 더 창 안으로 밀어 넣는다 —
  // 위쪽은 바깥에 붙은 「시연영상 닫기」 단추 자리까지 비운다.
  const rect: Box | null = base
    ? clampToViewport(
        adj
          ? {
              left: base.left + adj.dx,
              top: base.top + adj.dy,
              width: base.width * adj.scale,
              height: base.height * adj.scale,
            }
          : base,
        window.innerWidth,
        window.innerHeight,
      )
    : null

  // 모서리 끌기 — **맞은편 모서리를 붙박고** 끄는 쪽으로 커지고 작아진다. 비율은
  // 영상 그대로, 작게는 기본의 **딱 절반**까지(사용자 요청), 크게는 창 안까지.
  const drag = useRef<{ fx: number; fy: number; right: boolean; down: boolean } | null>(null)
  const onResizeDown = (corner: Corner) => (e: React.PointerEvent<HTMLSpanElement>) => {
    if (!rect) return
    e.preventDefault()
    e.stopPropagation()
    e.currentTarget.setPointerCapture?.(e.pointerId)
    const right = corner.includes('r')
    const down = corner.includes('b')
    drag.current = {
      fx: right ? rect.left : rect.left + rect.width,
      fy: down ? rect.top : rect.top + rect.height,
      right,
      down,
    }
  }
  const onResizeMove = (e: React.PointerEvent<HTMLSpanElement>) => {
    const d = drag.current
    if (!d || !base || !e.currentTarget.hasPointerCapture?.(e.pointerId)) return
    const aspect = base.width / base.height
    const room = 8 // 창 가장자리와 띄울 틈
    const maxW = Math.min(
      d.right ? window.innerWidth - room - d.fx : d.fx - room,
      (d.down ? window.innerHeight - room - d.fy : d.fy - room - CLOSE_ROOM) * aspect,
    )
    const want = Math.max(Math.abs(e.clientX - d.fx), Math.abs(e.clientY - d.fy) * aspect)
    const width = Math.max(base.width * MIN_SCALE, Math.min(want, maxW))
    const height = width / aspect
    setAdj({
      scale: width / base.width,
      dx: (d.right ? d.fx : d.fx - width) - base.left,
      dy: (d.down ? d.fy : d.fy - height) - base.top,
    })
  }
  const onResizeUp = () => {
    drag.current = null
  }

  const close = () => {
    videoRef.current?.pause()
    setClosed(true)
  }
  const reopen = () => {
    setEntrance('fade')
    setClosed(false)
    videoRef.current?.play().catch(() => {})
  }

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
    // 🔴 **아이콘은 ▶ 하나뿐이다**(사용자 정정). 멈추려고 누르면 ▶ 가 떠서 남고,
    // 다시 틀려고 누르면 그 ▶ 가 한 번 커지며 사라진다. ❚❚ 를 번쩍였다가 ▶ 로
    // 바뀌는 것(유튜브식)은 「재생 아이콘이 나오고 정지 아이콘이 나와 이상하다」로
    // 되돌렸다.
    if (v.paused) {
      v.play().catch(() => {})
      setFlash((n) => n + 1)
    } else {
      v.pause()
    }
  }

  // 끌어 옮기기 — 영상(과 붙은 단추)을 원하는 데 둔다(사용자 요청). 영상을 누르는
  // 것은 원래 멈춤/재생이라 **4px 넘게 움직였을 때만** 옮기기로 치고, 그때는 뒤이어
  // 오는 클릭을 삼킨다 — 안 그러면 옮길 때마다 영상이 멈춘다.
  const move = useRef<{ x: number; y: number; dx: number; dy: number; moved: boolean } | null>(null)
  const onMoveDown = (e: React.PointerEvent<HTMLElement>) => {
    if (!base || !rect || e.button !== 0) return
    e.currentTarget.setPointerCapture?.(e.pointerId)
    move.current = { x: e.clientX, y: e.clientY, dx: rect.left - base.left, dy: rect.top - base.top, moved: false }
  }
  const onMoveMove = (e: React.PointerEvent<HTMLElement>) => {
    const m = move.current
    if (!m || !base || !e.currentTarget.hasPointerCapture?.(e.pointerId)) return
    const ox = e.clientX - m.x
    const oy = e.clientY - m.y
    if (!m.moved && Math.hypot(ox, oy) < DRAG_THRESHOLD) return
    m.moved = true
    setAdj((a) => ({ scale: a?.scale ?? 1, dx: m.dx + ox, dy: m.dy + oy }))
  }
  const onMoveUp = () => {
    // 클릭은 pointerup 뒤에 온다 — 옮겼는지는 클릭 쪽이 읽고 지운다.
    if (move.current && !move.current.moved) move.current = null
  }
  const consumeDrag = () => {
    const moved = move.current?.moved ?? false
    move.current = null
    return moved
  }

  const pos = rect ? { top: rect.top, left: rect.left, width: rect.width, height: rect.height } : undefined

  return (
    <>
      {!unlocked && <div aria-hidden="true" className="ss-demo-lock" data-testid="demo-lock" />}
      {spot !== 'off' && (
        <>
          {/* 어둠 판 — 영상(z 55) 바로 밑이라 영상·닫기 단추만 밝게 남는다. */}
          <div aria-hidden="true" className="ss-demo-spot" data-state={spot} />
          {rect && (
            <div
              role="status"
              className="ss-demo-spot-note"
              data-state={spot}
              style={{ top: rect.top + rect.height + 14, left: rect.left + rect.width / 2 }}
            >
              <p>시연영상을 참고해 주세요.</p>
              <p className="ss-demo-spot-sub">모서리를 끌어 크기를, 영상을 끌어 위치를 바꿀 수 있습니다.</p>
            </div>
          )}
        </>
      )}
      {/* 단추 유리의 굴절(warp 8, 사용자 요청). 로그인 카드의 `#ss-glass-warp`(50)는
          그 화면에만 있고 세기도 달라 따로 둔다. */}
      <svg width="0" height="0" aria-hidden="true" focusable="false" className="absolute">
        <filter id="ss-demo-warp" x="-10%" y="-10%" width="120%" height="120%" colorInterpolationFilters="sRGB">
          <feTurbulence type="fractalNoise" baseFrequency="0.02 0.03" numOctaves="2" seed="7" result="warp" />
          <feDisplacementMap in="SourceGraphic" in2="warp" scale="8" xChannelSelector="R" yChannelSelector="G" />
        </filter>
      </svg>

      {/* 닫은 뒤 — 영상이 있던 자리 왼쪽 위에 작은 단추 하나만 남는다. */}
      {introDone && closed && (
        <button
          type="button"
          className="ss-demo-glass-btn ss-demo-reopen"
          style={rect ? { top: rect.top - CLOSE_ROOM, left: rect.left } : undefined}
          onPointerDown={onMoveDown}
          onPointerMove={onMoveMove}
          onPointerUp={onMoveUp}
          onClick={() => {
            if (!consumeDrag()) reopen()
          }}
        >
          시연 영상 다시보기
        </button>
      )}

      <div
        className="ss-demo-video"
        data-slotted={base?.slotted ? 'true' : 'false'}
        // 처음 나올 때만 화면 위 보이지 않는 데서 내려온다(사용자 요청). 닫았다가
        // 「다시보기」로 열 때는 그 자리에서 스르르 — 매번 떨어지면 성가시다.
        data-entrance={entrance}
        hidden={!introDone || closed}
        style={pos}
        onAnimationEnd={(e) => {
          // 안쪽(아이콘·막대)의 애니메이션도 여기로 올라온다 — 제 것만 센다.
          if (e.target !== e.currentTarget || entrance !== 'drop') return
          setEntrance('still')
          // 로그인 화면이면 다 내려온 순간 주위를 어둡게 하고 안내 한 줄을 띄운다.
          if (base?.slotted) setSpot('on')
        }}
      >
        {/* 닫기 — 외곽선 **바깥** 왼쪽 위(사용자 요청). 틀이 `overflow: hidden` 이라
            틀 밖 형제로 둔다. */}
        <button
          type="button"
          className="ss-demo-glass-btn ss-demo-close"
          onPointerDown={onMoveDown}
          onPointerMove={onMoveMove}
          onPointerUp={onMoveUp}
          onClick={() => {
            if (!consumeDrag()) close()
          }}
        >
          시연영상 닫기
        </button>

        <div className="ss-demo-video-frame">
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
            onPointerDown={onMoveDown}
            onPointerMove={onMoveMove}
            onPointerUp={onMoveUp}
            onClick={() => {
              if (!consumeDrag()) toggle()
            }}
          >
            {/* 멈춰 있는 동안은 가운데 ▶ 가 계속 떠 있다 — 멈춘 줄 모르고 「안
                나온다」로 읽히지 않게. */}
            {paused ? (
              <PlayIcon className="ss-demo-video-icon" />
            ) : (
              flash > 0 && <PlayIcon key={flash} className="ss-demo-video-icon ss-demo-video-flash" />
            )}
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

        {/* 크기 조절 손잡이 — 네 모서리. 틀 밖에 두어야 `overflow: hidden` 에 안 잘린다. */}
        {CORNERS.map((c) => (
          <span
            key={c}
            aria-hidden="true"
            data-corner={c}
            className="ss-demo-resize"
            onPointerDown={onResizeDown(c)}
            onPointerMove={onResizeMove}
            onPointerUp={onResizeUp}
            onPointerCancel={onResizeUp}
          />
        ))}
      </div>
    </>
  )
}

/** 가운데 ▶ — 판 없이 삼각형만, 작고 가늘게(사용자 요청). */
function PlayIcon({ className }: { className: string }) {
  return (
    <svg aria-hidden="true" className={className} viewBox="0 0 24 24">
      <path d="M8.5 6.2v11.6c0 .5.5.8.9.5l9-5.8a.6.6 0 0 0 0-1L9.4 5.7c-.4-.3-.9 0-.9.5z" />
    </svg>
  )
}

/** 「시연영상을 참고해 주세요」가 떠 있는 시간(아무도 안 누르면). */
export const SPOT_MS = 5000
/** 안내 문장이 다 나오는 시간 — 이때 로그인 화면 잠금이 풀린다. CSS 의 들어오는 길이와 같다. */
export const SPOT_IN_MS = 600
/** 무슨 일이 있어도 이 안에는 로그인 화면 잠금을 푼다(인트로 최대 7초 + 내려오기 + 문장). */
export const LOCK_MAX_MS = 12000
/** 어둠과 안내가 스르르 걷히는 시간 — CSS 의 전이 길이와 같아야 한다. */
const SPOT_FADE_MS = 600

/** 영상 위에 붙은 「시연영상 닫기」 단추가 차지하는 높이(단추 + 틈). */
const CLOSE_ROOM = 34
/** 이만큼 움직여야 「옮기기」다 — 그 아래는 그냥 누른 것(멈춤/재생). */
const DRAG_THRESHOLD = 4
/** 창 가장자리와 띄울 틈. */
const EDGE = 8

/** 상자를 창 안으로 밀어 넣는다(위쪽은 닫기 단추 자리까지). 창보다 크면 줄인다. */
export function clampToViewport(r: Box, vw: number, vh: number): Box {
  const aspect = r.width / r.height
  let width = Math.min(r.width, vw - EDGE * 2, (vh - EDGE * 2 - CLOSE_ROOM) * aspect)
  width = Math.max(width, 0)
  const height = width / aspect
  const left = Math.min(Math.max(r.left, EDGE), vw - EDGE - width)
  const top = Math.min(Math.max(r.top, EDGE + CLOSE_ROOM), vh - EDGE - height)
  return { left, top, width, height }
}

type Corner = 'tl' | 'tr' | 'bl' | 'br'
const CORNERS: Corner[] = ['tl', 'tr', 'bl', 'br']

/** 기본 크기에서 줄일 수 있는 한계 — 딱 절반(사용자 요청). */
export const MIN_SCALE = 0.5

type Adjust = { scale: number; dx: number; dy: number }

/** 영상 비율(자른 뒤 1902×952). `AuthShell` 의 자리 비율과 같아야 한다. */
const VIDEO_ASPECT = 1902 / 952

/** 로그인 자리가 없는 화면의 기본 자리 — 왼쪽 아래 구석, 폭 최대 320px. */
export function cornerBox(vw: number, vh: number): Box {
  const gap = 24
  const width = Math.min(320, vw * 0.4)
  const height = width / VIDEO_ASPECT
  return { left: gap, top: vh - gap - height, width, height }
}

/** 초 → `분:초`(예: 83.4 → `1:23`). 유튜브와 같은 꼴이다. */
export function formatTime(sec: number): string {
  const s = Math.max(0, Math.floor(Number.isFinite(sec) ? sec : 0))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}
