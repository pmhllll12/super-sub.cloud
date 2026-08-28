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
 * 뒤로 갈수록 잦아들되 **끝에 가서야** 잦아든다(`1 - p⁶`). 처음엔 `1 - p³`
 * 였는데, 그러면 마지막 1.2초가 통째로 죽어 "다 번지기도 전에 멈춘 것"처럼
 * 보였다(실측). 6제곱은 p=0.9 에서도 세기가 0.47 남아 있다가 마지막에
 * 급히 떨어진다 — 번지는 내내 살아 있고, 그러면서도 뚝 끊기지 않는다.
 */
export function glitchAmplitudeAt(p: number): number {
  if (p <= 0 || p >= 1) return 0
  const p3 = p * p * p
  return 1 - p3 * p3
}

/**
 * 띠가 어긋나는 최대 폭 — **글자 크기 기준(em)이다.**
 *
 * 앱은 글자가 52px 고정이라 14px 로 못박았는데, 웹은 글자가 화면 폭을
 * 따라가므로(`GlitchIntro` 의 `BRAND_SIZE`) 같은 픽셀 값을 쓰면 큰 화면에서
 * 흔들림만 상대적으로 작아진다. 그래서 비율을 em 으로 옮겼다.
 *
 * 값이 22/52 로 앱(14/52)보다 큰 이유는 아래 분포 때문이다 — 앱은 매 순간
 * 모든 띠를 균등하게 흔들어 14px 이 곧 **평균**이지만, 여기서는 대부분
 * 가만히 있다가 드물게 크게 튄다. 이건 **정점**이지 평균이 아니다.
 */
export const MAX_SHIFT_EM = 22 / 52

/**
 * 이보다 작게 어긋난 것은 **안 어긋난 것으로 친다**(글자 크기 기준 em, 52px
 * 에서 1px). `r³` 분포는 0 근처 값을 잔뜩 만드는데, 눈에는 안 보이면서 글자를
 * 조각내게 만들어 **조각 경계만 가로줄로 드러낸다**(`GlitchIntro` 주석 참고).
 */
export const MIN_SHIFT_EM = 1 / 52

/**
 * 한 순간(`HOLD_MS` 한 칸)에 무언가 어긋날 확률 — `amplitude` 를 곱해 쓴다.
 * 나머지 순간은 **정확히 정지**다.
 */
export const TEAR_CHANCE = 0.55

/** 터지는 순간에 띠 하나가 어긋날 확률. 7개 중 서넛만 움직인다. */
export const SLICE_CHANCE = 0.45

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
 * `seed` 로 결정되는 띠별 가로 어긋남(em). `BANDS` 개.
 *
 * **규칙적으로 흔들면 글리치가 아니라 그냥 떨림으로 보인다.** 앱처럼 매 칸
 * 모든 띠를 흔드는 방식은 버스트 3회 사이의 정적이 있어서 성립했는데, 웹은
 * 번지는 내내 흔들기로 해서 그 정적이 사라졌고 — 그래서 인위적으로 보였다.
 *
 * 정적을 **분포 안으로** 되돌린다. 세 가지가 겹쳐 불규칙해진다:
 *
 * 1. **대부분의 순간은 통째로 정지한다** (`TEAR_CHANCE`). 터지는 칸이 몇 개
 *    연달아 걸리기도 하고 한참 안 걸리기도 해서, 45ms 격자를 그대로 쓰면서도
 *    리듬이 불규칙해진다 — 메트로놈처럼 들리던 게 사라진다
 * 2. **터질 때도 일부 띠만 움직인다** (`SLICE_CHANCE`). 나머지는 제자리라
 *    "화면이 떠는" 게 아니라 "글자가 잘려 어긋난" 것으로 읽힌다. 움직이는 띠가
 *    붙어 나오면 그만큼 두꺼운 조각이 되어 조각 높이까지 매번 달라진다
 * 3. **크기가 한쪽으로 쏠린다** (`r³`). 대부분 작게, 가끔 크게 —
 *    균등분포는 전부 비슷한 크기로 흔들려 기계처럼 보인다
 */
export function bandShifts(seed: number, amplitude: number): number[] {
  const still = () => new Array<number>(BANDS).fill(0)
  if (amplitude <= 0) return still()

  const next = mulberry32(seed)
  if (next() > TEAR_CHANCE * amplitude) return still()

  return Array.from({ length: BANDS }, () => {
    if (next() > SLICE_CHANCE) return 0
    const r = next() * 2 - 1
    const shift = r * r * r * amplitude * MAX_SHIFT_EM
    return Math.abs(shift) < MIN_SHIFT_EM ? 0 : shift
  })
}
