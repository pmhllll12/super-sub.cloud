'use client'

import { useEffect, useRef } from 'react'
import type { Box } from '@/lib/box'
import { detectPeople, refinePose } from '@/lib/personDetector'
import { smoothPose, type Point } from '@/lib/pose'
import { POSE_VB, posePaths, toViewBox } from '@/lib/poseDraw'
import { smoothStep } from '@/lib/smoothBox'

/**
 * 검출을 다시 재는 **최소** 간격. 내 영상(`AnalysisStage` 의 70ms)보다 느리게
 * 둔다 — 검출기 하나를 두 영상이 나눠 쓰므로, 같이 빠르면 내 영상 쪽이 굼떠진다.
 * 선수 영상은 따라갈 사람을 고른 것이 아니라 **보여 주는 것**이라 이 정도로 된다.
 */
const DETECT_MS = 120

/**
 * 「선수와 비교하기」의 왼쪽 칸 — **선수 영상과 그 위의 하늘색 뼈대.**
 *
 * 🔴 **따라가지 않고 가장 큰 사람을 그린다.** 선수 영상은 사람이 누구를 볼지
 * 묶은 것이 아니라서 추적기를 걸 기준이 없다. 가장 큰 박스는 에이전트가 대상을
 * 고르는 규칙과 같다(`_largest_person_box`) — 두 규칙이 갈리면 화면이 보여 준
 * 사람과 서버가 본 사람이 달라진다.
 *
 * 🔴 **색은 하늘색이다**(사용자 결정, 2026-09-14). 초록은 「내 영상에서 따라가는
 * 사람」의 뜻으로 이미 쓰고 있어서, 같은 색이면 어느 쪽이 나인지 색으로 못 가른다.
 * 하늘색은 적록 색각 이상에서도 초록(누렇게 보인다)과 갈린다.
 *
 * ⚠️ 검출기를 못 올리면 **영상만 돈다** — 뼈대가 없어도 비교는 된다.
 */
export default function ComparePlayer({
  src,
  label,
  closing,
  seekTo = null,
}: {
  src: string
  label: string
  closing: boolean
  /** 초. 숫자면 그 시각으로 가서 멈추고, `null` 이면 이어 재생한다(세 순간 카드). */
  seekTo?: number | null
}) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const layerRef = useRef<HTMLDivElement>(null)
  const boxRef = useRef<HTMLDivElement>(null)
  const boneRef = useRef<SVGPathElement>(null)
  const jointRef = useRef<SVGPathElement>(null)

  /* 검출이 넣는 목표와 화면에 보이는 눅인 값 — 초당 60번 바뀌는 값이라 React
     상태에 두지 않는다(내 영상 쪽과 같은 이유). */
  const targetRef = useRef<Box | null>(null)
  const shownRef = useRef<Box | null>(null)
  const poseRef = useRef<Point[] | null>(null)
  const shownPoseRef = useRef<Point[] | null>(null)

  // 세 순간 카드를 누르면 그 순간에 멈춘다. 다시 누르면(`null`) 이어 돈다.
  useEffect(() => {
    const v = videoRef.current
    if (!v) return
    if (seekTo === null) {
      void v.play()?.catch(() => {})
      return
    }
    v.pause()
    v.currentTime = seekTo
  }, [seekTo])

  // 검출 — 겹쳐 돌리지 않는다. 한 장이 오래 걸리면 그 시간이 곧 간격이다.
  useEffect(() => {
    if (closing) return
    let stop = false
    const loop = async () => {
      while (!stop) {
        await new Promise((r) => setTimeout(r, DETECT_MS))
        const video = videoRef.current
        if (stop || !video) return
        // 멈춰 있으면 그림이 안 바뀐다 — 다시 잴 이유가 없다.
        if (video.paused || video.readyState < 2 || !video.videoWidth) continue

        let dets
        try {
          dets = await detectPeople(video)
        } catch {
          return
        }
        if (stop) return

        const big = dets.slice().sort((a, b) => b.box.w * b.box.h - a.box.w * a.box.h)[0]
        targetRef.current = big?.box ?? null
        poseRef.current = big?.keypoints ?? null
        if (!big) continue

        // 내 영상과 같은 2단계 — 그 사람만 잘라 확대해 관절을 다시 잰다.
        const fine = await refinePose(video, big.box).catch(() => null)
        if (stop) return
        if (fine) poseRef.current = fine
      }
    }
    void loop()
    return () => {
      stop = true
    }
  }, [closing])

  // 그리기 — 검출과 따로 60fps 로 눅여서 그린다.
  useEffect(() => {
    if (closing) return
    let raf = 0
    let prev = performance.now()
    const draw = (t: number) => {
      raf = requestAnimationFrame(draw)
      const dt = t - prev
      prev = t

      const layer = layerRef.current
      const el = boxRef.current
      const bone = boneRef.current
      const joint = jointRef.current
      const video = videoRef.current
      if (!layer || !el || !bone || !joint) return

      const target = targetRef.current
      if (!target) {
        el.style.opacity = '0'
        bone.setAttribute('d', '')
        joint.setAttribute('d', '')
        shownRef.current = null
        shownPoseRef.current = null
        return
      }

      const next = shownRef.current ? smoothStep(shownRef.current, target, dt) : target
      shownRef.current = next
      const v = toViewBox(next, layer, video)
      el.style.left = `${v.x * 100}%`
      el.style.top = `${v.y * 100}%`
      el.style.width = `${v.w * 100}%`
      el.style.height = `${v.h * 100}%`
      el.style.opacity = '1'

      const raw = poseRef.current
      if (!raw) {
        bone.setAttribute('d', '')
        joint.setAttribute('d', '')
        return
      }
      const pose = smoothPose(shownPoseRef.current, raw, dt)
      shownPoseRef.current = pose
      const { bones, joints } = posePaths([pose], layer, video)
      bone.setAttribute('d', bones)
      joint.setAttribute('d', joints)
    }
    raf = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(raf)
  }, [closing])

  return (
    <div className="ss-shot-compare-slot">
      <video
        ref={videoRef}
        src={src}
        aria-label={label}
        playsInline
        loop
        // 🔴 소리를 끈 채로만 자동 재생이 허용된다 — 내 영상 쪽 주석과 같다.
        autoPlay
        muted
        onLoadedData={(e) => {
          const el = e.currentTarget
          el.muted = true
          void el.play().catch(() => {})
        }}
      />
      <div ref={layerRef} className="ss-shot-track" aria-hidden="true">
        <svg
          className="ss-shot-pose"
          viewBox={`0 0 ${POSE_VB} ${POSE_VB}`}
          preserveAspectRatio="none"
          aria-hidden="true"
          focusable="false"
        >
          <path ref={boneRef} className="ss-shot-bone" vectorEffect="non-scaling-stroke" />
          <path ref={jointRef} className="ss-shot-joint" vectorEffect="non-scaling-stroke" />
        </svg>
        <div ref={boxRef} className="ss-shot-track-box">
          <span className="ss-shot-track-tag">PRO</span>
        </div>
      </div>
    </div>
  )
}
