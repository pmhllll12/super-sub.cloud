/**
 * 인트로 잉크 번짐·글리치의 순수 함수들.
 *
 * 원본: `flutter/lib/core/widgets/ink_bleed.dart` (`inkProgress`),
 * `flutter/lib/features/intro/presentation/screens/glitch_intro_screen.dart`
 * (`glitchAmplitudeAt`, 버스트 표, `_kSwapAt`). 수치는 그쪽에서 그대로 옮겼다
 * — 참조 영상에서 잰 값이라 임의로 바꾸지 않는다.
 */

/** 순백 구간이 끝나는 컨트롤러 값. 700ms / 3600ms. */
export const DRY_END = 0.7 / 3.6

/** 번짐이 끝나는 컨트롤러 값. 3100ms / 3600ms. */
export const WET_END = 3.1 / 3.6

/** 전체 인트로 길이(ms). 민트만 700 + 번짐 2400 + 머묾 500. */
export const TOTAL_MS = 3600

/** 문턱 경계 폭. */
export const EDGE = 0.02

/** 끓음 최대 폭. 문턱값을 이만큼 흔든다. */
export const BOIL = 0.06

/** 흔들림 값을 붙잡아 두는 시간(ms). 매 프레임 새로 뽑으면 지글거림이 된다. */
export const HOLD_MS = 45

/** 글자를 끊는 가로 띠 수. */
export const BANDS = 7

/** 가지런한 Rubik이 깨진 RubikGlitch로 바뀌는 잉크 진행도. */
export const SWAP_AT = 0.795

/**
 * 컨트롤러 값 `t`(0~1)를 잉크 진행도(0~1)로 옮긴다.
 *
 * 선형이 아니다 — 번짐 구간 절반 지점에서 65%가 젖는다(선형이면 50%).
 * `p = 1.6u - 0.6u²`.
 */
export function inkProgress(t: number): number {
  if (t <= DRY_END) return 0
  if (t >= WET_END) return 1
  const u = (t - DRY_END) / (WET_END - DRY_END)
  return 1.6 * u - 0.6 * u * u
}

/**
 * 지지직대는 구간 — [시작, 끝, 세기]. **컨트롤러 값이 아니라 잉크 진행도
 * 기준이다.** 버스트는 이 세 번뿐이고, 그 사이는 진폭이 정확히 0이다.
 */
const BURSTS: readonly [start: number, end: number, power: number][] = [
  [0.62, 0.71, 1.0],
  [0.76, 0.83, 0.72],
  [0.88, 0.93, 0.4],
]

/**
 * 잉크 진행도 `p`에서 얼마나 세게 흔들릴지(0~1).
 *
 * 버스트 안에서도 뒤로 갈수록 잦아든다(`power * (1 - into²)`). 버스트
 * 밖에서는 항상 0 — 사이의 정적이 있어야 터지는 순간이 산다.
 */
export function glitchAmplitudeAt(p: number): number {
  for (const [start, end, power] of BURSTS) {
    if (p < start || p >= end) continue
    const into = (p - start) / (end - start)
    return power * (1 - into * into)
  }
  return 0
}
