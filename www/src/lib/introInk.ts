/**
 * 인트로 잉크 번짐·글리치의 순수 함수들.
 *
 * 원본: `flutter/lib/core/widgets/ink_bleed.dart` (`inkProgress`),
 * `flutter/lib/features/intro/presentation/screens/glitch_intro_screen.dart`
 * (`glitchAmplitudeAt`, 버스트 표, `_kSwapAt`). 수치는 참조 영상에서 잰
 * 값이라 근거 없이 바꾸지 않는다 — **흔들림은 앱 그대로다.** 웹만 다른 것은
 * 구간 길이(아래)와 어긋남의 단위(px → em)뿐이고, 각 상수 주석에 앱 값을
 * 함께 적어 뒀다.
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

/**
 * 잉크가 **역으로 걷히는** 시간 — 인트로에서 화면으로 넘어가는 구간이다.
 *
 * 번질 때와 같은 알갱이(같은 셰이더의 `uErase`)로 되돌려, 검게 덮인 화면이
 * 점 단위로 사라지며 그 밑의 화면이 드러난다. 워드마크가 제자리로 날아가는
 * 시간(`GlitchIntro` 의 비행)과 같은 길이라 둘이 함께 끝난다.
 */
export const ERASE_MS = 700

/** 전체 인트로 길이(ms). */
export const TOTAL_MS = DRY_MS + WET_MS + SETTLE_MS

/** 민트만 보이는 구간이 끝나는 컨트롤러 값. */
export const DRY_END = DRY_MS / TOTAL_MS

/** 번짐이 끝나는 컨트롤러 값. */
export const WET_END = (DRY_MS + WET_MS) / TOTAL_MS

/** 흔들림 값을 붙잡아 두는 시간(ms). 매 프레임 새로 뽑으면 지글거림이 된다. */
export const HOLD_MS = 45

/** 글자를 끊는 가로 띠 수. 앱과 같다. */
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
 * 지지직대는 구간 — `[시작, 끝, 세기]`, **잉크 진행도 기준**이다.
 * 버스트는 이 세 번뿐이고 그 사이는 진폭이 정확히 0이다. **앱 그대로다.**
 *
 * 2026-08-28 에 웹만 다르게 가려고 두 번 시도했다가 둘 다 되돌렸다:
 * 번지는 내내 연속으로 흔들기(→ 글리치가 아니라 진동으로 보였다), 확률로
 * 드문드문 터뜨리기(→ 몇 번 터질지 통제가 안 돼 어수선했다). 참조 영상에서
 * 잰 이 표가 가장 낫다 — 근거 없이 바꾸지 말 것.
 */
const BURSTS: readonly [start: number, end: number, power: number][] = [
  [0.62, 0.71, 1.0],
  [0.76, 0.83, 0.72],
  [0.88, 0.93, 0.4],
]

/** 흔들리는 구간이 몇 번인지 — 테스트가 이 수를 본다. */
export const BURST_COUNT = BURSTS.length

/**
 * 잉크 진행도 `p`에서 얼마나 세게 흔들릴지(0~1).
 *
 * 버스트 안에서도 뒤로 갈수록 잦아든다(`power * (1 - into²)`). 버스트
 * 밖에서는 항상 0 — **사이의 정적이 있어야 터지는 순간이 산다.**
 */
export function glitchAmplitudeAt(p: number): number {
  for (const [start, end, power] of BURSTS) {
    if (p < start || p >= end) continue
    const into = (p - start) / (end - start)
    return power * (1 - into * into)
  }
  return 0
}

/**
 * 띠가 어긋나는 폭 — **글자 크기 기준(em)이다.**
 *
 * 앱은 글자가 52px 고정이라 14px 로 못박았는데, 웹은 글자가 화면 폭을
 * 따라가므로(`GlitchIntro` 의 `BRAND_SIZE`) 같은 픽셀 값을 쓰면 큰 화면에서
 * 흔들림만 상대적으로 작아진다. 그래서 비율을 em 으로 옮겼다 — 52px 에서는
 * 앱과 정확히 같은 14px 이다. **단위만 바꾼 것이지 세기는 앱 그대로다.**
 */
export const MAX_SHIFT_EM = 14 / 52

/** 표준 mulberry32 PRNG — 같은 seed 면 같은 수열이다. */
function mulberry32(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/**
 * `seed` 로 결정되는 띠별 가로 어긋남(em). `BANDS` 개. **앱 그대로다** —
 * 버스트가 도는 동안 일곱 띠가 매 칸 각각 다르게 어긋난다.
 *
 * 진폭이 0이면(버스트 밖) 전부 0을 준다. `GlitchIntro` 가 이때 글자를
 * 자르지 않고 통짜로 그린다 — 자르기만 해도 조각 경계가 가로줄로 보인다.
 */
export function bandShifts(seed: number, amplitude: number): number[] {
  if (amplitude <= 0) return new Array<number>(BANDS).fill(0)
  const next = mulberry32(seed)
  return Array.from({ length: BANDS }, () => (next() * 2 - 1) * amplitude * MAX_SHIFT_EM)
}

/**
 * 걷히는 진행도(0~1) — 앞이 빠르고 뒤가 느리다(`1 − (1−e)²`).
 *
 * 번질 때(`inkProgress`)와 방향이 반대다. 번짐은 "천천히 스며드는" 것이고
 * 이건 "확 걷히는" 것이라, 앞에서 대부분을 걷어내고 남은 자락만 마무리한다.
 */
export function eraseProgress(e: number): number {
  if (e <= 0) return 0
  if (e >= 1) return 1
  const rest = 1 - e
  return 1 - rest * rest
}
