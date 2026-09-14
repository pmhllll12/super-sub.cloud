/**
 * 선수 등급 — **화면이 쓰는 눈금 한 곳**.
 *
 * 🔴 **지금 서버가 내는 것은 `A`·`B`·`C`·`D` 넷뿐이다**(`analysis_report.
 * overall_grade`, `String(1)`). `S` 와 `F` 는 아래 규칙이 붙어야 생긴다 —
 * 그때까지 이 둘은 **화면에만 있는 값**이다.
 *
 * ## 표시 등급이 정해지는 규칙 (2026-09-11, 사용자 결정)
 *
 * ```
 * 분석 등급(A~D)  ×  신뢰점수(경기 뒤 서로 남긴 리뷰의 집계)
 *    → D 인데 리뷰가 없거나 신뢰점수가 낮으면      F
 *    → A 인데 신뢰점수도 좋으면                   S
 * ```
 *
 * 리뷰는 **그 사람의 대표 영상에 달린다.** 그래서 「이 사람의 등급」은
 * 대표 영상 하나에서 나온다 — 계약이 *"`overall_grade` 는 영상 하나의 값,
 * 선수 단위로 합친 오버롤은 없다"* 고 적어 둔 자리에 이 규칙이 들어간다.
 *
 * 🔴 **아직 아무것도 안 붙었다.** 평가 스키마는 있지만(계약 3-9) 계약이
 * *"평가 조회 — 내가 받은 평가를 보는 경로. **신뢰도 표시 화면이 정해지면
 * 낸다**"* 로 미뤄 두었다. 이 화면이 그 규격의 근거가 된다 — 분석 리포트가
 * 같은 길을 밟았다. 미결 항목에 올려 두었다.
 *
 * ⚠️ 그때까지 화면에 보이는 등급은 **전부 mock 이다.** 남의 리포트를 읽을
 * 경로도 없다(`GET /videos/{id}/report` 는 자기 영상만 — 남의 것은 404).
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
