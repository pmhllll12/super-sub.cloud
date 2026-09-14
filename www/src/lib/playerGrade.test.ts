import { describe, it, expect } from 'vitest'
import { GRADES, averageGrade, gradeFromValue, gradeValue } from './playerGrade'

describe('선수 등급', () => {
  /** 🔴 눈금의 차례가 곧 값이다 — 표를 따로 두면 한쪽만 늙는다. */
  it('S 가 가장 높고 F 가 가장 낮다', () => {
    const values = GRADES.map(gradeValue)
    expect(values).toEqual([...values].sort((a, b) => b - a))
    expect(gradeValue('S')).toBeGreaterThan(gradeValue('A'))
    expect(gradeValue('D')).toBeGreaterThan(gradeValue('F'))
  })

  it('수로 바꿨다 되돌려도 같은 등급이다', () => {
    for (const g of GRADES) expect(gradeFromValue(gradeValue(g))).toBe(g)
  })

  it('평균은 가장 가까운 칸으로 간다', () => {
    expect(averageGrade(['A', 'A', 'A'])).toBe('A')
    // A(4) B(3) B(3) C(2) → 3 = B
    expect(averageGrade(['A', 'B', 'B', 'C'])).toBe('B')
  })

  /**
   * 🔴 **「모른다」와 「낮다」는 다르다.** 아직 분석을 안 한 사람을 0(F)으로
   * 치면 팀 평균이 통째로 끌려 내려가, 멀쩡한 팀에 F 만 추천된다.
   */
  it('등급을 모르는 사람은 셈에서 뺀다', () => {
    expect(averageGrade(['A', null, 'A', undefined])).toBe('A')
  })

  /** 아무도 등급이 없으면 거르지 않는다 — 빈 목록보다 낫다. */
  it('아무도 등급이 없으면 null 이다', () => {
    expect(averageGrade([null, undefined])).toBeNull()
  })
})
