/**
 * 튀는 검출 결과를 **부드럽게 따라가는 상자**로 눅인다.
 *
 * ## 🔴 왜 필요한가
 *
 * 검출은 초당 10~15번이고 그 값이 프레임마다 조금씩 흔들린다 — 특히 **크기**가
 * 심하다(팔을 들면 상자가 커지고, 다리가 가려지면 줄어든다). 그걸 그대로
 * 그리면 네모가 계속 커졌다 작아졌다 하고, 초당 15번만 움직이니 뚝뚝 끊긴다.
 *
 * 실제 서비스는 검출 결과를 그대로 안 그린다. **검출과 그리기를 나눈다**:
 *
 * ```
 *  검출    ●        ●        ●        ●      초당 10~15번, 값이 튄다
 *           ↓  필터(칼만 필터 · 지수 평활)
 *  그리기  ●●●●●●●●●●●●●●●●●●●●●●●●●●●     초당 60번, 부드럽다
 * ```
 *
 * 여기서는 **지수 평활**을 쓴다. 칼만 필터가 정석이지만(SORT · DeepSORT 가
 * 그렇다) 그건 다음 자리를 **예측**하려고 쓰는 것이고, 예측은 이미 짝짓기
 * (`personTrack`)가 하고 있다. 여기 남은 일은 보이는 것을 눅이는 것뿐이라
 * 상태 방정식을 세울 것 없이 한 줄이면 된다.
 *
 * ## 🔴 세 가지를 지킨다
 *
 * 1. **시간으로 눅인다.** 프레임마다 같은 비율로 섞으면 화면이 느린 기기에서
 *    더 느리게 따라온다. `1 − exp(−dt/τ)` 로 재면 **프레임률과 무관하게** 같은
 *    속도가 된다
 * 2. **크기는 자리보다 훨씬 천천히.** 자리는 진짜로 움직이는 값이지만 크기는
 *    대부분 검출 잡음이다 — 같은 속도로 따라가면 네모가 숨쉬듯 벌렁거린다
 * 3. **멀리 건너뛸 때는 눅이지 않고 붙인다.** 다른 사람으로 옮겨 갈 때
 *    부드럽게 미끄러지면 빈 코트를 가로질러 날아가는 것으로 보인다 — 그건
 *    부드러운 게 아니라 틀린 그림이다
 */

import { centerDist, type Box } from './box'

/** 자리가 목표의 63% 까지 오는 데 걸리는 시간. 짧을수록 빠르고 덜 부드럽다. */
const POS_TAU = 70

/** 크기의 같은 값. 🔴 자리의 네 배 — 크기 흔들림은 대부분 검출 잡음이다. */
const SIZE_TAU = 280

/** 이보다 멀리 건너뛰면(상자 키 대비) 눅이지 않고 그냥 붙인다. */
const SNAP_DIST = 0.9

export type SmoothOpts = { posTau?: number; sizeTau?: number; snapDist?: number }

/**
 * 지금 그리고 있는 자리를 목표 쪽으로 `dt` 만큼 옮긴다.
 *
 * `dt` 는 지난 그림에서 흐른 시간(ms)이다.
 */
export function smoothStep(cur: Box, target: Box, dt: number, opts?: SmoothOpts): Box {
  const snapDist = opts?.snapDist ?? SNAP_DIST
  // 🔴 다른 사람으로 옮겨 간 것이면 미끄러지지 않고 붙는다.
  if (centerDist(cur, target) > snapDist) return target

  // 프레임률과 무관한 비율 — 60fps 든 20fps 든 같은 시간에 같은 만큼 온다.
  const ms = Math.max(0, Math.min(200, dt))
  const kp = 1 - Math.exp(-ms / (opts?.posTau ?? POS_TAU))
  const ks = 1 - Math.exp(-ms / (opts?.sizeTau ?? SIZE_TAU))

  const w = cur.w + (target.w - cur.w) * ks
  const h = cur.h + (target.h - cur.h) * ks
  // 자리는 **가운데**를 눅인다. 왼쪽 위 모서리를 눅이면 크기가 바뀔 때마다
  // 네모가 한쪽으로 쏠린다.
  const cx = cur.x + cur.w / 2 + (target.x + target.w / 2 - (cur.x + cur.w / 2)) * kp
  const cy = cur.y + cur.h / 2 + (target.y + target.h / 2 - (cur.y + cur.h / 2)) * kp

  return { x: cx - w / 2, y: cy - h / 2, w, h }
}
