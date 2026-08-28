/**
 * 인트로 잉크 번짐·글리치의 순수 함수들.
 *
 * 원본: `flutter/lib/core/widgets/ink_bleed.dart` (`inkProgress`),
 * `flutter/lib/features/intro/presentation/screens/glitch_intro_screen.dart`
 * (`glitchAmplitudeAt`, `_kSwapAt`). 수치는 참조 영상에서 잰 값이라 근거
 * 없이 바꾸지 않는다 — **단 구간 길이와 흔들림 곡선 둘은 2026-08-28 에
 * 요청을 받아 웹만 따로 정했다.** 각 상수 주석에 앱 값을 함께 적어 뒀다.
 */

/**
 * 인트로 구간 길이(ms). 이 셋이 원본이고 아래 비율은 전부 여기서 나온다 —
 * 타이밍을 손볼 때 여기만 고치면 된다.
 *
 * 앱(참조 영상 실측)은 700 / 2400 / 500 이었다. 2026-08-28 에 웹만
 * **300 / 3000 / 500** 으로 바꿨다 — 들어가자마자 번지기 시작하고, 번지는
 * 것 자체는 더 천천히 보이게 해 달라는 요청이다. 앱과 값이 갈린 자리다.
 */
/** 민트 종이만 보이는 시간 — 아직 잉크가 안 번진 구간. */
export const DRY_MS = 300
/** 잉크가 번지는 시간. */
export const WET_MS = 3000
/** 다 번진 뒤 머무는 시간. */
export const SETTLE_MS = 500

/** 전체 인트로 길이(ms). */
export const TOTAL_MS = DRY_MS + WET_MS + SETTLE_MS

/** 민트만 보이는 구간이 끝나는 컨트롤러 값. */
export const DRY_END = DRY_MS / TOTAL_MS

/** 번짐이 끝나는 컨트롤러 값. */
export const WET_END = (DRY_MS + WET_MS) / TOTAL_MS

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
 * 잉크 진행도 `p`에서 얼마나 세게 흔들릴지(0~1).
 *
 * **번지는 내내 흔들린다.** 잉크가 번지기 시작해 글자가 드러나는 순간부터
 * 흔들리기 시작하고, 다 번지면 멈춰 `BrandMark` 와 같은 워드마크로 굳는다.
 *
 * 앱은 버스트 세 번(0.62~0.71 / 0.76~0.83 / 0.88~0.93)이고 그 사이엔 정확히
 * 정지였다. 2026-08-28 에 웹만 이 방식으로 바꿨다 — "글자가 보이면 바로
 * 흔들리고, 다 번지면 그때 멈춘다". 앱과 갈린 자리다.
 *
 * 뒤로 갈수록 잦아든다(`1 - p³`). 끝에서 뚝 끊지 않고 잦아들다 멎어야
 * 로고로 "굳는" 것처럼 보인다 — p 가 0.8 을 넘어서야 눈에 띄게 가라앉는
 * 곡선이라, 번짐 대부분의 구간에서는 세기가 살아 있다.
 */
export function glitchAmplitudeAt(p: number): number {
  if (p <= 0 || p >= 1) return 0
  return 1 - p * p * p
}
