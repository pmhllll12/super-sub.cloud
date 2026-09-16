/**
 * 선수 등급 — **화면이 쓰는 눈금 한 곳**.
 *
 * ✅ **2026-09-16 — 진짜가 됐다**(계약 3-6·3-16절 · 미결 `paik` 25·26번).
 * 그전까지 화면에 보이던 등급은 전부 지어낸 값이었다.
 *
 * ## 🔴 경계는 **서버가** 긋는다 — 여기서 다시 긋지 않는다
 *
 * ```
 * 표시등급(분석등급 A~D, 신뢰우세) =
 *     A 이고 신뢰 우세     → S
 *     D 이고 신뢰 우세 아님 → F
 *     그 밖                → 분석 등급 그대로
 *
 * 신뢰 우세 = (재매칭 긍정 / 재매칭 의사를 표한 건수)의
 *             95% 신뢰구간 하한 > 0.5
 * ```
 *
 * 하한을 쓰는 것이라 **표본이 작을수록 저절로 불리해진다** — 「한 건으로 `S` 가
 * 갈리면 안 된다」가 규칙을 따로 안 써도 만족된다(1건 전원 긍정의 하한은
 * 0.207, 전원 긍정이어도 4건은 있어야 넘는다). 정상호 회신(2026-09-14).
 *
 * 🔴 **`F` 는 강등이 아니다.** 「`D` 인데 구해 줄 근거가 없다」는 뜻이고, 증거
 * 없음은 어느 쪽으로도 밀지 않는다 — 리뷰가 없는 `A` 는 `S` 가 안 되고 `A` 로
 * 남는다. 못 잰 것을 나쁨의 근거로 쓰지 않는다는 규칙이 등급에도 그대로 선다.
 *
 * 🔴 **`provisional` 과 짝으로 다룬다.** 지금 루브릭은 검수 전이라(`agent/`의
 * `review_required: true`) 등급이 잠정이다. 화면은 그 값이 `true` 인 동안
 * 「검수 전」을 함께 적는다 — 등급 문자만 떼면 받는 쪽이 확정으로 읽고, 남의
 * 화면에 박힌 등급은 회수가 안 된다.
 *
 * ⚠️ 아래 `gradeValue`·`gradeFromValue`·`averageGrade` 는 **등급을 정하는 데
 * 쓰지 않는다.** 그것은 서버 몫이다 — 여기 것은 「받은 등급들로 평균을 내
 * 보여 주는」 표시용 셈이고, 모르는 사람을 셈에서 빼는 규칙이 그 안에 있다.
 */
export const GRADES = ['S', 'A', 'B', 'C', 'D', 'F'] as const

export type Grade = (typeof GRADES)[number]

/** 「등급 상관없음」 — 거르지 않는다는 뜻의 값. 빈 문자열을 쓰지 않는다(빈 값은 "아직 못 정했다"와 섞인다). */
export const ANY_GRADE = 'any' as const

export type GradeFilter = Grade | typeof ANY_GRADE

export function isGrade(v: string): v is Grade {
  return (GRADES as readonly string[]).includes(v)
}

/**
 * 평균을 내려면 등급을 수로 바꿔야 한다. 🔴 **`GRADES` 의 차례에서 뽑는다** —
 * 표를 따로 적으면 등급을 하나 늘릴 때 한쪽만 고쳐진다.
 *
 * `S` 가 가장 높으므로 뒤에서부터 센다(F=0 … S=5).
 */
export function gradeValue(g: Grade): number {
  return GRADES.length - 1 - GRADES.indexOf(g)
}

/** 수를 다시 등급으로. 반올림해서 가장 가까운 칸에 넣는다. */
export function gradeFromValue(v: number): Grade {
  const i = GRADES.length - 1 - Math.round(v)
  return GRADES[Math.min(GRADES.length - 1, Math.max(0, i))]
}

/**
 * 이미 팀에 있는 사람들의 **평균 등급** — AI 추천이 "비슷한 사람"을 고르는
 * 기준이다(사용자 요청: 넷이 찼고 하나를 더 구할 때, 그 넷의 평균과 비슷한
 * 등급만 보여 준다).
 *
 * 🔴 **등급을 모르는 사람은 셈에서 뺀다.** 0 으로 치면 아직 분석을 안 한
 * 사람이 팀 평균을 끌어내린다 — 「없다」와 「낮다」는 다르다(리포트 화면이
 * 같은 판단을 한다).
 *
 * 아무도 등급이 없으면 `null` — 그때는 거르지 않는다(빈 목록보다 낫다).
 */
export function averageGrade(list: (Grade | null | undefined)[]): Grade | null {
  const known = list.filter((g): g is Grade => !!g && isGrade(g))
  if (known.length === 0) return null
  const mean = known.reduce((sum, g) => sum + gradeValue(g), 0) / known.length
  return gradeFromValue(mean)
}
